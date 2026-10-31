import { useQuery } from '@tanstack/react-query'
import { Link, createFileRoute } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

import { StudioIcon } from '../components/StudioIcon'
import { formatStatus } from '../i18n/format'
import { api, type Project } from '../lib/api'

export const Route = createFileRoute('/')({
  component: HomePage,
})

function HomePage() {
  const { t } = useTranslation(['home', 'common'])
  const setup = useQuery({ queryKey: ['setup-status'], queryFn: api.setupStatus })
  const settings = useQuery({ queryKey: ['settings'], queryFn: api.getSettings })
  const projects = useQuery({ queryKey: ['projects'], queryFn: api.listProjects })

  const projectList = [...(projects.data ?? [])].sort((a, b) => b.updated_at.localeCompare(a.updated_at))
  const recentIds = settings.data?.recent_project_ids ?? []
  const byId = new Map(projectList.map((p) => [p.id, p]))
  const orderedRecent: Project[] =
    recentIds.length > 0
      ? recentIds.map((id) => byId.get(id)).filter((p): p is Project => p != null).slice(0, 5)
      : projectList.slice(0, 5)

  const jobs = useQuery({ queryKey: ['jobs'], queryFn: api.listJobs, refetchInterval: 5000 })
  if (orderedRecent.length === 0) orderedRecent.push(...projectList.slice(0, 5))
  const activeJobs = jobs.data?.filter((job) => job.status === 'running' || job.status === 'queued').length

  const continueProject =
    (recentIds[0] ? byId.get(recentIds[0]) : undefined) ?? projectList[0] ?? null

  return (
    <section className="page home">
      <div className="home-header">
        <div>
          <p className="eyebrow">{t('home:eyebrow')}</p>
          <h1>{t('home:title')}</h1>
          <p className="lede">{t('home:lede')}</p>
        </div>
        <Link to="/projects" className="btn primary">
          ＋ {t('home:newProject')}
        </Link>
      </div>

      {setup.isSuccess && !setup.data.setup_completed && (
        <div className="banner" data-testid="setup-banner">
          <p>{t('home:setupBanner')}</p>
          <Link to="/setup" className="btn primary" data-testid="home-open-setup">
            {t('home:openSetup')}
          </Link>
        </div>
      )}

      <h2>{t('home:intentHeading')}</h2>
      <div className="intent-grid" data-testid="home-intent-cards">
        {continueProject ? (
          <Link
            className="panel-card intent-card"
            to="/projects/$projectId"
            params={{ projectId: continueProject.id }}
            data-testid="home-intent-continue"
          >
            <h3>{t('home:continueProject')}</h3>
            <p>{t('home:continueProjectHint', { title: continueProject.title })}</p>
          </Link>
        ) : (
          <Link className="panel-card intent-card" to="/projects" data-testid="home-intent-create">
            <h3>{t('home:createProject')}</h3>
            <p>{t('home:createProjectHint')}</p>
          </Link>
        )}
        <Link className="panel-card intent-card" to="/studio" data-testid="home-intent-quick-test">
          <h3>{t('home:quickTestTitle')}</h3>
          <p>{t('home:quickTestHint')}</p>
        </Link>
        <Link
          className="panel-card intent-card"
          to="/visual-library"
          data-testid="home-intent-visual-library"
        >
          <h3>{t('home:visualLibraryTitle')}</h3>
          <p>{t('home:visualLibraryHint')}</p>
        </Link>
      </div>

      <div className="dashboard-stats">
        {[
          { query: projects, value: projects.data?.length, label: 'projectCount', to: '/projects' as const },
          { query: jobs, value: activeJobs, label: 'activeJobs', to: '/jobs' as const },
        ].map(({ query, value, label, to }) => (
          <Link className="stat-card" to={to} key={label}>
            <strong>{query.isError ? '—' : (value ?? '…')}</strong>
            <span>{t(`home:${label}`)}</span>
          </Link>
        ))}
      </div>
      {[setup, settings, projects, jobs].some((query) => query.isError) && (
        <div className="banner" role="alert">
          <p>{t('home:loadError')}</p>
          <button
            className="btn"
            onClick={() => {
              for (const query of [setup, settings, projects, jobs]) {
                if (query.isError) void query.refetch()
              }
            }}
          >
            {t('home:retry')}
          </button>
        </div>
      )}
      <div className="dashboard-columns">
        <div className="workspace-panel">
          <h2>{t('home:recentProjects')}</h2>
          <ul className="list" data-testid="recent-projects">
            {projects.isPending && <li className="meta">{t('common:loading')}</li>}
            {projects.isSuccess && orderedRecent.length === 0 && (
              <li className="empty-state">
                <StudioIcon name="projects" />
                <strong>{t('home:noProjects')}</strong>
                <p>{t('home:emptyProjectHint')}</p>
                <Link to="/projects" className="btn">
                  {t('home:newProject')}
                </Link>
              </li>
            )}
            {orderedRecent.map((p) => (
              <li key={p.id}>
                <Link to="/projects/$projectId" params={{ projectId: p.id }}>
                  {p.title}
                </Link>
                <span className="meta">{formatStatus(t, p.status)}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="workspace-panel">
          <h2>{t('home:activeJobs')}</h2>
          <ul className="list" data-testid="home-jobs">
            {(jobs.data ?? [])
              .filter((job) => ['queued', 'running', 'failed'].includes(job.status))
              .map((job) => (
                <li key={job.id}>
                  <strong>{job.kind}</strong>
                  <span>{formatStatus(t, job.status)}</span>
                  {job.error_message && <span>{job.error_message}</span>}
                </li>
              ))}
            {jobs.isSuccess &&
              !jobs.data.some((job) => ['queued', 'running', 'failed'].includes(job.status)) && (
                <li className="empty-state">{t('home:noPendingJobs')}</li>
              )}
          </ul>
        </div>
      </div>
    </section>
  )
}
