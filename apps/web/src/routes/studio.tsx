import { createFileRoute } from '@tanstack/react-router'

import { ImageStudioPage } from '../views/ImageStudioPage'

export const Route = createFileRoute('/studio')({
  component: ImageStudioPage,
})
