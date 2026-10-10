import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Link, Outlet, createRootRoute, useNavigate } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

import { loadStudioContext } from '../lib/api'

const queryClient = new QueryClient()

export const Route = createRootRoute({
  component: RootLayout,
})

function ReviewNavLink() {
  const { t } = useTranslation('common')
  const navigate = useNavigate()
  return (
    <Link
      to="/review"
      data-testid="nav-review"
      onClick={(e) => {
        const ctx = loadStudioContext()
        if (!ctx.shotId) return
        e.preventDefault()
        if (ctx.generationAttemptId) {
          void navigate({
            to: '/shots/$shotId/generations/$attemptId',
            params: { shotId: ctx.shotId, attemptId: ctx.generationAttemptId },
          })
        } else {
          void navigate({
            to: '/shots/$shotId/generations',
            params: { shotId: ctx.shotId },
          })
        }
      }}
    >
      {t('nav.review')}
    </Link>
  )
}

function RootLayout() {
  const { t } = useTranslation('common')

  return (
    <QueryClientProvider client={queryClient}>
      <div className="app-shell" data-testid="app-shell">
        <header className="topbar">
          <Link to="/" className="brand" data-testid="nav-home">
            {t('appName')}
          </Link>
          <nav>
            <Link to="/" data-testid="nav-home-link">
              {t('nav.home')}
            </Link>
            <Link to="/projects" data-testid="nav-projects">
              {t('nav.projects')}
            </Link>
            <Link to="/characters" data-testid="nav-characters">
              {t('nav.characters')}
            </Link>
            <Link to="/story" data-testid="nav-story">
              {t('nav.story')}
            </Link>
            <Link to="/wardrobe" data-testid="nav-wardrobe">
              {t('nav.wardrobe')}
            </Link>
            <Link to="/shots" data-testid="nav-shots">
              {t('nav.shots')}
            </Link>
            <ReviewNavLink />
            <Link to="/csp" data-testid="nav-csp">
              {t('nav.csp')}
            </Link>
            <Link to="/release" data-testid="nav-release">
              {t('nav.release')}
            </Link>
            <Link to="/integrations" data-testid="nav-integrations">
              {t('nav.integrations')}
            </Link>
            <Link to="/settings" data-testid="nav-settings">
              {t('nav.settings')}
            </Link>
            <Link to="/jobs" data-testid="nav-jobs">
              {t('nav.jobs')}
            </Link>
          </nav>
        </header>
        <main className="main">
          <Outlet />
        </main>
      </div>
    </QueryClientProvider>
  )
}
