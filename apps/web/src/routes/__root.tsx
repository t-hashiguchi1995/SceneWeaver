import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Link, Outlet, createRootRoute, useParams } from '@tanstack/react-router'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { StudioIcon } from '../components/StudioIcon'
import { JobsIndicator } from '../components/JobsIndicator'

const queryClient = new QueryClient()

export const Route = createRootRoute({
  component: RootLayout,
})

function RootLayout() {
  const { projectId } = useParams({ strict: false })
  const [menuOpen, setMenuOpen] = useState(false)
  const { t } = useTranslation('common')
  const [mobile, setMobile] = useState(() => window.matchMedia('(max-width: 799px)').matches)
  const drawer = useRef<HTMLDialogElement>(null)
  const menuButton = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    const media = window.matchMedia('(max-width: 799px)')
    const update = () => { setMobile(media.matches); setMenuOpen(false) }
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])
  useEffect(() => {
    if (mobile && menuOpen) drawer.current?.showModal()
    else drawer.current?.close()
  }, [mobile, menuOpen])

  const navigation = (
<nav id="studio-navigation" className={menuOpen ? 'is-open' : ''} aria-label={t('shell.navigation')} onClick={(event) => { if ((event.target as HTMLElement).closest('a')) setMenuOpen(false) }}>
            <Link to="/" activeOptions={{ exact: true }} data-testid="nav-home-link" aria-label={t("nav.home")} title={t("nav.home")}>
<StudioIcon name="home" /><span>{t('nav.home')}</span>
            </Link>
            <p className="nav-group">{t('shell.create')}</p>
            <Link to="/projects" activeOptions={{ exact: true }} data-testid="nav-projects" aria-label={t("nav.projects")} title={t("nav.projects")}>
<StudioIcon name="projects" /><span>{t('nav.projects')}</span>
            </Link>
            <Link to="/characters" activeOptions={{ exact: true }} data-testid="nav-characters" aria-label={t("nav.characters")} title={t("nav.characters")}>
<StudioIcon name="characters" /><span>{t('nav.characters')}</span>
            </Link>
            {projectId && <>
              <p className="nav-group"><span>{t('shell.projectWorkspace')}</span></p>
              <Link to="/projects/$projectId" params={{ projectId }} activeOptions={{ exact: true }} data-testid="nav-overview" aria-label={t("shell.overview")} title={t("shell.overview")}><StudioIcon name="projects" /><span>{t('shell.overview')}</span></Link>
              <Link to="/projects/$projectId/story" params={{ projectId }} data-testid="nav-story" aria-label={t("nav.story")} title={t("nav.story")}><StudioIcon name="story" /><span>{t('nav.story')}</span></Link>
              <Link to="/projects/$projectId/wardrobe" params={{ projectId }} data-testid="nav-wardrobe" aria-label={t("nav.wardrobe")} title={t("nav.wardrobe")}><StudioIcon name="wardrobe" /><span>{t('nav.wardrobe')}</span></Link>
              <Link to="/projects/$projectId/shots" params={{ projectId }} data-testid="nav-shots" aria-label={t("nav.shots")} title={t("nav.shots")}><StudioIcon name="shots" /><span>{t('nav.shots')}</span></Link>
              <Link to="/projects/$projectId/csp" params={{ projectId }} data-testid="nav-csp" aria-label={t("nav.csp")} title={t("nav.csp")}><StudioIcon name="csp" /><span>{t('nav.csp')}</span></Link>
              <Link to="/projects/$projectId/release" params={{ projectId }} data-testid="nav-release" aria-label={t("nav.release")} title={t("nav.release")}><StudioIcon name="release" /><span>{t('nav.release')}</span></Link>
            </>}
            <p className="nav-group">{t('shell.system')}</p>
            <Link to="/integrations" activeOptions={{ exact: true }} data-testid="nav-integrations" aria-label={t("nav.integrations")} title={t("nav.integrations")}>
<StudioIcon name="integrations" /><span>{t('nav.integrations')}</span>
            </Link>
            <Link to="/settings" activeOptions={{ exact: true }} data-testid="nav-settings" aria-label={t("nav.settings")} title={t("nav.settings")}>
<StudioIcon name="settings" /><span>{t('nav.settings')}</span>
            </Link>

          </nav>
  )

  return (
    <QueryClientProvider client={queryClient}>
      <div className={menuOpen ? "app-shell is-expanded" : "app-shell"} data-testid="app-shell">
        <a className="skip-link" href="#main-content">{t('shell.skip')}</a>
        <header className="topbar">
          <Link to="/" className="brand" data-testid="nav-home">
            <span className="brand-mark" aria-hidden="true">S</span><span className="brand-name">{t('appName')}</span>
          </Link>
          <button ref={menuButton} className="menu-toggle btn" aria-expanded={menuOpen} aria-controls="studio-navigation" onClick={() => setMenuOpen(!menuOpen)}>{t('shell.menu')}</button>
          {mobile ? <dialog ref={drawer} className="navigation-drawer" aria-label={t('shell.navigation')} onClose={() => setMenuOpen(false)}>
            <button type="button" className="btn" autoFocus onClick={() => setMenuOpen(false)}>{t('actions.close')}</button>
            {navigation}
          </dialog> : navigation}
        </header>
        <main className="main" id="main-content" tabIndex={-1}>
          <div className="workspace-header"><span>{projectId ? t("shell.projectWorkspace") : t("shell.workspace")}</span><JobsIndicator /></div>
          <Outlet />
        </main>
      </div>
    </QueryClientProvider>
  )
}
