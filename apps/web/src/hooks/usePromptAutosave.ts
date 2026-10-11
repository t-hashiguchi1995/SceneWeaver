import { useEffect, useRef, useState } from 'react'
import { api, type PromptDraft } from '../lib/api'

// Serialize writes per editor so a slow response cannot overwrite a newer edit.
export function usePromptAutosave(shotId: string, draft: PromptDraft | null) {
  const [status, setStatus] = useState<'saveDirty' | 'saveSaving' | 'saveSaved' | 'saveError'>('saveSaved')
  const [error, setError] = useState('')
  const latest = useRef(draft)
  latest.current = draft
  const saved = useRef('')
  const chain = useRef<Promise<unknown>>(Promise.resolve())
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const alive = useRef(true)
  const key = (d: PromptDraft) => JSON.stringify([d.id, d.edited_positive, d.edited_negative])
  const flush = () => {
    clearTimeout(timer.current)
    const value = latest.current
    if (!value || key(value) === saved.current) return chain.current
    const valueKey = key(value)
    chain.current = chain.current.catch(() => undefined).then(async () => {
      if (valueKey === saved.current) return
      if (alive.current) setStatus('saveSaving')
      try {
        await api.updatePromptDraft(value.shot_id, value.edited_positive, value.edited_negative)
        saved.current = valueKey
        if (alive.current) {
          setStatus(latest.current && key(latest.current) !== valueKey ? 'saveDirty' : 'saveSaved')
          setError('')
        }
      } catch (err) {
        if (alive.current) { setStatus('saveError'); setError((err as Error).message) }
        throw err
      }
    })
    return chain.current
  }
  const flushRef = useRef(flush)
  flushRef.current = flush
  useEffect(() => {
    alive.current = true
    saved.current = ''
    return () => {
      alive.current = false
      void flushRef.current().catch(() => undefined)
    }
  }, [shotId])
  useEffect(() => {
    if (!draft) return
    if (!saved.current) { saved.current = key(draft); return }
    if (saved.current === key(draft)) return
    setStatus('saveDirty')
    clearTimeout(timer.current)
    timer.current = setTimeout(() => { void flushRef.current().catch(() => undefined) }, 700)
    return () => clearTimeout(timer.current)
  }, [draft])
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (latest.current && key(latest.current) !== saved.current) {
        event.preventDefault()
        event.returnValue = ''
      }
    }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [])
  return { status, error, flush }
}
