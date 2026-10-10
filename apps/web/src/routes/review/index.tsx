import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'

import { loadStudioContext } from '../../lib/api'

export const Route = createFileRoute('/review/')({
  component: ReviewRedirectPage,
  validateSearch: (search: Record<string, unknown>) => ({
    shotId: typeof search.shotId === 'string' ? search.shotId : undefined,
    attemptId: typeof search.attemptId === 'string' ? search.attemptId : undefined,
  }),
})

/** Compat redirect → UI Spec R1 nested routes under /shots/:shotId/generations */
function ReviewRedirectPage() {
  const { t } = useTranslation('generation')
  const navigate = useNavigate()
  const search = Route.useSearch()
  const ctx = loadStudioContext()
  const shotId = search.shotId || ctx.shotId
  const attemptId = search.attemptId || ctx.generationAttemptId

  useEffect(() => {
    if (!shotId) return
    if (attemptId) {
      void navigate({
        to: '/shots/$shotId/generations/$attemptId',
        params: { shotId, attemptId },
        replace: true,
      })
      return
    }
    void navigate({
      to: '/shots/$shotId/generations',
      params: { shotId },
      replace: true,
    })
  }, [attemptId, navigate, shotId])

  if (!shotId) {
    return (
      <section className="page" data-testid="review-page">
        <h1>{t('reviewTitle')}</h1>
        <p className="lede">{t('reviewEmpty')}</p>
        <button type="button" className="btn primary" onClick={() => navigate({ to: '/shots' })}>
          {t('openShotStudio')}
        </button>
      </section>
    )
  }

  return (
    <section className="page" data-testid="review-page">
      <p className="meta">{t('loading', { defaultValue: '…' })}</p>
    </section>
  )
}
