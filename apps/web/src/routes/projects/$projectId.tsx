import { useQuery } from '@tanstack/react-query'
import { createFileRoute, Link } from '@tanstack/react-router'
import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'

import { formatDateTime, formatStatus } from '../../i18n/format'
import { api, saveStudioContext } from '../../lib/api'
import { primaryNextLink, stageStatus } from '../../lib/workflow'

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

  const dashboard = useQuery({
    queryKey: ['project-dashboard', projectId],
    queryFn: () => api.projectDashboard(projectId),
  })
  useEffect(() => {
    saveStudioContext({ projectId })
  }, [projectId])

  if (project.isLoading) return <p>{t('common:loading')}</p>
  if (project.error) return <p className="error">{(project.error as Error).message}</p>
  if (!project.data) return <p>{t('common:notFound')}</p>

  const p = project.data
  const workflow = dashboard.data?.workflow
  const primary = workflow?.primary_next
  const primaryLink = primary ? primaryNextLink(projectId, primary) : null
  const storyState = workflow ? stageStatus(workflow.story.done, workflow.story.total) : 'not_started'
  const shotsState = workflow ? stageStatus(workflow.shots.done, workflow.shots.total) : 'not_started'

  return (
    <section className="page" data-testid="project-dashboard">
      <p className="eyebrow">{t('project:title')}</p>
      <h1>{p.title}</h1>
      {dashboard.error && <p role="alert">{dashboard.error.message}</p>}
      {dashboard.data && workflow && (
        <>
          <article className="panel-card workflow-summary" data-testid="project-workflow">
            <h2>{t('project:workflowTitle')}</h2>
            <ol className="workflow-stages">
              <li data-testid="workflow-stage-story" data-status={storyState} data-step="1">
                <span className="workflow-step" aria-hidden="true">
                  1
                </span>
                <strong>{t('project:stages.story')}</strong>
                <span>{t('project:progressCount', workflow.story)}</span>
                <span className="meta">{t(`project:stageStatus.${storyState}`)}</span>
              </li>
              <li data-testid="workflow-stage-shots" data-status={shotsState} data-step="2">
                <span className="workflow-step" aria-hidden="true">
                  2
                </span>
                <strong>{t('project:stages.shots')}</strong>
                <span>{t('project:progressCount', workflow.shots)}</span>
                <span className="meta">{t(`project:stageStatus.${shotsState}`)}</span>
              </li>
              <li
                data-testid="workflow-stage-csp"
                data-status={workflow.csp.done ? 'complete' : 'not_started'}
                data-step="3"
              >
                <span className="workflow-step" aria-hidden="true">
                  3
                </span>
                <strong>{t('project:stages.csp')}</strong>
                <span className="meta">
                  {workflow.csp.done
                    ? t('project:stageStatus.csp_done')
                    : t('project:stageStatus.csp_pending')}
                </span>
              </li>
              <li
                data-testid="workflow-stage-release"
                data-status={workflow.release.ready ? 'ready' : 'waiting'}
                data-step="4"
              >
                <span className="workflow-step" aria-hidden="true">
                  4
                </span>
                <strong>{t('project:stages.release')}</strong>
                <span className="meta">
                  {workflow.release.ready
                    ? t('project:stageStatus.ready')
                    : t('project:stageStatus.release_after_csp')}
                </span>
              </li>
            </ol>
          </article>

          {primary && primaryLink && (
            <article className="panel-card workflow-primary" data-testid="project-primary-next">
              <h2>{t('project:primaryNext')}</h2>
              <p>{t(`project:primary.${primary.kind}`)}</p>
              {primary.kind !== 'complete' && (
                <Link
                  className="btn primary"
                  to={primaryLink.to}
                  params={primaryLink.params}
                  search={'search' in primaryLink ? primaryLink.search : undefined}
                  data-testid="project-primary-next-action"
                >
                  {t(`project:primary.${primary.kind}`)}
                </Link>
              )}
            </article>
          )}

          <div className="dashboard-metrics">
            {Object.entries(dashboard.data.counts).map(([key, count]) => (
              <article className="panel-card" key={key}>
                <h2>{t(`project:counts.${key}`)}</h2>
                <strong>{count}</strong>
              </article>
            ))}
          </div>
          <div className="creator-columns">
            {dashboard.data.next_actions.length > 0 && (
              <article className="panel-card" data-testid="project-next-actions">
                <h2>{t('project:nextActions')}</h2>
                <ul className="list">
                  {dashboard.data.next_actions.map((action, index) => (
                    <li key={index}>
                      <span>{t(`project:actions.${action.kind}`)}</span>
                      {action.shot_id ? (
                        <Link
                          className="btn"
                          to={
                            action.attempt_id
                              ? '/projects/$projectId/shots/$shotId/generations/$attemptId'
                              : '/projects/$projectId/shots/$shotId'
                          }
                          params={{
                            projectId,
                            shotId: action.shot_id,
                            attemptId: action.attempt_id ?? '',
                          }}
                        >
                          {t('common:actions.open')}
                        </Link>
                      ) : (
                        <Link
                          className="btn"
                          to="/projects/$projectId/story"
                          params={{ projectId }}
                          search={{ sceneId: action.scene_id, beatId: action.beat_id }}
                        >
                          {t('common:actions.open')}
                        </Link>
                      )}
                    </li>
                  ))}
                </ul>
              </article>
            )}
            <article className="panel-card">
              <h2>{t('project:recentShots')}</h2>
              <ul className="list">
                {dashboard.data.recent_shots.map((shot, index) => (
                  <li key={shot.id}>
                    <Link
                      to="/projects/$projectId/shots/$shotId"
                      params={{ projectId, shotId: shot.id }}
                    >
                      Shot {index + 1}
                    </Link>
                    <span>
                      {shot.prompt_stale ? t('project:actions.prompt_stale') : `r${shot.revision}`}
                    </span>
                  </li>
                ))}
              </ul>
              <h3>CLIP STUDIO</h3>
              <p>{dashboard.data.latest_handoff?.revision ?? '—'}</p>
              <Link className="btn" to="/projects/$projectId/csp" params={{ projectId }}>
                CLIP STUDIO
              </Link>
            </article>
          </div>
        </>
      )}
      <details>
        <summary>{t('project:metadata')}</summary>
        <dl className="kv">
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
        </dl>
      </details>
    </section>
  )
}
