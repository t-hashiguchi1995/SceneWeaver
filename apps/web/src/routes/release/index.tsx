import { createFileRoute } from '@tanstack/react-router'
import { ReleasePage } from '../../views/ReleasePage'

export const Route = createFileRoute('/release/')({
  component: ReleasePage,
})
