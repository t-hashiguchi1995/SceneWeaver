import { createFileRoute } from '@tanstack/react-router'
import { StoryPage } from '../../views/StoryPage'
export const Route = createFileRoute('/projects/$projectId_/story')({
  validateSearch: (search: Record<string, unknown>): { sceneId?: string; beatId?: string } => ({ sceneId: typeof search.sceneId === 'string' ? search.sceneId : undefined, beatId: typeof search.beatId === 'string' ? search.beatId : undefined }),
  component: Page,
})
function Page() { const { projectId } = Route.useParams(); return <StoryPage key={projectId} /> }
