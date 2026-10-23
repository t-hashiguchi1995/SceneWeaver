import { useMutation, useQuery } from '@tanstack/react-query'
import { Link, useParams } from '@tanstack/react-router'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { AssetImage } from '../components/AssetImage'
import { ErrorBanner } from '../components/ErrorBanner'
import { ProjectContextBar } from '../components/ProjectContextBar'
import { WorkflowCompletionCard } from '../components/WorkflowCompletionCard'
import { api, loadStudioContext, saveStudioContext } from '../lib/api'

type PanelDraft = {
  panel_no: number
  shot_id: string
  asset_id: string
  beat_id: string
  lines: string[]
}

export function CspPage() {
  const { t } = useTranslation(['csp', 'project'])
  const { projectId } = useParams({ strict: false })
  const ctx = projectId ? {} : loadStudioContext()
  const dashboard = useQuery({
    queryKey: ['project-dashboard', projectId],
    queryFn: () => api.projectDashboard(projectId!),
    enabled: Boolean(projectId),
  })
  const settings = useQuery({ queryKey: ['settings'], queryFn: api.getSettings })
  const [revision, setRevision] = useState(ctx.handoffRevision ?? '')
  const [path, setPath] = useState(ctx.handoffPath ?? '')
  const [manifest, setManifest] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState('')
  const [copyStatus, setCopyStatus] = useState('')
  const [panels, setPanels] = useState<PanelDraft[]>([])
  const [orderDirty, setOrderDirty] = useState(false)

  useEffect(() => {
    if (!dashboard.data) return
    const nextDrafts = dashboard.data.adopted_assets.map((asset, index) => ({
      panel_no: index + 1,
      shot_id: asset.shot_id,
      asset_id: asset.asset_id,
      beat_id: asset.beat_id,
      lines: dashboard.data.script_events
        .filter((event) => event.locked && event.beat_id === asset.beat_id)
        .map((event) => event.text),
    }))
    setPanels((current) => {
      if (!orderDirty || current.length === 0) return nextDrafts
      const byId = new Map(nextDrafts.map((panel) => [panel.asset_id, panel]))
      const kept = current
        .filter((panel) => byId.has(panel.asset_id))
        .map((panel) => ({ ...byId.get(panel.asset_id)!, panel_no: panel.panel_no }))
      const keptIds = new Set(kept.map((panel) => panel.asset_id))
      const appended = nextDrafts.filter((panel) => !keptIds.has(panel.asset_id))
      return [...kept, ...appended].map((panel, index) => ({ ...panel, panel_no: index + 1 }))
    })
  }, [dashboard.data, orderDirty])

  const folderLabel = useMemo(() => {
    const value = path || dashboard.data?.latest_handoff?.path || ''
    if (!value) return ''
    const parts = value.replace(/\\/g, '/').split('/')
    return parts.filter(Boolean).slice(-2).join('/')
  }, [dashboard.data?.latest_handoff?.path, path])

  const movePanel = (index: number, direction: -1 | 1) => {
    setOrderDirty(true)
    setPanels((current) => {
      const next = [...current]
      const target = index + direction
      if (target < 0 || target >= next.length) return current
      ;[next[index], next[target]] = [next[target], next[index]]
      return next.map((panel, i) => ({ ...panel, panel_no: i + 1 }))
    })
  }

  const build = useMutation({
    mutationFn: async () => {
      if (projectId) {
        if (!panels.length) throw new Error(t('needContext'))
        return api.cspHandoff({
          project_id: projectId,
          pages: [
            {
              page_no: 1,
              panels: panels.map((panel) => ({
                panel_no: panel.panel_no,
                shot_id: panel.shot_id,
                asset_id: panel.asset_id,
                script_event_ids: (dashboard.data?.script_events ?? [])
                  .filter((event) => event.locked && event.beat_id === panel.beat_id)
                  .map((event) => event.id),
              })),
            },
          ],
          script_rows: (dashboard.data?.script_events ?? [])
            .filter((event) => event.locked)
            .map((event) => ({
              id: event.id,
              kind: 'speech',
              speaker: event.speaker_id ?? '',
              text: event.text,
            })),
        })
      }
      const current = loadStudioContext()
      if (!current.projectId || !current.shotId || !current.adoptedRenderAssetId) {
        throw new Error(t('needContext'))
      }
      return api.cspHandoff({
        project_id: current.projectId,
        pages: [
          {
            page_no: 1,
            panels: [
              {
                panel_no: 1,
                shot_id: current.shotId,
                script_event_ids: current.lockedEventId ? [current.lockedEventId] : [],
                asset_id: current.adoptedRenderAssetId,
              },
            ],
          },
        ],
        script_rows: current.lockedEventId
          ? [
              {
                id: current.lockedEventId,
                kind: 'speech',
                speaker: current.characterName ?? 'Character',
                text: current.lockedText ?? '',
              },
            ]
          : [],
      })
    },
    onSuccess: (result) => {
      // Keep local panel order; refetch would rebuild from adopted_assets and undo reorder.
      setRevision(result.revision)
      setPath(result.path)
      setManifest(result.manifest)
      saveStudioContext({
        handoffRevision: result.revision,
        handoffPath: result.path,
      })
    },
    onError: (err) => setError((err as Error).message),
  })

  const copyOutputPath = async () => {
    const value = path || dashboard.data?.latest_handoff?.path || ''
    if (!value) return
    try {
      await navigator.clipboard.writeText(value)
      setCopyStatus(t('pathCopied'))
    } catch {
      setCopyStatus(t('pathCopyFailed'))
    }
  }

  return (
    <section className="page" data-testid="csp-page">
      {projectId && <ProjectContextBar />}
      <h1>{t('title')}</h1>
      <p className="lede">{t('lede')}</p>

      <p className="meta">{settings.data?.csp_export_dir || t('defaultOutput')}</p>

      {projectId && (
        <div className="candidate-grid" data-testid="csp-page-plan">
          {panels.map((panel, index) => (
            <article
              className="panel-card csp-panel-card"
              key={panel.asset_id}
              data-testid={`csp-panel-${index}`}
              data-asset-id={panel.asset_id}
            >
              <h2>{t('panel', { n: panel.panel_no })}</h2>
              <AssetImage assetId={panel.asset_id} alt={t('panel', { n: panel.panel_no })} />
              <ol className="dialogue-lines" data-testid={`csp-panel-lines-${index}`}>
                {panel.lines.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ol>
              <div className="cta-row">
                <button
                  type="button"
                  className="btn"
                  data-testid={`csp-panel-up-${index}`}
                  disabled={index === 0}
                  onClick={() => movePanel(index, -1)}
                >
                  {t('moveUp')}
                </button>
                <button
                  type="button"
                  className="btn"
                  data-testid={`csp-panel-down-${index}`}
                  disabled={index === panels.length - 1}
                  onClick={() => movePanel(index, 1)}
                >
                  {t('moveDown')}
                </button>
              </div>
            </article>
          ))}
        </div>
      )}

      <div className="cta-row">
        <button
          type="button"
          className="btn primary"
          data-testid="csp-build-handoff"
          disabled={build.isPending}
          onClick={() => build.mutate()}
        >
          {t('build')}
        </button>
      </div>

      {error && <ErrorBanner message={error} />}
      {(revision || dashboard.data?.latest_handoff?.revision) && (
        <div className="panel-card stack" data-testid="csp-result">
          <p>
            {t('revision')}{' '}
            <strong data-testid="csp-revision">
              {revision || dashboard.data?.latest_handoff?.revision}
            </strong>
          </p>
          {folderLabel && <p className="meta">{t('outputFolder', { name: folderLabel })}</p>}
          <button
            type="button"
            className="btn primary"
            data-testid="csp-open-output"
            onClick={() => void copyOutputPath()}
          >
            {t('openOutput')}
          </button>
          {copyStatus && <p className="hint">{copyStatus}</p>}
          <details>
            <summary>{t('details')}</summary>
            <pre className="lede" data-testid="csp-manifest">
              {JSON.stringify(
                manifest ?? dashboard.data?.latest_handoff?.manifest ?? {},
                null,
                2,
              )}
            </pre>
          </details>
          <details className="meta technical-details">
            <summary>{t('technicalInfo')}</summary>
            <p className="meta" data-testid="csp-path">
              {path || dashboard.data?.latest_handoff?.path}
            </p>
          </details>
        </div>
      )}
      {(revision || dashboard.data?.latest_handoff?.revision) && projectId && (
        <WorkflowCompletionCard
          testId="csp-next-release"
          title={t('project:completion.cspTitle')}
          description={t('project:completion.cspDescription')}
          action={
            <Link
              className="btn primary"
              to="/projects/$projectId/release"
              params={{ projectId }}
              data-testid="csp-next-release-action"
            >
              {t('project:completion.cspAction')}
            </Link>
          }
        />
      )}
    </section>
  )
}
