import { createFileRoute } from '@tanstack/react-router'
import { ShotStudioPage } from '../../../views/ShotStudioPage'

export const Route = createFileRoute('/shots/$shotId/')({
  validateSearch: (search: Record<string, unknown>): { sourceAttemptId?: string } => ({ sourceAttemptId: typeof search.sourceAttemptId === "string" ? search.sourceAttemptId : undefined }),
  component: ShotStudioPage,
})
