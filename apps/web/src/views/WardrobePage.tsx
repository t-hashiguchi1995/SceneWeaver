import { useMutation, useQuery } from '@tanstack/react-query'
import { useParams } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { AssetImage } from '../components/AssetImage'
import { ErrorBanner } from '../components/ErrorBanner'
import { formatStatus } from '../i18n/format'
import { api, loadStudioContext, saveStudioContext } from '../lib/api'


export function WardrobePage() {
  const { t } = useTranslation(['wardrobe', 'common'])
  const { projectId } = useParams({ strict: false })
  const dashboard = useQuery({ queryKey: ['project-dashboard', projectId], queryFn: () => api.projectDashboard(projectId!), enabled: Boolean(projectId) })
  const ctx = projectId ? { characterId: dashboard.data?.character_ids[0], sceneId: dashboard.data?.scenes[0]?.id, characterName: undefined, marketplaceItemId: undefined, tryonSessionId: undefined, tryonAdoptedAssetId: undefined, outfitProfileId: undefined } : loadStudioContext()
  const [characterId, setCharacterId] = useState('')
  const [sceneId, setSceneId] = useState('')
  const characters = useQuery({ queryKey: ['characters'], queryFn: api.listCharacters })
  const [activeCandidate, setActiveCandidate] = useState('')
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

  useEffect(() => {
    const session = dashboard.data?.tryon_sessions.at(-1)
    if (!session || sessionId) return
    setSessionId(session.session_id); setCandidates(session.candidate_asset_ids)
    setCharacterId(session.character_id); setSceneId(session.scene_id)
    setAdoptedId(session.adopted_asset_id ?? ''); setOutfitId(session.outfit_profile_id)
    setPhase('succeeded')
  }, [dashboard.data, sessionId])
  const [filter, setFilter] = useState('')
  const selected = (items.data ?? []).find((i) => i.id === selectedId)

  const tryOn = useMutation({
    mutationFn: async () => {
      const effectiveCharacterId = characterId || ctx.characterId
      const effectiveSceneId = sceneId || ctx.sceneId
      if (!effectiveCharacterId || !selectedId) throw new Error(t('wardrobe:needCharacterOutfit'))
      setPhase('queued')
      await new Promise((r) => setTimeout(r, 120))
      setPhase('running')
      return api.runTryOn(effectiveCharacterId!, selectedId, effectiveSceneId)
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
      const effectiveSceneId = sceneId || ctx.sceneId
      return api.adoptTryOn(sessionId, assetId, effectiveSceneId)
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

      {projectId && <div className="semantic-grid">
        <label>{t('wardrobe:character')}<select value={characterId || ctx.characterId || ''} onChange={(e) => setCharacterId(e.target.value)}><option value="">—</option>{characters.data?.map((c) => <option key={c.id} value={c.id}>{c.display_name}</option>)}</select></label>
        <label>{t('wardrobe:scene')}<select value={sceneId || ctx.sceneId || ''} onChange={(e) => setSceneId(e.target.value)}><option value="">—</option>{dashboard.data?.scenes.map((scene) => <option key={scene.id} value={scene.id}>{scene.title}</option>)}</select></label>
      </div>}
      <label>{t('wardrobe:search')}<input value={filter} onChange={(e) => setFilter(e.target.value)} /></label>
      <ul className="candidate-grid" data-testid="market-list">
        {(items.data ?? []).filter((item) => `${item.title} ${item.category} ${item.style_tags.join(" ")}`.toLowerCase().includes(filter.toLowerCase())).map((i) => (
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
            {i.canonical_plate_asset_id && <AssetImage assetId={i.canonical_plate_asset_id} alt={i.title} />}
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
            disabled={tryOn.isPending || (Boolean(projectId) && !(sceneId || ctx.sceneId))}
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
            <button type="button" className="btn candidate-select" aria-pressed={activeCandidate === id} onClick={() => setActiveCandidate(id)}><AssetImage assetId={id} alt={t("wardrobe:candidate", { n: index + 1 })} /></button>
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

      {activeCandidate && <div className="panel-card"><AssetImage assetId={activeCandidate} alt={t('wardrobe:preview')} /><button className="btn primary" disabled={adopt.isPending} onClick={() => adopt.mutate(activeCandidate)}>{t('common:actions.adopt')}</button><button className="btn" onClick={() => void api.setAssetDecision(activeCandidate, 'rejected').then(() => { setCandidates((previous) => previous.filter((id) => id !== activeCandidate)); setActiveCandidate('') }).catch((err: Error) => setError(err.message))}>{t('wardrobe:reject')}</button></div>}
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
