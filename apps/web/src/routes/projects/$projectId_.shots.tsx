import { createFileRoute, Outlet, useLocation } from '@tanstack/react-router'

import { ShotsEntryPage } from '../../views/ShotsEntryPage'

export const Route = createFileRoute('/projects/$projectId_/shots')({
  validateSearch: (search: Record<string, unknown>): { beatId?: string } => ({
    beatId: typeof search.beatId === 'string' ? search.beatId : undefined,
  }),
  component: Page,
})

function Page() {
  const match = useLocation()
  return match.pathname.endsWith('/shots') ? <ShotsEntryPage /> : <Outlet />
}
