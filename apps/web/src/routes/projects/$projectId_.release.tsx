import { createFileRoute } from '@tanstack/react-router'
import { ReleasePage } from '../../views/ReleasePage'
export const Route = createFileRoute('/projects/$projectId_/release')({ component: ReleasePage })
