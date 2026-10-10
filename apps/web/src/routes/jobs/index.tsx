import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'

import { useJobEvents } from '../../hooks/useJobEvents'
import { api } from '../../lib/api'

export const Route = createFileRoute('/jobs/')({
  component: JobsPage,
})

function JobsPage() {
  const qc = useQueryClient()
  const [watchId, setWatchId] = useState<string | null>(null)
  const jobs = useQuery({ queryKey: ['jobs'], queryFn: api.listJobs, refetchInterval: 500 })
  useJobEvents(watchId)
  const watched = useQuery({
    queryKey: ['jobs', watchId],
    queryFn: () => api.getJob(watchId!),
    enabled: !!watchId,
  })

  const enqueue = useMutation({
    mutationFn: () => api.enqueueStubJob({ source: 'ui' }),
    onSuccess: async (job) => {
      setWatchId(job.id)
      await qc.invalidateQueries({ queryKey: ['jobs'] })
    },
  })

  return (
    <section className="page" data-testid="jobs-page">
      <div className="row-between">
        <h1>Jobs</h1>
        <button
          type="button"
          className="btn primary"
          data-testid="job-enqueue-stub"
          onClick={() => enqueue.mutate()}
        >
          Enqueue stub job
        </button>
      </div>
      {watchId && (
        <p className="hint" data-testid="job-watching">
          Watching SSE for {watchId}
        </p>
      )}
      {watched.data && (
        <p data-testid="job-live-status">
          Live: <span data-testid="job-live-status-label">{statusLabel(watched.data.status)}</span>
        </p>
      )}
      <ul className="list" data-testid="job-list">
        {(jobs.data ?? []).map((j) => (
          <li key={j.id} data-testid="job-item">
            <button
              type="button"
              className="linkish"
              data-testid="job-kind"
              onClick={() => setWatchId(j.id)}
            >
              {j.kind}
            </button>
            <span className="meta" data-testid="job-status">
              {statusLabel(j.status)}
            </span>
            <span className="meta">attempts {j.attempts}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}

function statusLabel(status: string): string {
  switch (status) {
    case 'queued':
      return 'Queued'
    case 'running':
      return 'Running'
    case 'succeeded':
      return 'Succeeded'
    case 'failed':
      return 'Failed'
    case 'cancelled':
      return 'Cancelled'
    default:
      return status
  }
}
