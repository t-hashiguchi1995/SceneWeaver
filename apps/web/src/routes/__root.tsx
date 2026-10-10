import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Link, Outlet, createRootRoute } from '@tanstack/react-router'

const queryClient = new QueryClient()

export const Route = createRootRoute({
  component: RootLayout,
})

function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="app-shell" data-testid="app-shell">
        <header className="topbar">
          <Link to="/" className="brand" data-testid="nav-home">
            SceneWeaver
          </Link>
          <nav>
            <Link to="/" data-testid="nav-home-link">
              Home
            </Link>
            <Link to="/projects" data-testid="nav-projects">
              Projects
            </Link>
            <Link to="/story" data-testid="nav-story">
              Story
            </Link>
            <Link to="/wardrobe" data-testid="nav-wardrobe">
              Wardrobe
            </Link>
            <Link to="/shots" data-testid="nav-shots">
              Shots
            </Link>
            <Link to="/csp" data-testid="nav-csp">
              CSP
            </Link>
            <Link to="/release" data-testid="nav-release">
              Release
            </Link>
            <Link to="/jobs" data-testid="nav-jobs">
              Jobs
            </Link>
            <Link to="/capabilities" data-testid="nav-capabilities">
              Capabilities
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