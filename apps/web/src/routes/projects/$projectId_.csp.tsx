import { createFileRoute } from '@tanstack/react-router'
import { CspPage } from '../../views/CspPage'
export const Route = createFileRoute('/projects/$projectId_/csp')({ component: CspPage })
