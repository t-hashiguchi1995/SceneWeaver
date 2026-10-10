import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'

import { api } from '../../lib/api'

export const Route = createFileRoute('/projects/')({
  component: ProjectsPage,
})

function ProjectsPage() {
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
      <h1>Projects</h1>
      <form
        className="inline-form"
        onSubmit={(e) => {
          e.preventDefault()
          if (title.trim()) create.mutate()
        }}
      >
        <input
          data-testid="project-title-input"
          aria-label="New project title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="New project title"
        />
        <button
          type="submit"
          className="btn primary"
          data-testid="project-create-button"
          disabled={create.isPending}
        >
          Create
        </button>
      </form>
      {projects.isLoading && <p>Loading…</p>}
      {projects.error && <p className="error">{(projects.error as Error).message}</p>}
      <ul className="list" data-testid="project-list">
        {(projects.data ?? []).map((p) => (
          <li key={p.id} data-testid="project-item">
            <Link to="/projects/$projectId" params={{ projectId: p.id }}>
              {p.title}
            </Link>
            <span className="meta">{p.status}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}