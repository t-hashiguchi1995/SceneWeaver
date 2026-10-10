import { useQuery } from '@tanstack/react-query'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'

import { api, saveStudioContext } from '../../../../lib/api'

export const Route = createFileRoute('/shots/$shotId/generations/')({
  component: GenerationHistoryPage,
})

function GenerationHistoryPage() {
  const { t } = useTranslation('generation')
  const navigate = useNavigate()
  const { shotId } = Route.useParams()

  const history = useQuery({
    queryKey: ['generation-attempts', shotId],
    queryFn: () => api.listGenerationAttempts(shotId),
  })

  useEffect(() => {
    const latest = history.data?.items?.[0]
    if (!latest) return
    saveStudioContext({ shotId, generationAttemptId: latest.id })
    void navigate({
      to: '/shots/$shotId/generations/$attemptId',
      params: { shotId, attemptId: latest.id },
      replace: true,
    })
  }, [history.data, navigate, shotId])

  if (history.isLoading) {
    return (
      <section className="page" data-testid="generation-history-page">
        <h1>{t('historyTitle')}</h1>
        <p className="meta">…</p>
      </section>
    )
  }

  if (!history.data?.items?.length) {
    return (
      <section className="page" data-testid="generation-history-page">
        <h1>{t('historyTitle')}</h1>
        <p className="lede">{t('historyEmpty')}</p>
        <button
          type="button"
          className="btn primary"
          onClick={() => navigate({ to: '/shots/$shotId', params: { shotId } })}
        >
          {t('openShotStudio')}
        </button>
      </section>
    )
  }

  return (
    <section className="page" data-testid="generation-history-page">
      <h1>{t('historyTitle')}</h1>
      <p className="meta">…</p>
    </section>
  )
}
