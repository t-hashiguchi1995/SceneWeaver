import { useMutation } from '@tanstack/react-query'
import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { ErrorBanner } from '../../components/ErrorBanner'
import { api, loadStudioContext, saveStudioContext } from '../../lib/api'

export const Route = createFileRoute('/shots/')({
  component: ShotsEntryPage,
})

function ShotsEntryPage() {
  const { t } = useTranslation(['generation', 'common'])
  const navigate = useNavigate()
  const ctx = loadStudioContext()
  const [beatId, setBeatId] = useState(ctx.beatId ?? '')
  const [error, setError] = useState('')

  const plan = useMutation({
    mutationFn: () => api.planShot(beatId),
    onSuccess: async (shot) => {
      saveStudioContext({ shotId: shot.id, beatId })
      await api.ensurePromptDraft(shot.id)
      void navigate({ to: '/shots/$shotId', params: { shotId: shot.id } })
    },
    onError: (err) => setError((err as Error).message),
  })

  return (
    <section className="page" data-testid="shots-entry-page">
      <h1>{t('generation:title')}</h1>
      <p className="lede">{t('generation:lede')}</p>

      {ctx.shotId && (
        <div className="cta-row">
          <Link
            to="/shots/$shotId"
            params={{ shotId: ctx.shotId }}
            className="btn primary"
            data-testid="shot-continue"
          >
            {t('generation:continueShot')}
          </Link>
          <Link
            to="/shots/$shotId/generations"
            params={{ shotId: ctx.shotId }}
            className="btn"
            data-testid="shot-open-review"
          >
            {t('generation:openReview')}
          </Link>
        </div>
      )}

      <div className="stack">
        <label>
          {t('generation:beatId')}
          <input
            aria-label={t('generation:beatId')}
            data-testid="shot-beat-id"
            value={beatId}
            onChange={(e) => setBeatId(e.target.value)}
          />
        </label>
        <button
          type="button"
          className="btn primary"
          data-testid="shot-plan"
          disabled={!beatId || plan.isPending}
          onClick={() => plan.mutate()}
        >
          {t('generation:planShot')}
        </button>
      </div>

      {error && <ErrorBanner message={error} />}
    </section>
  )
}
