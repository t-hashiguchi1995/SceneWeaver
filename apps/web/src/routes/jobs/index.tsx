import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { useJobEvents } from '../../hooks/useJobEvents'
import { formatDateTime, formatStatus } from '../../i18n/format'
import { api } from '../../lib/api'

export const Route = createFileRoute('/jobs/')({
  component: JobsPage,
})

function JobsPage() {
  const { t, i18n } = useTranslation(['jobs', 'common'])
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
        <h1>{t('jobs:title')}</h1>
        <button
          type="button"
          className="btn primary"
          data-testid="job-enqueue-stub"
          onClick={() => enqueue.mutate()}
        >
          {t('jobs:enqueueStub')}
        </button>
      </div>
      {watchId && (
        <p className="hint" data-testid="job-watching">
          {t('jobs:watching', { id: watchId })}
        </p>
      )}
      {watched.data && (
        <p data-testid="job-live-status">
          {t('jobs:live')}:{' '}
          <span data-testid="job-live-status-label">{formatStatus(t, watched.data.status)}</span>
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
              {formatStatus(t, j.status)}
            </span>
            <span className="meta">{t('jobs:attempts', { n: j.attempts })}</span>
            <span className="meta">{formatDateTime(j.updated_at, i18n.language)}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}
