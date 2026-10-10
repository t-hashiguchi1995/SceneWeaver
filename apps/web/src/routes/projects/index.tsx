import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { formatStatus } from '../../i18n/format'
import { api } from '../../lib/api'

export const Route = createFileRoute('/projects/')({
  component: ProjectsPage,
})

function ProjectsPage() {
  const { t } = useTranslation(['project', 'common'])
  const qc = useQueryClient()
  const [title, setTitle] = useState('')
  const projects = useQuery({ queryKey: ['projects'], queryFn: api.listProjects })
  const create = useMutation({
    mutationFn: () => api.createProject(title),
    onSuccess: async () => {
      setTitle('')
      await qc.invalidateQueries({ queryKey: ['projects'] })
    },
  })

  return (
    <section className="page" data-testid="projects-page">
      <h1>{t('project:title')}</h1>
      <form
        className="inline-form"
        onSubmit={(e) => {
          e.preventDefault()
          if (title.trim()) create.mutate()
        }}
      >
        <input
          data-testid="project-title-input"
          aria-label={t('project:newTitleAria')}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder={t('project:newTitlePlaceholder')}
        />
        <button
          type="submit"
          className="btn primary"
          data-testid="project-create-button"
          disabled={create.isPending}
        >
          {t('common:actions.create')}
        </button>
      </form>
      {projects.isLoading && <p>{t('common:loading')}</p>}
      {projects.error && <p className="error">{(projects.error as Error).message}</p>}
      <ul className="list" data-testid="project-list">
        {(projects.data ?? []).map((p) => (
          <li key={p.id} data-testid="project-item">
            <Link to="/projects/$projectId" params={{ projectId: p.id }}>
              {p.title}
            </Link>
            <span className="meta">{formatStatus(t, p.status)}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}
