import { createFileRoute } from '@tanstack/react-router'
import { ShotsEntryPage } from '../../views/ShotsEntryPage'

export const Route = createFileRoute('/shots/')({
  component: ShotsEntryPage,
})
