import { useMutation } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'

import { api, loadStudioContext, saveStudioContext } from '../../lib/api'

export const Route = createFileRoute('/shots/')({
  component: ShotsPage,
})

function ShotsPage() {
  const ctx = loadStudioContext()
  const [beatId, setBeatId] = useState(ctx.beatId ?? '')
  const [shotId, setShotId] = useState(ctx.shotId ?? '')
  const [usePose, setUsePose] = useState(true)
  const [phase, setPhase] = useState<'idle' | 'queued' | 'running' | 'succeeded' | 'failed'>('idle')
  const [candidates, setCandidates] = useState<string[]>(ctx.generationAssetIds ?? [])
  const [adoptedId, setAdoptedId] = useState(ctx.adoptedRenderAssetId ?? '')
  const [error, setError] = useState('')

  const plan = useMutation({
    mutationFn: () => api.planShot(beatId),
    onSuccess: (shot) => {
      setShotId(shot.id)
      saveStudioContext({ shotId: shot.id, beatId })
    },
    onError: (err) => setError((err as Error).message),
  })

  const render = useMutation({
    mutationFn: async () => {
      setPhase('queued')
      await new Promise((r) => setTimeout(r, 120))
      setPhase('running')
      return api.renderShot(shotId, usePose)
    },
    onSuccess: (result) => {
      setCandidates(result.output_asset_ids)
      setPhase('succeeded')
      saveStudioContext({
        shotId: result.shot_id,
        generationAssetIds: result.output_asset_ids,
      })
    },
    onError: (err) => {
      setPhase('failed')
      setError((err as Error).message)
    },
  })

  const adopt = useMutation({
    mutationFn: (assetId: string) => api.setAssetDecision(assetId, 'adopted'),
    onSuccess: (result) => {
      setAdoptedId(result.asset_id)
      saveStudioContext({
        adoptedRenderAssetId: result.asset_id,
        adoptedRenderSha256: result.sha256,
      })
    },
  })

  return (
    <section className="page" data-testid="shots-page">
      <h1>Shot Studio</h1>
      <p className="lede">Plan ShotSpec, set Pose/Camera, Generate, Review/Adopt.</p>

      <div className="stack">
        <label>
          Beat ID
          <input
            aria-label="Beat ID"
            data-testid="shot-beat-id"
            value={beatId}
            onChange={(e) => setBeatId(e.target.value)}
          />
        </label>
        <button
          type="button"
          className="btn primary"
          data-testid="shot-plan"
          disabled={!beatId || plan.isPending}
          onClick={() => plan.mutate()}
        >
          Plan ShotSpec
        </button>

        <label className="checkbox">
          <input
            type="checkbox"
            data-testid="shot-use-pose"
            checked={usePose}
            onChange={(e) => setUsePose(e.target.checked)}
          />
          Pose / Camera (LLLite path)
        </label>

        <button
          type="button"
          className="btn primary"
          data-testid="shot-generate"
          disabled={!shotId || render.isPending}
          onClick={() => render.mutate()}
        >
          Generate
        </button>
      </div>

      <p className="hint" data-testid="shot-phase">
        Status: <span data-testid="shot-status-label">{phaseLabel(phase)}</span>
      </p>
      {shotId && (
        <p className="meta" data-testid="shot-id">
          Shot {shotId}
        </p>
      )}
      {error && <p className="error">{error}</p>}

      <ul className="candidate-grid" data-testid="generation-candidate-list">
        {candidates.map((id, index) => (
          <li key={id} data-testid={`generation-candidate-${index}`}>
            <code>{id.slice(0, 8)}…</code>
            <button
              type="button"
              className="btn"
              data-testid={`generation-adopt-${index}`}
              onClick={() => adopt.mutate(id)}
            >
              Adopt
            </button>
          </li>
        ))}
      </ul>

      {adoptedId && (
        <p data-testid="generation-adopted-banner">Adopted render {adoptedId.slice(0, 8)}…</p>
      )}
    </section>
  )
}

function phaseLabel(phase: string): string {
  switch (phase) {
    case 'queued':
      return 'Queued'
    case 'running':
      return 'Running'
    case 'succeeded':
      return 'Succeeded'
    case 'failed':
      return 'Failed'
    default:
      return 'Idle'
  }
}
