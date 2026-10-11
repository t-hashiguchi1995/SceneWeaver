import { useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'

export function useCharacterAutosave(id: string, persona: Record<string, unknown>, visual: Record<string, unknown>) {
  const latest = useRef({ persona, visual })
  latest.current = { persona, visual }
  const saved = useRef({ persona: JSON.stringify(persona), visual: JSON.stringify(visual) })
  const chain = useRef<Promise<unknown>>(Promise.resolve())
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const alive = useRef(true)
  const [status, setStatus] = useState('saved')
  const [error, setError] = useState('')
  const flush = () => {
    clearTimeout(timer.current)
    const snapshot = latest.current
    chain.current = chain.current.catch(() => undefined).then(async () => {
      if (alive.current) setStatus('saving')
      try {
        const p = JSON.stringify(snapshot.persona)
        const v = JSON.stringify(snapshot.visual)
        if (p !== saved.current.persona) {
          await api.updatePersona(id, snapshot.persona)
          saved.current.persona = p
        }
        if (v !== saved.current.visual) {
          await api.updateVisualIdentity(id, snapshot.visual)
          saved.current.visual = v
        }
        if (alive.current) { setStatus(JSON.stringify(latest.current.persona) === saved.current.persona && JSON.stringify(latest.current.visual) === saved.current.visual ? 'saved' : 'unsaved'); setError('') }
      } catch (err) {
        if (alive.current) { setStatus('saveFailed'); setError((err as Error).message) }
        throw err
      }
    })
    return chain.current
  }
  const flushRef = useRef(flush)
  flushRef.current = flush
  useEffect(() => {
    if (JSON.stringify(persona) === saved.current.persona && JSON.stringify(visual) === saved.current.visual) return
    setStatus('unsaved')
    timer.current = setTimeout(() => { void flushRef.current().catch(() => undefined) }, 700)
    return () => clearTimeout(timer.current)
  }, [persona, visual])
  useEffect(() => {
    alive.current = true
    return () => { alive.current = false; void flushRef.current().catch(() => undefined) }
  }, [id])
  return { status, error, flush }
}
