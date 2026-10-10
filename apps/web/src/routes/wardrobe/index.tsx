import { useMutation, useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { ErrorBanner } from '../../components/ErrorBanner'
import { formatStatus } from '../../i18n/format'
import { api, loadStudioContext, saveStudioContext } from '../../lib/api'

export const Route = createFileRoute('/wardrobe/')({
  component: WardrobePage,
})

function WardrobePage() {
  const { t } = useTranslation(['wardrobe', 'common'])
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
      if (!characterId || !selectedId) throw new Error(t('wardrobe:needCharacterOutfit'))
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
      <h1>{t('wardrobe:title')}</h1>
      <p className="lede">{t('wardrobe:lede')}</p>
      {ctx.characterId ? (
        <p className="meta" data-testid="wardrobe-character">
          {t('wardrobe:activeCharacter', {
            name: ctx.characterName || ctx.characterId.slice(0, 8),
          })}
        </p>
      ) : (
        <p className="meta" data-testid="wardrobe-need-character">
          {t('wardrobe:needCharacterFirst')}
        </p>
      )}

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
            {t('wardrobe:runTryOn')}
          </button>
        </div>
      )}

      <p className="hint" data-testid="tryon-phase">
        {t('wardrobe:statusLabel')}:{' '}
        <span data-testid="tryon-status-label">{formatStatus(t, phase)}</span>
      </p>
      {error && <ErrorBanner message={error} />}

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
              {t('common:actions.adopt')}
            </button>
          </li>
        ))}
      </ul>

      {adoptedId && (
        <p data-testid="tryon-adopted-banner">
          {t('wardrobe:adoptedBanner', {
            asset: `${adoptedId.slice(0, 8)}…`,
            outfit: `${outfitId.slice(0, 8)}…`,
          })}
        </p>
      )}
    </section>
  )
}
