import { useQuery } from '@tanstack/react-query'
import { createFileRoute, Link } from '@tanstack/react-router'
import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'

import { formatDateTime, formatStatus } from '../../i18n/format'
import { api, saveStudioContext } from '../../lib/api'

export const Route = createFileRoute('/projects/$projectId')({
  component: ProjectDetailPage,
})

function ProjectDetailPage() {
  const { t, i18n } = useTranslation(['project', 'common'])
  const { projectId } = Route.useParams()
  const project = useQuery({
    queryKey: ['projects', projectId],
    queryFn: () => api.getProject(projectId),
  })

  const dashboard = useQuery({ queryKey: ['project-dashboard', projectId], queryFn: () => api.projectDashboard(projectId) })
  useEffect(() => { saveStudioContext({ projectId }) }, [projectId])

  if (project.isLoading) return <p>{t('common:loading')}</p>
  if (project.error) return <p className="error">{(project.error as Error).message}</p>
  if (!project.data) return <p>{t('common:notFound')}</p>

  const p = project.data
  return (
    <section className="page">
      <p className="eyebrow">{t('project:title')}</p>
      <h1>{p.title}</h1>
      {dashboard.error && <p role="alert">{dashboard.error.message}</p>}
      {dashboard.data && <>
        <div className="dashboard-metrics">{Object.entries(dashboard.data.counts).map(([key, count]) => <article className="panel-card" key={key}><h2>{t(`project:counts.${key}`)}</h2><strong>{count}</strong></article>)}</div>
        <div className="creator-columns">
          <article className="panel-card"><h2>{t('project:nextActions')}</h2><ul className="list">{dashboard.data.next_actions.map((action, index) => <li key={index}>
            <span>{t(`project:actions.${action.kind}`)}</span>
            {action.shot_id ? <Link className="btn" to={action.attempt_id ? '/projects/$projectId/shots/$shotId/generations/$attemptId' : '/projects/$projectId/shots/$shotId'} params={{ projectId, shotId: action.shot_id, attemptId: action.attempt_id ?? '' }}>{t('common:actions.open')}</Link> : <Link className="btn" to="/projects/$projectId/story" params={{ projectId }} search={{ sceneId: action.scene_id, beatId: action.beat_id }}>{t('common:actions.open')}</Link>}
          </li>)}</ul></article>
          <article className="panel-card"><h2>{t('project:recentShots')}</h2><ul className="list">{dashboard.data.recent_shots.map((shot, index) => <li key={shot.id}><Link to="/projects/$projectId/shots/$shotId" params={{ projectId, shotId: shot.id }}>Shot {index + 1}</Link><span>{shot.prompt_stale ? t('project:actions.prompt_stale') : `r${shot.revision}`}</span></li>)}</ul><h3>CLIP STUDIO</h3><p>{dashboard.data.latest_handoff?.revision ?? '—'}</p><Link className="btn" to="/projects/$projectId/csp" params={{ projectId }}>CLIP STUDIO</Link></article>
        </div>
      </>}
      <details><summary>{t('project:metadata')}</summary><dl className="kv">
        <dt>{t('project:status')}</dt>
        <dd>{formatStatus(t, p.status)}</dd>
        <dt>{t('project:rating')}</dt>
        <dd>{p.content_rating}</dd>
        <dt>{t('project:createdAt')}</dt>
        <dd>{formatDateTime(p.created_at, i18n.language)}</dd>
        <dt>{t('project:updatedAt')}</dt>
        <dd>{formatDateTime(p.updated_at, i18n.language)}</dd>
        <dt>{t('project:id')}</dt>
        <dd>
          <code>{p.id}</code>
        </dd>
      </dl></details>
    </section>
  )
}
