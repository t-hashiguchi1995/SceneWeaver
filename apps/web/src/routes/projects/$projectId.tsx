import { useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'

import { api } from '../../lib/api'

export const Route = createFileRoute('/projects/$projectId')({
  component: ProjectDetailPage,
})

function ProjectDetailPage() {
  const { projectId } = Route.useParams()
  const project = useQuery({
    queryKey: ['projects', projectId],
    queryFn: () => api.getProject(projectId),
  })

  if (project.isLoading) return <p>Loading…</p>
  if (project.error) return <p className="error">{(project.error as Error).message}</p>
  if (!project.data) return <p>Not found</p>

  const p = project.data
  return (
    <section className="page">
      <p className="eyebrow">Project</p>
      <h1>{p.title}</h1>
      <dl className="kv">
        <dt>Status</dt>
        <dd>{p.status}</dd>
        <dt>Rating</dt>
        <dd>{p.content_rating}</dd>
        <dt>ID</dt>
        <dd>
          <code>{p.id}</code>
        </dd>
      </dl>
      <p className="hint">Story / Wardrobe / Shot screens arrive in later milestones.</p>
    </section>
  )
}