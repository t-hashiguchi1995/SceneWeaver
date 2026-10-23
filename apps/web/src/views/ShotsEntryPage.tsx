import { useMutation, useQuery } from '@tanstack/react-query'
import { Link, useNavigate, useParams, useSearch } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { ErrorBanner } from '../components/ErrorBanner'
import { ProjectContextBar } from '../components/ProjectContextBar'
import { api, loadStudioContext, saveStudioContext } from '../lib/api'

export function ShotsEntryPage() {
  const { t } = useTranslation(['generation', 'common'])
  const navigate = useNavigate()
  const { projectId } = useParams({ strict: false })
  const search = useSearch({ strict: false }) as { beatId?: string }
  const ctx = projectId ? {} : loadStudioContext()
  const dashboard = useQuery({
    queryKey: ['project-dashboard', projectId],
    queryFn: () => api.projectDashboard(projectId!),
    enabled: Boolean(projectId),
  })
  const [beatId, setBeatId] = useState(search.beatId ?? ctx.beatId ?? '')
  const [error, setError] = useState('')

  useEffect(() => {
    if (search.beatId) setBeatId(search.beatId)
  }, [search.beatId])

  const plan = useMutation({
    mutationFn: () => api.planShot(beatId),
    onSuccess: async (shot) => {
      saveStudioContext({ shotId: shot.id, beatId })
      await api.ensurePromptDraft(shot.id)
      void navigate({
        to: projectId ? '/projects/$projectId/shots/$shotId' : '/shots/$shotId',
        params: { projectId: projectId ?? '', shotId: shot.id },
      })
    },
    onError: (err) => setError((err as Error).message),
  })

  return (
    <section className="page" data-testid="shots-entry-page">
      {projectId && <ProjectContextBar beatId={beatId || undefined} strict />}
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
          {projectId ? (
            <select
              data-testid="shot-beat-id"
              value={beatId}
              onChange={(e) => setBeatId(e.target.value)}
            >
              <option value="">—</option>
              {dashboard.data?.beats.map((beat) => (
                <option key={beat.id} value={beat.id}>
                  {beat.intent}
                </option>
              ))}
            </select>
          ) : (
            <input
              aria-label={t('generation:beatId')}
              data-testid="shot-beat-id"
              value={beatId}
              onChange={(e) => setBeatId(e.target.value)}
            />
          )}
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

      {projectId && (
        <ul className="list">
          {dashboard.data?.recent_shots.map((shot, index) => (
            <li key={shot.id}>
              <Link
                to="/projects/$projectId/shots/$shotId"
                params={{ projectId, shotId: shot.id }}
              >
                Shot {index + 1}
              </Link>
            </li>
          ))}
        </ul>
      )}
      {error && <ErrorBanner message={error} />}
    </section>
  )
}
