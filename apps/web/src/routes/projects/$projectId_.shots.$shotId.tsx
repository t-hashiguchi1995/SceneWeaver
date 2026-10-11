import { createFileRoute, Outlet, useLocation } from '@tanstack/react-router'
import { ShotStudioPage } from '../../views/ShotStudioPage'
import { ProjectShotBoundary } from '../../components/ProjectShotBoundary'
export const Route = createFileRoute('/projects/$projectId_/shots/$shotId')({ validateSearch: (search: Record<string, unknown>): { sourceAttemptId?: string } => ({ sourceAttemptId: typeof search.sourceAttemptId === "string" ? search.sourceAttemptId : undefined }), component: Page })
function Page() { const { projectId, shotId } = Route.useParams(); const location = useLocation(); if (location.pathname.includes('/generations')) return <Outlet />; return <ProjectShotBoundary projectId={projectId} shotId={shotId}><ShotStudioPage key={shotId} /></ProjectShotBoundary> }
