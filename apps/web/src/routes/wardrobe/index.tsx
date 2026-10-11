import { createFileRoute } from '@tanstack/react-router'
import { WardrobePage } from '../../views/WardrobePage'

export const Route = createFileRoute('/wardrobe/')({
  component: WardrobePage,
})
