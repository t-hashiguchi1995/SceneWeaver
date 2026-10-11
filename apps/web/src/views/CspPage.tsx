import { useMutation, useQuery } from '@tanstack/react-query'
import { useParams } from '@tanstack/react-router'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { AssetImage } from '../components/AssetImage'
import { ErrorBanner } from '../components/ErrorBanner'
import { api, loadStudioContext, saveStudioContext } from '../lib/api'


export function CspPage() {
  const { t } = useTranslation('csp')
  const { projectId } = useParams({ strict: false })
  const ctx = projectId ? {} : loadStudioContext()
  const dashboard = useQuery({ queryKey: ['project-dashboard', projectId], queryFn: () => api.projectDashboard(projectId!), enabled: Boolean(projectId) })
  const settings = useQuery({ queryKey: ['settings'], queryFn: api.getSettings })
  const [revision, setRevision] = useState(ctx.handoffRevision ?? '')
  const [path, setPath] = useState(ctx.handoffPath ?? '')
  const [manifest, setManifest] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState('')

  const build = useMutation({
    mutationFn: async () => {
      if (projectId) {
        const state = await api.projectDashboard(projectId)
        const pages = [{ page_no: 1, panels: state.adopted_assets.map((asset, index) => ({ panel_no: index + 1, shot_id: asset.shot_id, asset_id: asset.asset_id, script_event_ids: state.script_events.filter((event) => event.locked && event.beat_id === asset.beat_id).map((event) => event.id) })) }]
        if (!pages[0].panels.length) throw new Error(t('needContext'))
        return api.cspHandoff({ project_id: projectId, pages, script_rows: state.script_events.filter((event) => event.locked).map((event) => ({ id: event.id, kind: 'speech', speaker: event.speaker_id ?? '', text: event.text })) })
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
      void dashboard.refetch()
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

  return (
    <section className="page" data-testid="csp-page">
      <h1>{t('title')}</h1>
      <p className="lede">{t('lede')}</p>

      <p className="meta">{settings.data?.csp_export_dir || t('defaultOutput')}</p>
      {projectId && <div className="candidate-grid" data-testid="csp-page-plan">{dashboard.data?.adopted_assets.map((asset, index) => <article className="panel-card" key={asset.asset_id}><h2>{t('panel', { n: index + 1 })}</h2><AssetImage assetId={asset.asset_id} alt={t('panel', { n: index + 1 })} /></article>)}</div>}
      <button
        type="button"
        className="btn primary"
        data-testid="csp-build-handoff"
        disabled={build.isPending}
        onClick={() => build.mutate()}
      >
        {t('build')}
      </button>

      {error && <ErrorBanner message={error} />}
      {(revision || dashboard.data?.latest_handoff?.revision) && (
        <div data-testid="csp-result">
          <p>
            {t('revision')} <strong data-testid="csp-revision">{revision || dashboard.data?.latest_handoff?.revision}</strong>
          </p>
          <p className="meta" data-testid="csp-path">
            {path || dashboard.data?.latest_handoff?.path}
          </p>
          {manifest && (
            <details><summary>{t("details")}</summary>
            <pre className="lede" data-testid="csp-manifest">
              {JSON.stringify(manifest, null, 2)}
            </pre></details>
          )}
        </div>
      )}
    </section>
  )
}
