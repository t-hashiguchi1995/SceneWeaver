import { createFileRoute } from '@tanstack/react-router'
import { WardrobePage } from '../../views/WardrobePage'
export const Route = createFileRoute('/projects/$projectId_/wardrobe')({ component: Page })

function Page() { const { projectId } = Route.useParams(); return <WardrobePage key={projectId} /> }
