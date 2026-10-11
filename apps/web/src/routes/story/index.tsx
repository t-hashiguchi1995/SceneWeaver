import { createFileRoute } from '@tanstack/react-router'
import { StoryPage } from '../../views/StoryPage'

export const Route = createFileRoute('/story/')({
  component: StoryPage,
})
