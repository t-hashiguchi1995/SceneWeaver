import { useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'

import { api, type Job } from '../lib/api'

/**
 * SSE job progress. On reconnect, refresh via GET /jobs/{id}.
 * Last-Event-ID is Post-MVP.
 */
export function useJobEvents(jobId: string | null) {
  const queryClient = useQueryClient()

  useEffect(() => {
    if (!jobId) return

    const refresh = () => {
      void api.getJob(jobId).then((job) => {
        queryClient.setQueryData(['jobs', jobId], job)
        void queryClient.invalidateQueries({ queryKey: ['jobs'] })
      })
    }

    refresh()
    const es = new EventSource(`/api/v1/jobs/${jobId}/events`)
    es.addEventListener('job', (ev) => {
      const job = JSON.parse((ev as MessageEvent).data) as Job
      queryClient.setQueryData(['jobs', jobId], job)
      void queryClient.invalidateQueries({ queryKey: ['jobs'] })
    })
    es.addEventListener('done', (ev) => {
      const job = JSON.parse((ev as MessageEvent).data) as Job
      queryClient.setQueryData(['jobs', jobId], job)
      void queryClient.invalidateQueries({ queryKey: ['jobs'] })
      es.close()
    })
    es.onerror = () => {
      refresh()
    }
    return () => es.close()
  }, [jobId, queryClient])
}