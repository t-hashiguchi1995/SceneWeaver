import { createFileRoute, Outlet, useLocation } from '@tanstack/react-router'
import { GenerationReviewView } from '../../components/GenerationReviewView'
import { ProjectShotBoundary } from '../../components/ProjectShotBoundary'
export const Route = createFileRoute('/projects/$projectId_/shots/$shotId/generations')({ component: Page })
function Page() { const params = Route.useParams(); const location = useLocation(); if (!location.pathname.endsWith('/generations')) return <Outlet />; return <ProjectShotBoundary projectId={params.projectId} shotId={params.shotId}><GenerationReviewView {...params} /></ProjectShotBoundary> }
