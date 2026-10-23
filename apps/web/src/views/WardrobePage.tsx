import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from '@tanstack/react-router'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { AssetImage } from '../components/AssetImage'
import { OperationError } from '../components/OperationError'
import { ProjectContextBar } from '../components/ProjectContextBar'
import { WorkflowCompletionCard } from '../components/WorkflowCompletionCard'
import { formatStatus } from '../i18n/format'
import { endActiveOperation, startActiveOperation, updateActiveOperation } from '../lib/activeOperations'
import { api, loadStudioContext, saveStudioContext } from '../lib/api'

type WardrobeTab = 'market' | 'tryon' | 'mine'

export function WardrobePage() {
  const { t } = useTranslation(['wardrobe', 'common', 'project'])
  const { projectId } = useParams({ strict: false })
  const qc = useQueryClient()
  const dashboard = useQuery({
    queryKey: ['project-dashboard', projectId],
    queryFn: () => api.projectDashboard(projectId!),
    enabled: Boolean(projectId),
  })
  const ctx = projectId
    ? {
        characterId: dashboard.data?.character_ids[0],
        sceneId: dashboard.data?.scenes[0]?.id,
        characterName: undefined as string | undefined,
        marketplaceItemId: undefined as string | undefined,
        tryonSessionId: undefined as string | undefined,
        tryonAdoptedAssetId: undefined as string | undefined,
        outfitProfileId: undefined as string | undefined,
      }
    : loadStudioContext()
  const [tab, setTab] = useState<WardrobeTab>('market')
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
  const [filter, setFilter] = useState('')

  const items = useQuery({
    queryKey: ['market'],
    queryFn: () => api.listMarket(),
  })

  useEffect(() => {
    const session = dashboard.data?.tryon_sessions.at(-1)
    if (!session || sessionId) return
    setSessionId(session.session_id)
    setCandidates(session.candidate_asset_ids)
    setCharacterId(session.character_id)
    setSceneId(session.scene_id)
    setAdoptedId(session.adopted_asset_id ?? '')
    setOutfitId(session.outfit_profile_id)
    setPhase('succeeded')
    setTab(session.adopted_asset_id ? 'mine' : 'tryon')
  }, [dashboard.data, sessionId])

  const selected = (items.data ?? []).find((i) => i.id === selectedId)
  const filtered = useMemo(
    () =>
      (items.data ?? []).filter((item) =>
        `${item.title} ${item.category} ${item.style_tags.join(' ')}`
          .toLowerCase()
          .includes(filter.toLowerCase()),
      ),
    [filter, items.data],
  )
  const characterName =
    characters.data?.find((c) => c.id === (characterId || ctx.characterId))?.display_name ||
    ctx.characterName
  const adoptedOutfits = useMemo(() => {
    const items = (dashboard.data?.tryon_sessions ?? [])
      .filter((session) => session.adopted_asset_id)
      .map((session) => ({
        assetId: session.adopted_asset_id!,
        outfitId: session.outfit_profile_id,
        sessionId: session.session_id,
      }))
    if (adoptedId && !items.some((item) => item.assetId === adoptedId)) {
      items.push({
        assetId: adoptedId,
        outfitId,
        sessionId,
      })
    }
    return items
  }, [adoptedId, dashboard.data?.tryon_sessions, outfitId, sessionId])

  const tryOn = useMutation({
    mutationFn: async () => {
      const effectiveCharacterId = characterId || ctx.characterId
      const effectiveSceneId = sceneId || ctx.sceneId
      if (!effectiveCharacterId || !selectedId) throw new Error(t('wardrobe:needCharacterOutfit'))
      const opId = `tryon-${effectiveCharacterId}-${selectedId}`
      startActiveOperation({
        id: opId,
        kind: 'tryon',
        detail: characterName || effectiveCharacterId,
        status: 'queued',
        progress: 8,
      })
      setPhase('queued')
      // Keep queued visible long enough for Header / body status to agree (CX-F0).
      await new Promise((r) => setTimeout(r, 500))
      setPhase('running')
      updateActiveOperation(opId, { status: 'running', progress: 45 })
      try {
        return await api.runTryOn(effectiveCharacterId!, selectedId, effectiveSceneId)
      } finally {
        endActiveOperation(opId)
      }
    },
    onSuccess: (result) => {
      setSessionId(result.session_id)
      setCandidates(result.candidate_asset_ids)
      setActiveCandidate(result.candidate_asset_ids[0] ?? '')
      setPhase('succeeded')
      setTab('tryon')
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
      setTab('mine')
      saveStudioContext({
        tryonAdoptedAssetId: assetId,
        outfitProfileId: result.outfit_profile_id,
      })
      if (projectId) {
        void qc.invalidateQueries({ queryKey: ['project-dashboard', projectId] })
      }
    },
  })

  return (
    <section className="page" data-testid="wardrobe-page">
      {projectId && (
        <ProjectContextBar
          sceneId={sceneId || ctx.sceneId}
          beatId={loadStudioContext().beatId}
          shotId={loadStudioContext().shotId}
        />
      )}
      <h1>{t('wardrobe:title')}</h1>
      <p className="lede">{t('wardrobe:lede')}</p>
      {characterName || ctx.characterId ? (
        <p className="meta" data-testid="wardrobe-character">
          {t('wardrobe:activeCharacter', {
            name: characterName || (ctx.characterId ?? '').slice(0, 8),
          })}
        </p>
      ) : (
        <p className="meta" data-testid="wardrobe-need-character">
          {t('wardrobe:needCharacterFirst')}
        </p>
      )}

      <div className="cta-row wardrobe-tabs" role="tablist" data-testid="wardrobe-tabs">
        {(
          [
            ['market', 'tabMarket'],
            ['tryon', 'tabTryOn'],
            ['mine', 'tabMine'],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            className={tab === key ? 'btn primary' : 'btn'}
            data-testid={`wardrobe-tab-${key}`}
            onClick={() => setTab(key)}
          >
            {t(`wardrobe:${label}`)}
          </button>
        ))}
      </div>

      {tab === 'market' && (
        <div className="stack studio-form" data-testid="wardrobe-market-panel">
          {projectId && (
            <div className="semantic-grid">
              <label>
                {t('wardrobe:character')}
                <select
                  value={characterId || ctx.characterId || ''}
                  onChange={(e) => setCharacterId(e.target.value)}
                >
                  <option value="">—</option>
                  {characters.data?.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.display_name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                {t('wardrobe:scene')}
                <select
                  value={sceneId || ctx.sceneId || ''}
                  onChange={(e) => setSceneId(e.target.value)}
                >
                  <option value="">—</option>
                  {dashboard.data?.scenes.map((scene) => (
                    <option key={scene.id} value={scene.id}>
                      {scene.title}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          )}
          <label>
            {t('wardrobe:search')}
            <input value={filter} onChange={(e) => setFilter(e.target.value)} />
          </label>
          <ul className="candidate-grid" data-testid="market-list">
            {filtered.map((i) => (
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
                {i.canonical_plate_asset_id && (
                  <AssetImage assetId={i.canonical_plate_asset_id} alt={i.title} />
                )}
                <span className="meta">{i.category}</span>
              </li>
            ))}
          </ul>

          {selected && (
            <div className="stack panel-card" data-testid="outfit-detail">
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
              {error && (
                <OperationError
                  title={t('common:errors.tryonFailedTitle')}
                  message={error}
                  onRetry={() => {
                    setError('')
                    tryOn.mutate()
                  }}
                />
              )}
            </div>
          )}
        </div>
      )}

      {tab === 'tryon' && (
        <div className="stack" data-testid="wardrobe-tryon-panel">
          <p className="hint" data-testid="tryon-phase">
            {t('wardrobe:statusLabel')}:{' '}
            <span data-testid="tryon-status-label">{formatStatus(t, phase)}</span>
          </p>
          {error && (
            <OperationError
              title={t('common:errors.tryonFailedTitle')}
              message={error}
              onRetry={() => {
                setError('')
                tryOn.mutate()
              }}
            />
          )}
          {candidates.length === 0 ? (
            <p className="meta">{t('wardrobe:tryonEmpty')}</p>
          ) : (
            <div className="review-layout review-layout-3pane">
              <div className="tryon-candidates">
                <ul className="candidate-grid" data-testid="tryon-candidate-list">
                  {candidates.map((id, index) => (
                    <li key={id} data-testid={`tryon-candidate-${index}`}>
                      <button
                        type="button"
                        className={
                          activeCandidate === id
                            ? 'btn primary candidate-select'
                            : 'btn candidate-select'
                        }
                        aria-pressed={activeCandidate === id}
                        onClick={() => setActiveCandidate(id)}
                      >
                        <AssetImage
                          assetId={id}
                          alt={t('wardrobe:candidate', { n: index + 1 })}
                        />
                        {t('wardrobe:candidate', { n: index + 1 })}
                      </button>
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
              </div>
              {activeCandidate && (
                <div className="panel-card stack" data-testid="tryon-candidate-detail">
                  <h2>{t('wardrobe:preview')}</h2>
                  <div className="candidate-preview">
                    <AssetImage assetId={activeCandidate} alt={t('wardrobe:preview')} />
                  </div>
                  <div className="review-primary-actions">
                    <button
                      type="button"
                      className="btn primary"
                      disabled={adopt.isPending}
                      onClick={() => adopt.mutate(activeCandidate)}
                    >
                      {t('common:actions.adopt')}
                    </button>
                    <button
                      type="button"
                      className="btn"
                      onClick={() =>
                        void api
                          .setAssetDecision(activeCandidate, 'rejected')
                          .then(() => {
                            setCandidates((previous) =>
                              previous.filter((id) => id !== activeCandidate),
                            )
                            setActiveCandidate('')
                          })
                          .catch((err: Error) => setError(err.message))
                      }
                    >
                      {t('wardrobe:reject')}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {tab === 'mine' && (
        <div className="stack" data-testid="wardrobe-mine-panel">
          {adoptedOutfits.length === 0 ? (
            <p className="meta panel-card">{t('wardrobe:mineEmpty')}</p>
          ) : (
            <>
              <p data-testid="tryon-adopted-banner">
                {t('wardrobe:adoptedBanner', {
                  asset: t('wardrobe:adoptedShort'),
                  outfit: t('wardrobe:outfitCount', { count: adoptedOutfits.length }),
                })}
              </p>
              <ul className="candidate-grid" data-testid="wardrobe-adopted-list">
                {adoptedOutfits.map((outfit, index) => (
                  <li key={`${outfit.sessionId}-${outfit.assetId}`} data-testid={`wardrobe-adopted-${index}`}>
                    <h2>
                      {t('wardrobe:adoptedTitle')} {index + 1}
                    </h2>
                    <AssetImage
                      assetId={outfit.assetId}
                      alt={`${t('wardrobe:adoptedTitle')} ${index + 1}`}
                    />
                    <details className="meta technical-details">
                      <summary>{t('common:actions.details')}</summary>
                      <p className="meta">asset={outfit.assetId}</p>
                      <p className="meta">outfit={outfit.outfitId || '—'}</p>
                    </details>
                  </li>
                ))}
              </ul>
              {projectId && (
                <WorkflowCompletionCard
                  testId="wardrobe-next-shots"
                  title={t('project:completion.wardrobeTitle')}
                  description={t('project:completion.wardrobeDescription')}
                  action={
                    <Link
                      className="btn primary"
                      to="/projects/$projectId/shots"
                      params={{ projectId }}
                      data-testid="wardrobe-next-shots-action"
                    >
                      {t('project:completion.wardrobeAction')}
                    </Link>
                  }
                />
              )}
            </>
          )}
        </div>
      )}
    </section>
  )
}
