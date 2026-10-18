import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from '@tanstack/react-router'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { AssetImage } from './AssetImage'
import { ErrorBanner } from './ErrorBanner'
import { WorkflowCompletionCard } from './WorkflowCompletionCard'
import {
  api,
  saveStudioContext,
  type GenerationAttemptSummary,
} from '../lib/api'

function attemptBadge(attempt: GenerationAttemptSummary): string | null {
  const decisions = Object.values(attempt.asset_decisions ?? {})
  if (decisions.includes('adopted')) return 'adopted'
  if (decisions.includes('rejected') && decisions.every((d) => d === 'rejected')) return 'rejected'
  return null
}

export type GenerationReviewViewProps = {
  shotId: string
  attemptId?: string
  projectId?: string
}

export function GenerationReviewView({ shotId, attemptId, projectId }: GenerationReviewViewProps) {
  const { t } = useTranslation(['generation', 'common', 'prompt', 'project'])
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [selectedAttemptId, setSelectedAttemptId] = useState(attemptId ?? '')
  const [selectedCandidate, setSelectedCandidate] = useState(0)
  const [adoptedId, setAdoptedId] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    if (attemptId) setSelectedAttemptId(attemptId)
  }, [attemptId])

  const history = useQuery({
    queryKey: ['generation-attempts', shotId],
    queryFn: () => api.listGenerationAttempts(shotId),
    enabled: Boolean(shotId),
  })

  const attempts = history.data?.items ?? []
  const selected =
    attempts.find((a) => a.id === selectedAttemptId) ?? attempts[0] ?? null

  useEffect(() => {
    if (!selectedAttemptId && attempts[0]) setSelectedAttemptId(attempts[0].id)
  }, [attempts, selectedAttemptId])

  useEffect(() => {
    setSelectedCandidate(0)
  }, [selected?.id])

  const candidates = selected?.output_asset_ids ?? []
  const activeAssetId = candidates[selectedCandidate] ?? ''

  const provenance = useMemo(() => {
    if (!selected) return null
    return {
      model: selected.model_id || String(selected.payload.model_id || '—'),
      workflow: selected.workflow_template_id || '—',
      seed: selected.seed,
      modified: Boolean(selected.modified),
      promptHash: selected.prompt_hash || '',
      workflowHash: selected.workflow_hash || '',
      source:
        selected.source_kind === 'compiler_rule'
          ? `Anima Compiler ${selected.template_version || 'v1'}`
          : `${selected.source_kind || ''}: ${selected.source_ref || ''}`,
      revision: selected.based_on_shot_revision,
    }
  }, [selected])

  const goAttempt = (id: string) => {
    setSelectedAttemptId(id)
    saveStudioContext({ shotId, generationAttemptId: id })
    void navigate({
      to: projectId
        ? '/projects/$projectId/shots/$shotId/generations/$attemptId'
        : '/shots/$shotId/generations/$attemptId',
      params: { projectId: projectId ?? '', shotId, attemptId: id },
    })
  }

  const adopt = useMutation({
    mutationFn: (assetId: string) => api.setAssetDecision(assetId, 'adopted'),
    onSuccess: (result) => {
      setAdoptedId(result.asset_id)
      saveStudioContext({
        shotId,
        adoptedRenderAssetId: result.asset_id,
        adoptedRenderSha256: result.sha256,
        generationAttemptId: selected?.id,
      })
      void qc.invalidateQueries({ queryKey: ['generation-attempts', shotId] })
    },
    onError: (err) => setError((err as Error).message),
  })

  const reject = useMutation({
    mutationFn: (assetId: string) => api.setAssetDecision(assetId, 'rejected'),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['generation-attempts', shotId] })
    },
    onError: (err) => setError((err as Error).message),
  })

  const regenerateSame = useMutation({
    mutationFn: (mode: 'new' | 'same') => api.replayGeneration(selected!.id, mode),
    onSuccess: (result) => {
      saveStudioContext({
        shotId: result.shot_id,
        generationAttemptId: result.generation_attempt_id,
        generationAssetIds: result.output_asset_ids,
      })
      void qc.invalidateQueries({ queryKey: ['generation-attempts', shotId] })
      void navigate({
        to: projectId
          ? '/projects/$projectId/shots/$shotId/generations/$attemptId'
          : '/shots/$shotId/generations/$attemptId',
        params: {
          projectId: projectId ?? '',
          shotId: result.shot_id,
          attemptId: result.generation_attempt_id,
        },
      })
    },
    onError: (err) => setError((err as Error).message),
  })

  const editPromptAndRegenerate = async () => {
    if (!selected) return
    const positive = String(selected.final_positive_prompt || '')
    const negative = String(selected.final_negative_prompt || '')
    await api.ensurePromptDraft(shotId)
    await api.updatePromptDraft(shotId, positive, negative)
    saveStudioContext({ shotId, generationAttemptId: selected.id })
    void navigate({
      to: projectId ? '/projects/$projectId/shots/$shotId' : '/shots/$shotId',
      search: {
        sourceAttemptId: selected.payload.render_snapshot ? selected.id : undefined,
      },
      params: { projectId: projectId ?? '', shotId },
    })
  }

  if (!shotId) {
    return (
      <section className="page" data-testid="generation-review">
        <h1>{t('generation:reviewTitle')}</h1>
        <p className="lede">{t('generation:reviewEmpty')}</p>
        <button type="button" className="btn primary" onClick={() => navigate({ to: '/shots' })}>
          {t('generation:openShotStudio')}
        </button>
      </section>
    )
  }

  return (
    <section className="page" data-testid="generation-review">
      <div className="row-between">
        <div>
          <h1>{t('generation:reviewTitle')}</h1>
          <p className="lede">{t('generation:reviewLede')}</p>
        </div>
        <button
          type="button"
          className="btn"
          data-testid="review-open-shot-studio"
          onClick={() =>
            navigate({
              to: projectId ? '/projects/$projectId/shots/$shotId' : '/shots/$shotId',
              params: { projectId: projectId ?? '', shotId },
            })
          }
        >
          {t('generation:openShotStudio')}
        </button>
      </div>

      {error && <ErrorBanner message={error} />}

      <div className="review-layout review-layout-3pane">
        <aside className="review-history" data-testid="generation-history">
          <h2>{t('generation:historyTitle')}</h2>
          {attempts.length === 0 && <p className="meta">{t('generation:historyEmpty')}</p>}
          <ul className="list">
            {attempts.map((attempt, index) => {
              const badge = attemptBadge(attempt)
              const label = `#${attempts.length - index}`
              return (
                <li key={attempt.id}>
                  <button
                    type="button"
                    className={attempt.id === selected?.id ? 'btn primary' : 'btn'}
                    data-testid={`generation-history-${index}`}
                    onClick={() => goAttempt(attempt.id)}
                  >
                    {label}{' '}
                    <span className="meta">
                      {new Date(attempt.created_at).toLocaleTimeString('ja-JP', {
                        hour: '2-digit',
                        minute: '2-digit',
                        hour12: false,
                      })}
                      {badge ? ` · ${t(`common:status.${badge}`)}` : ''}
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        </aside>

        <div className="review-candidates">
          {selected && (
            <>
              <p className="meta" data-testid="generation-attempt-id">
                {t('generation:attemptLabel', { id: selected.id.slice(0, 8) })} ·{' '}
                {t(
                  `common:status.${selected.status === 'succeeded' ? 'succeeded' : selected.status}`,
                )}
              </p>
              <ul className="candidate-grid" data-testid="generation-candidate-list">
                {candidates.map((id, index) => (
                  <li key={id} data-testid={`generation-candidate-${index}`}>
                    <button
                      type="button"
                      className={
                        index === selectedCandidate
                          ? 'btn primary candidate-select'
                          : 'btn candidate-select'
                      }
                      aria-pressed={index === selectedCandidate}
                      data-testid={`generation-select-${index}`}
                      onClick={() => setSelectedCandidate(index)}
                    >
                      <AssetImage assetId={id} alt={t('generation:candidate', { n: index + 1 })} />
                      {t('generation:candidate', { n: index + 1 })}
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>

        <div className="review-detail">
          {selected && activeAssetId && (
            <div className="stack panel-card" data-testid="generation-candidate-detail">
              <h2>
                {t('generation:candidate', { n: selectedCandidate + 1 })} —{' '}
                {t('generation:largePreview')}
              </h2>
              <div className="candidate-preview" data-testid="generation-large-preview">
                <AssetImage
                  assetId={activeAssetId}
                  alt={t('generation:candidate', { n: selectedCandidate + 1 })}
                />
              </div>
              <div className="review-primary-actions">
                <button
                  type="button"
                  className="btn primary"
                  data-testid="generation-adopt"
                  onClick={() => adopt.mutate(activeAssetId)}
                >
                  {t('generation:actions.adopt')}
                </button>
                <button
                  type="button"
                  className="btn"
                  data-testid="generation-reject"
                  onClick={() => reject.mutate(activeAssetId)}
                >
                  {t('generation:actions.reject')}
                </button>
              </div>
              <div className="review-secondary-actions">
                <button
                  type="button"
                  className="btn"
                  data-testid="generation-regenerate-same"
                  disabled={regenerateSame.isPending || !selected?.payload.render_snapshot}
                  onClick={() => regenerateSame.mutate('new')}
                >
                  {t('generation:actions.regenerateSame')}
                </button>
                <button
                  type="button"
                  className="btn"
                  data-testid="generation-reproduce"
                  disabled={regenerateSame.isPending || !selected?.payload.render_snapshot}
                  onClick={() => regenerateSame.mutate('same')}
                >
                  {t('generation:actions.reproduce')}
                </button>
                <button
                  type="button"
                  className="btn"
                  data-testid="generation-edit-prompt"
                  onClick={() =>
                    void editPromptAndRegenerate().catch((err: Error) => setError(err.message))
                  }
                >
                  {t('generation:actions.editPrompt')}
                </button>
              </div>
            </div>
          )}

          {selected && provenance && (
            <details className="panel-card review-meta-panel" data-testid="generation-provenance">
              <summary>{t('generation:provenanceTitle')}</summary>
              <div className="review-meta-content">
                <p className="meta">
                  {t('generation:model')}: {provenance.model}
                </p>
                <p className="meta">
                  {t('generation:template')}: {provenance.source}
                </p>
                <p className="meta">
                  {t('generation:workflow')}: {provenance.workflow}
                </p>
                <p className="meta">
                  {t('generation:seed')}: {provenance.seed}
                </p>
                <p className="meta">
                  {t('generation:shotRevision')}: {provenance.revision}
                </p>
                <p className="meta">
                  {t('generation:promptModified')}:{' '}
                  {provenance.modified ? t('common:yes') : t('common:no')}
                </p>
                <p className="meta" data-testid="generation-workflow-hash">
                  {t('generation:workflowHash')}: {provenance.workflowHash.slice(0, 12)}…
                </p>
              </div>
            </details>
          )}

          {selected && (
            <details
              className="panel-card review-meta-panel"
              data-testid="generation-prompt-snapshot"
            >
              <summary>{t('generation:runtimePromptTitle')}</summary>
              <div className="review-meta-content">
                <p className="meta" data-testid="generation-prompt-hash">
                  {t('generation:promptHash')}: {provenance?.promptHash?.slice(0, 12)}…
                </p>
                <label>
                  {t('prompt:positive')}
                  <pre className="lede" data-testid="generation-final-positive">
                    {String(selected.final_positive_prompt || '')}
                  </pre>
                </label>
                <label>
                  {t('prompt:negative')}
                  <pre className="lede" data-testid="generation-final-negative">
                    {String(selected.final_negative_prompt || '')}
                  </pre>
                </label>
              </div>
            </details>
          )}

          {adoptedId && (
            <p data-testid="generation-adopted-banner">
              {t('generation:adoptedBanner', { asset: `${adoptedId.slice(0, 8)}…` })}
            </p>
          )}

          <details className="meta technical-details">
            <summary>{t('generation:technicalInfo')}</summary>
            <p className="meta" data-testid="review-shot-id">
              {t('generation:shotId', { id: shotId })}
            </p>
            {activeAssetId && (
              <code data-testid="generation-active-asset">{activeAssetId}</code>
            )}
          </details>
        </div>
      </div>
      {adoptedId && projectId && (
        <WorkflowCompletionCard
          testId="review-next-csp"
          title={t('project:completion.reviewTitle')}
          description={t('project:completion.reviewDescription')}
          action={
            <Link
              className="btn primary"
              to="/projects/$projectId/csp"
              params={{ projectId }}
              data-testid="review-next-csp-action"
            >
              {t('project:completion.reviewAction')}
            </Link>
          }
        />
      )}
    </section>
  )
}
