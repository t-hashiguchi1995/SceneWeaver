import { useMutation, useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'

import { api, loadStudioContext, saveStudioContext } from '../../lib/api'

export const Route = createFileRoute('/wardrobe/')({
  component: WardrobePage,
})

function WardrobePage() {
  const ctx = loadStudioContext()
  const [selectedId, setSelectedId] = useState(ctx.marketplaceItemId ?? '')
  const [candidates, setCandidates] = useState<string[]>([])
  const [sessionId, setSessionId] = useState(ctx.tryonSessionId ?? '')
  const [phase, setPhase] = useState<'idle' | 'queued' | 'running' | 'succeeded' | 'failed'>('idle')
  const [adoptedId, setAdoptedId] = useState(ctx.tryonAdoptedAssetId ?? '')
  const [outfitId, setOutfitId] = useState(ctx.outfitProfileId ?? '')
  const [error, setError] = useState('')

  const items = useQuery({
    queryKey: ['market'],
    queryFn: () => api.listMarket(),
  })

  const selected = (items.data ?? []).find((i) => i.id === selectedId)

  const tryOn = useMutation({
    mutationFn: async () => {
      const characterId = loadStudioContext().characterId
      const sceneId = loadStudioContext().sceneId
      if (!characterId || !selectedId) throw new Error('character and outfit required')
      setPhase('queued')
      await new Promise((r) => setTimeout(r, 120))
      setPhase('running')
      return api.runTryOn(characterId, selectedId, sceneId)
    },
    onSuccess: (result) => {
      setSessionId(result.session_id)
      setCandidates(result.candidate_asset_ids)
      setPhase('succeeded')
      saveStudioContext({
        marketplaceItemId: selectedId,
        tryonSessionId: result.session_id,
      })
    },
    onError: (err) => {
      setPhase('failed')
      setError((err as Error).message)
    },
  })

  const adopt = useMutation({
    mutationFn: (assetId: string) => {
      const sceneId = loadStudioContext().sceneId
      return api.adoptTryOn(sessionId, assetId, sceneId)
    },
    onSuccess: (result, assetId) => {
      setAdoptedId(assetId)
      setOutfitId(result.outfit_profile_id)
      saveStudioContext({
        tryonAdoptedAssetId: assetId,
        outfitProfileId: result.outfit_profile_id,
      })
    },
  })

  return (
    <section className="page" data-testid="wardrobe-page">
      <h1>Wardrobe Market</h1>
      <p className="lede">Pick an outfit, run Try-On, adopt one of four candidates.</p>

      <ul className="list" data-testid="market-list">
        {(items.data ?? []).map((i) => (
          <li key={i.id} data-testid="market-item">
            <button
              type="button"
              className="linkish"
              data-testid={`market-item-${i.title.toLowerCase().replace(/\s+/g, '-')}`}
              onClick={() => {
                setSelectedId(i.id)
                saveStudioContext({ marketplaceItemId: i.id })
              }}
            >
              {i.title}
            </button>
            <span className="meta">{i.category}</span>
          </li>
        ))}
      </ul>

      {selected && (
        <div className="stack" data-testid="outfit-detail">
          <h2 data-testid="outfit-title">{selected.title}</h2>
          <p>{selected.garment_description}</p>
          <button
            type="button"
            className="btn primary"
            data-testid="tryon-generate"
            disabled={tryOn.isPending}
            onClick={() => tryOn.mutate()}
          >
            Run Try-On
          </button>
        </div>
      )}

      <p className="hint" data-testid="tryon-phase">
        Status: <span data-testid="tryon-status-label">{phaseLabel(phase)}</span>
      </p>
      {error && <p className="error">{error}</p>}

      <ul className="candidate-grid" data-testid="tryon-candidate-list">
        {candidates.map((id, index) => (
          <li key={id} data-testid={`tryon-candidate-${index}`}>
            <code>{id.slice(0, 8)}…</code>
            <button
              type="button"
              className="btn"
              data-testid={`tryon-adopt-${index}`}
              onClick={() => adopt.mutate(id)}
            >
              Adopt
            </button>
          </li>
        ))}
      </ul>

      {adoptedId && (
        <p data-testid="tryon-adopted-banner">
          Adopted {adoptedId.slice(0, 8)}… · OutfitState {outfitId.slice(0, 8)}…
        </p>
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
