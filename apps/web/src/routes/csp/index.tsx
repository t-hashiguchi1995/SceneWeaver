import { useMutation } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { ErrorBanner } from '../../components/ErrorBanner'
import { api, loadStudioContext, saveStudioContext } from '../../lib/api'

export const Route = createFileRoute('/csp/')({
  component: CspPage,
})

function CspPage() {
  const { t } = useTranslation('csp')
  const ctx = loadStudioContext()
  const [revision, setRevision] = useState(ctx.handoffRevision ?? '')
  const [path, setPath] = useState(ctx.handoffPath ?? '')
  const [manifest, setManifest] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState('')

  const build = useMutation({
    mutationFn: async () => {
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
      {revision && (
        <div data-testid="csp-result">
          <p>
            {t('revision')} <strong data-testid="csp-revision">{revision}</strong>
          </p>
          <p className="meta" data-testid="csp-path">
            {path}
          </p>
          {manifest && (
            <pre className="lede" data-testid="csp-manifest">
              {JSON.stringify(manifest, null, 2)}
            </pre>
          )}
        </div>
      )}
    </section>
  )
}
