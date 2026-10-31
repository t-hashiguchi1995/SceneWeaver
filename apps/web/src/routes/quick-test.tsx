import { createFileRoute, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/quick-test')({
  beforeLoad: () => {
    throw redirect({ to: '/studio' })
  },
})
