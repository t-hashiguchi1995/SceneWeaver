import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { api } from '../lib/api'
import { formatStatus } from '../i18n/format'

export function JobsIndicator() {
  const { t } = useTranslation(['jobs', 'common'])
  const dialog = useRef<HTMLDialogElement>(null)
  const jobs = useQuery({ queryKey: ['jobs'], queryFn: api.listJobs, refetchInterval: 5000 })
  const active = (jobs.data ?? []).filter((job) => ['queued', 'running'].includes(job.status))
  return <div className="jobs-indicator">
    <button type="button" className="btn" data-testid="nav-jobs" onClick={() => dialog.current?.showModal()}>{t('jobs:title')} · {active.length}</button>
    <dialog ref={dialog} className="jobs-drawer" aria-labelledby="jobs-drawer-title" onClick={(e) => { if (e.target === e.currentTarget) dialog.current?.close() }}>
      <div className="row-between"><h2 id="jobs-drawer-title">{t('jobs:title')}</h2><button className="btn" autoFocus onClick={() => dialog.current?.close()}>{t('common:actions.close')}</button></div>
      {jobs.error && <p role="alert">{jobs.error.message}</p>}
      <ul className="list">{(jobs.data ?? []).slice(0, 20).map((job) => <li key={job.id}><strong>{job.kind}</strong><span>{formatStatus(t, job.status)}</span>{job.error_message && <p role="alert">{job.error_message}</p>}</li>)}</ul>
      <Link to="/jobs" className="btn" onClick={() => dialog.current?.close()}>{t('common:actions.details')}</Link>
    </dialog>
  </div>
}
