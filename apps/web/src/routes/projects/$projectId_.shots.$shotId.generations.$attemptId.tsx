import { createFileRoute } from '@tanstack/react-router'
import { GenerationReviewView } from '../../components/GenerationReviewView'
import { ProjectShotBoundary } from '../../components/ProjectShotBoundary'
export const Route = createFileRoute('/projects/$projectId_/shots/$shotId/generations/$attemptId')({ component: Page })
function Page() { const params = Route.useParams(); return <ProjectShotBoundary projectId={params.projectId} shotId={params.shotId}><GenerationReviewView {...params} /></ProjectShotBoundary> }
