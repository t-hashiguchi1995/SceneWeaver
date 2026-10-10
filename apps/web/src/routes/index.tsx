import { useQuery } from '@tanstack/react-query'
import { Link, createFileRoute } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

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
  const characters = useQuery({ queryKey: ['characters'], queryFn: api.listCharacters })

  const projectList = projects.data ?? []
  const recentIds = settings.data?.recent_project_ids ?? []
  const byId = new Map(projectList.map((p) => [p.id, p]))
  const orderedRecent: Project[] =
    recentIds.length > 0
      ? recentIds.map((id) => byId.get(id)).filter((p): p is Project => p != null)
      : projectList.slice(0, 5)

  const characterList = characters.data ?? []

  return (
    <section className="page home">
      <p className="eyebrow">{t('home:eyebrow')}</p>
      <h1>{t('common:appName')}</h1>
      <p className="lede">{t('home:lede')}</p>

      {!setup.data?.setup_completed && (
        <div className="banner" data-testid="setup-banner">
          <p>{t('home:setupBanner')}</p>
          <Link to="/setup" className="btn primary" data-testid="home-open-setup">
            {t('home:openSetup')}
          </Link>
        </div>
      )}

      <div className="cta-row">
        <Link to="/projects" className="btn primary">
          {t('common:nav.projects')}
        </Link>
        <Link to="/characters" className="btn">
          {t('common:nav.characters')}
        </Link>
        <Link to="/integrations" className="btn">
          {t('common:nav.integrations')}
        </Link>
        <Link to="/settings" className="btn">
          {t('common:nav.settings')}
        </Link>
      </div>

      <h2>{t('home:recentProjects')}</h2>
      <ul className="list" data-testid="recent-projects">
        {orderedRecent.length === 0 && <li className="meta">{t('home:noProjects')}</li>}
        {orderedRecent.map((p) => (
          <li key={p.id}>
            <Link to="/projects/$projectId" params={{ projectId: p.id }}>
              {p.title}
            </Link>
            <span className="meta">{formatStatus(t, p.status)}</span>
          </li>
        ))}
      </ul>

      <h2>{t('home:characters')}</h2>
      <ul className="list" data-testid="home-characters">
        {characterList.length === 0 && (
          <li className="meta">
            {t('home:noCharacters')} <Link to="/characters">{t('home:openLibrary')}</Link>
          </li>
        )}
        {characterList.slice(0, 5).map((c) => (
          <li key={c.id}>
            <Link to="/characters">{c.display_name}</Link>
          </li>
        ))}
      </ul>
    </section>
  )
}
