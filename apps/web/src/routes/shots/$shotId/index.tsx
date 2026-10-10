import { useMutation } from '@tanstack/react-query'
import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { ErrorBanner } from '../../../components/ErrorBanner'
import { PromptEditor } from '../../../components/PromptEditor'
import { formatStatus } from '../../../i18n/format'
import { api, saveStudioContext, type PromptDraft } from '../../../lib/api'

export const Route = createFileRoute('/shots/$shotId/')({
  component: ShotStudioPage,
})

function withLocalEdits(
  draft: PromptDraft,
  editedPositive: string,
  editedNegative: string,
): PromptDraft {
  const modified_positive = editedPositive !== draft.rendered_base_positive
  const modified_negative = editedNegative !== draft.rendered_base_negative
  return {
    ...draft,
    edited_positive: editedPositive,
    edited_negative: editedNegative,
    modified_positive,
    modified_negative,
    modified: modified_positive || modified_negative,
  }
}

function ShotStudioPage() {
  const { t } = useTranslation(['generation', 'common', 'prompt'])
  const navigate = useNavigate()
  const { shotId } = Route.useParams()
  const [usePose, setUsePose] = useState(true)
  const [phase, setPhase] = useState<'idle' | 'queued' | 'running' | 'succeeded' | 'failed'>('idle')
  const [error, setError] = useState('')
  const [draft, setDraft] = useState<PromptDraft | null>(null)
  const [templateBody, setTemplateBody] = useState('')
  const [staleDismissed, setStaleDismissed] = useState(false)
  const [specSummary, setSpecSummary] = useState<Record<string, unknown>>({})

  useEffect(() => {
    saveStudioContext({ shotId })
    let cancelled = false
    void (async () => {
      try {
        const shot = await api.getShot(shotId)
        if (cancelled) return
        setSpecSummary(shot.render_spec ?? {})
        const existing = await api.ensurePromptDraft(shotId)
        if (cancelled) return
        setDraft(existing)
        const tpl = await api.getPromptTemplate(shotId)
        if (!cancelled) setTemplateBody(tpl.body)
      } catch (err) {
        if (!cancelled) setError((err as Error).message)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [shotId])

  const resetEdits = useMutation({
    mutationFn: () => api.resetPromptEdits(shotId),
    onSuccess: (updated) => setDraft(updated),
  })

  const rebuild = useMutation({
    mutationFn: (confirm: boolean) => api.rebuildPromptDraft(shotId, confirm),
    onSuccess: (updated) => {
      setDraft(updated)
      setStaleDismissed(false)
    },
    onError: (err) => setError((err as Error).message),
  })

  const render = useMutation({
    mutationFn: async () => {
      if (draft) {
        await api.updatePromptDraft(shotId, draft.edited_positive, draft.edited_negative)
      }
      setPhase('queued')
      await new Promise((r) => setTimeout(r, 120))
      setPhase('running')
      return api.renderShot(shotId, usePose)
    },
    onSuccess: (result) => {
      setPhase('succeeded')
      saveStudioContext({
        shotId: result.shot_id,
        generationAssetIds: result.output_asset_ids,
        generationAttemptId: result.generation_attempt_id,
      })
      void navigate({
        to: '/shots/$shotId/generations/$attemptId',
        params: { shotId: result.shot_id, attemptId: result.generation_attempt_id },
      })
    },
    onError: (err) => {
      setPhase('failed')
      setError((err as Error).message)
    },
  })

  const expression = (specSummary.expression as { id?: string } | undefined)?.id
  const characterTags = Array.isArray(specSummary.identity_tags)
    ? (specSummary.identity_tags as string[]).slice(0, 3).join(', ')
    : ''

  return (
    <section className="page" data-testid="shots-page">
      <div className="row-between">
        <div>
          <h1>{t('generation:title')}</h1>
          <p className="lede">{t('generation:lede')}</p>
        </div>
        <div className="cta-row">
          <Link
            to="/shots/$shotId/generations"
            params={{ shotId }}
            className="btn"
            data-testid="shot-open-review"
          >
            {t('generation:openReview')}
          </Link>
        </div>
      </div>

      <div className="stack panel-card" data-testid="shot-settings-summary">
        <h2>{t('generation:shotSettings')}</h2>
        <p className="meta">
          {t('generation:character')}: {characterTags || '—'}
        </p>
        <p className="meta">
          {t('generation:expression')}: {expression || '—'}
        </p>
        <label className="checkbox">
          <input
            type="checkbox"
            data-testid="shot-use-pose"
            checked={usePose}
            onChange={(e) => setUsePose(e.target.checked)}
          />
          {t('generation:poseCamera')}
        </label>
      </div>

      {!draft && !error && <p className="meta">{t('prompt:loading')}</p>}

      {draft && (
        <PromptEditor
          templateLabel={draft.template_label}
          sourceKind={draft.source_kind}
          templateSource={templateBody}
          renderedBasePositive={draft.rendered_base_positive}
          renderedBaseNegative={draft.rendered_base_negative}
          editedPositive={draft.edited_positive}
          editedNegative={draft.edited_negative}
          modifiedPositive={draft.modified_positive}
          modifiedNegative={draft.modified_negative}
          stale={draft.stale && !staleDismissed}
          generateDisabled={render.isPending}
          onPositiveChange={(value) =>
            setDraft(withLocalEdits(draft, value, draft.edited_negative))
          }
          onNegativeChange={(value) =>
            setDraft(withLocalEdits(draft, draft.edited_positive, value))
          }
          onResetEdits={() => resetEdits.mutate()}
          onRebuild={() => {
            if (draft.modified && !window.confirm(t('prompt:rebuildConfirm'))) return
            rebuild.mutate(draft.modified)
          }}
          onDismissStale={() => setStaleDismissed(true)}
          onGenerate={() => render.mutate()}
        />
      )}

      <p className="hint" data-testid="shot-phase">
        {t('generation:statusLabel')}:{' '}
        <span data-testid="shot-status-label">{formatStatus(t, phase)}</span>
      </p>
      <p className="meta" data-testid="shot-id">
        {t('generation:shotId', { id: shotId })}
      </p>
      {error && <ErrorBanner message={error} />}
    </section>
  )
}
