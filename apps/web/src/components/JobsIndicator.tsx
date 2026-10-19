import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { useMemo, useRef } from 'react'
import { useTranslation } from 'react-i18next'

import { useActiveOperations } from '../lib/activeOperations'
import { api, type Job } from '../lib/api'
import { formatStatus } from '../i18n/format'

type DisplayJob = {
  id: string
  kind: string
  detail?: string
  status: string
  progress?: number
  errorMessage?: string | null
  source: 'api' | 'local'
}

function kindLabel(t: (key: string, opts?: Record<string, unknown>) => string, kind: string): string {
  return t(`kinds.${kind}`, { defaultValue: kind })
}

function runningLabel(t: (key: string, opts?: Record<string, unknown>) => string, kind: string): string {
  return t(`running.${kind}`, { defaultValue: kindLabel(t, kind) })
}

function jobDetail(job: Job): string | undefined {
  const payload = job.payload ?? {}
  const parts = [
    typeof payload.character_name === 'string' ? payload.character_name : null,
    typeof payload.outfit_label === 'string' ? payload.outfit_label : null,
    typeof payload.scene_title === 'string' ? payload.scene_title : null,
    typeof payload.shot_label === 'string' ? payload.shot_label : null,
    typeof payload.shot_id === 'string' ? `Shot ${String(payload.shot_id).slice(0, 8)}` : null,
  ].filter(Boolean)
  return parts.length ? parts.join(' / ') : undefined
}

function progressPercent(job: Job): number | undefined {
  const value = job.progress?.percent
  return typeof value === 'number' ? value : undefined
}

export function JobsIndicator() {
  const { t } = useTranslation(['jobs', 'common'])
  const dialog = useRef<HTMLDialogElement>(null)
  const jobs = useQuery({ queryKey: ['jobs'], queryFn: api.listJobs, refetchInterval: 5000 })
  const localOps = useActiveOperations()

  const apiActive = useMemo(
    () => (jobs.data ?? []).filter((job) => ['queued', 'running'].includes(job.status)),
    [jobs.data],
  )
  const apiFailed = useMemo(
    () => (jobs.data ?? []).filter((job) => job.status === 'failed').slice(0, 5),
    [jobs.data],
  )

  const active: DisplayJob[] = [
    ...localOps.map((op) => ({
      id: op.id,
      kind: op.kind,
      detail: op.detail,
      status: op.status,
      progress: op.progress,
      source: 'local' as const,
    })),
    ...apiActive.map((job) => ({
      id: job.id,
      kind: job.kind,
      detail: jobDetail(job),
      status: job.status,
      progress: progressPercent(job),
      errorMessage: job.error_message,
      source: 'api' as const,
    })),
  ]

  const failed: DisplayJob[] = apiFailed.map((job) => ({
    id: job.id,
    kind: job.kind,
    detail: jobDetail(job),
    status: job.status,
    progress: progressPercent(job),
    errorMessage: job.error_message,
    source: 'api' as const,
  }))

  // Idle with no in-flight work: hide completely (no "0" / "処理なし").
  if (active.length === 0) {
    return null
  }

  const indicatorLabel =
    active.length === 1
      ? runningLabel(t, active[0].kind)
      : t('indicatorMany', { count: active.length })

  return (
    <div className="jobs-indicator" data-testid="jobs-indicator">
      <button
        type="button"
        className="btn jobs-indicator__button"
        data-testid="nav-jobs"
        onClick={() => dialog.current?.showModal()}
      >
        <span className="jobs-indicator__dot" aria-hidden="true" />
        <span data-testid="jobs-indicator-label">{indicatorLabel}</span>
      </button>
      <dialog
        ref={dialog}
        className="jobs-drawer"
        aria-labelledby="jobs-drawer-title"
        onClick={(e) => {
          if (e.target === e.currentTarget) dialog.current?.close()
        }}
      >
        <div className="row-between">
          <h2 id="jobs-drawer-title">{t('drawerTitle')}</h2>
          <button type="button" className="btn" autoFocus onClick={() => dialog.current?.close()}>
            {t('common:actions.close')}
          </button>
        </div>
        {jobs.error && (
          <p role="alert">{jobs.error.message}</p>
        )}
        {active.length === 0 && failed.length === 0 && (
          <p className="meta">{t('empty')}</p>
        )}
        <ul className="list jobs-drawer__list" data-testid="jobs-drawer-list">
          {[...active, ...failed].map((job) => (
            <li key={`${job.source}-${job.id}`} data-testid={`jobs-drawer-item-${job.status}`}>
              <strong>{kindLabel(t, job.kind)}</strong>
              {job.detail && <p className="meta">{job.detail}</p>}
              {typeof job.progress === 'number' && (
                <div
                  className="jobs-drawer__progress"
                  role="progressbar"
                  aria-valuenow={job.progress}
                  aria-valuemin={0}
                  aria-valuemax={100}
                >
                  <span style={{ width: `${Math.max(0, Math.min(100, job.progress))}%` }} />
                </div>
              )}
              <span className="meta">{formatStatus(t, job.status)}</span>
              {job.errorMessage && <p role="alert">{job.errorMessage}</p>}
            </li>
          ))}
        </ul>
        <Link to="/jobs" className="btn" onClick={() => dialog.current?.close()}>
          {t('common:actions.details')}
        </Link>
      </dialog>
    </div>
  )
}
