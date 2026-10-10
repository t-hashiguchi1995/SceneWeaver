import { useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { useTranslation } from 'react-i18next'

import { formatDateTime, formatStatus } from '../../i18n/format'
import { api } from '../../lib/api'

export const Route = createFileRoute('/projects/$projectId')({
  component: ProjectDetailPage,
})

function ProjectDetailPage() {
  const { t, i18n } = useTranslation(['project', 'common'])
  const { projectId } = Route.useParams()
  const project = useQuery({
    queryKey: ['projects', projectId],
    queryFn: () => api.getProject(projectId),
  })

  if (project.isLoading) return <p>{t('common:loading')}</p>
  if (project.error) return <p className="error">{(project.error as Error).message}</p>
  if (!project.data) return <p>{t('common:notFound')}</p>

  const p = project.data
  return (
    <section className="page">
      <p className="eyebrow">{t('project:title')}</p>
      <h1>{p.title}</h1>
      <dl className="kv">
        <dt>{t('project:status')}</dt>
        <dd>{formatStatus(t, p.status)}</dd>
        <dt>{t('project:rating')}</dt>
        <dd>{p.content_rating}</dd>
        <dt>{t('project:createdAt')}</dt>
        <dd>{formatDateTime(p.created_at, i18n.language)}</dd>
        <dt>{t('project:updatedAt')}</dt>
        <dd>{formatDateTime(p.updated_at, i18n.language)}</dd>
        <dt>{t('project:id')}</dt>
        <dd>
          <code>{p.id}</code>
        </dd>
      </dl>
      <p className="hint">{t('project:detailHint')}</p>
    </section>
  )
}
