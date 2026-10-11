import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import type { ReactNode } from 'react'
import { api } from '../lib/api'
export function ProjectShotBoundary({ projectId, shotId, children }: { projectId: string; shotId: string; children: ReactNode }) {
  const { t } = useTranslation('common')
  const query = useQuery({ queryKey: ['project-dashboard', projectId], queryFn: () => api.projectDashboard(projectId) })
  if (query.error) return <p role="alert">{query.error.message}</p>
  if (!query.data) return <p>{t('loading')}</p>
  if (!query.data.recent_shots.some((shot) => shot.id === shotId)) return <p role="alert">{t('notFound')}</p>
  return children
}
