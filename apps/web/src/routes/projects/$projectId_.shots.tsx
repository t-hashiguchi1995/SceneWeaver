import { createFileRoute, Outlet, useLocation } from '@tanstack/react-router'
import { ShotsEntryPage } from '../../views/ShotsEntryPage'
export const Route = createFileRoute('/projects/$projectId_/shots')({ component: Page })
function Page() { const match = useLocation(); return match.pathname.endsWith('/shots') ? <ShotsEntryPage /> : <Outlet /> }
