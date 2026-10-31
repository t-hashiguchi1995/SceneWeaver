import { useMutation, useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { AssetImage } from '../components/AssetImage'
import { ErrorBanner } from '../components/ErrorBanner'
import { PoseGallery } from '../components/PoseGallery'
import { api } from '../lib/api'
import type { SelectedPose } from '../pose/types'

type StudioPhase = 'setup' | 'ready' | 'generated' | 'adopted'

export function ImageStudioPage() {
  const { t } = useTranslation(['home'])
  const characters = useQuery({ queryKey: ['characters'], queryFn: api.listCharacters })
  const [characterId, setCharacterId] = useState('')
  const [outfitId, setOutfitId] = useState('')
  const [pose, setPose] = useState<SelectedPose | null>(null)
  const [galleryOpen, setGalleryOpen] = useState(false)
  const [shotId, setShotId] = useState('')
  const [lifecycle, setLifecycle] = useState('draft')
  const [positive, setPositive] = useState('')
  const [negative, setNegative] = useState('')
  const [assetIds, setAssetIds] = useState<string[]>([])
  const [attemptId, setAttemptId] = useState('')
  const [provenance, setProvenance] = useState<Record<string, unknown> | null>(null)
  const [formalShotId, setFormalShotId] = useState<string | null>(null)
  const [phase, setPhase] = useState<StudioPhase>('setup')
  const [error, setError] = useState('')

  const outfits = useQuery({
    queryKey: ['outfit-profiles', characterId],
    queryFn: () => api.listOutfitProfiles(characterId),
    enabled: Boolean(characterId),
  })

  const outfitOptions = outfits.data ?? []

  const canStart = Boolean(characterId)
  const canGenerate = Boolean(shotId && pose)

  const start = useMutation({
    mutationFn: async () => {
      const session = await api.createStudioSession({
        character_id: characterId,
        outfit_profile_id: outfitId || null,
        capability: 'BaseRender',
      })
      return session
    },
    onSuccess: (session) => {
      setShotId(session.shot_id)
      setLifecycle(session.lifecycle)
      const draft = session.prompt_draft
      setPositive(String(draft?.edited_positive || draft?.rendered_base_positive || ''))
      setNegative(String(draft?.edited_negative || draft?.rendered_base_negative || ''))
      setPhase('ready')
      setError('')
    },
    onError: (err) => setError((err as Error).message),
  })

  const applyPose = useMutation({
    mutationFn: async (sel: SelectedPose) => {
      if (!shotId) throw new Error('no session')
      return api.applyStudioPose(shotId, {
        pose_id: sel.poseId,
        pose_view: sel.poseView,
        flipped: sel.flipHorizontal,
        control_strength: sel.strength,
      })
    },
    onSuccess: (session) => {
      setLifecycle(String(session.lifecycle || 'draft'))
      setProvenance((session.pose_provenance as Record<string, unknown>) || null)
      const draft = session.prompt_draft as Record<string, unknown> | null
      if (draft) {
        setPositive(String(draft.edited_positive || draft.rendered_base_positive || positive))
        setNegative(String(draft.edited_negative || draft.rendered_base_negative || negative))
      }
    },
    onError: (err) => setError((err as Error).message),
  })

  const savePrompt = useMutation({
    mutationFn: async () => {
      if (!shotId) throw new Error('no session')
      return api.updatePromptDraft(shotId, positive, negative)
    },
    onError: (err) => setError((err as Error).message),
  })

  const generate = useMutation({
    mutationFn: async () => {
      if (!shotId) throw new Error('no session')
      await savePrompt.mutateAsync()
      return api.renderStudioSession(shotId)
    },
    onSuccess: (result) => {
      setAssetIds(result.output_asset_ids || [])
      setAttemptId(result.generation_attempt_id)
      const session = result.session as Record<string, unknown>
      setLifecycle(String(session.lifecycle || 'generated'))
      setProvenance((session.pose_provenance as Record<string, unknown>) || provenance)
      setPhase('generated')
      setError('')
    },
    onError: (err) => setError((err as Error).message),
  })

  const adopt = useMutation({
    mutationFn: async () => {
      if (!shotId) throw new Error('no session')
      return api.materializeStudioSession(shotId, {
        generation_attempt_id: attemptId || undefined,
      })
    },
    onSuccess: (result) => {
      setLifecycle(result.lifecycle)
      setFormalShotId(result.formal_shot_id)
      setPhase('adopted')
      setError('')
    },
    onError: (err) => setError((err as Error).message),
  })

  const abandon = useMutation({
    mutationFn: async () => {
      if (!shotId) throw new Error('no session')
      return api.abandonStudioSession(shotId)
    },
    onSuccess: (session) => {
      setLifecycle(String(session.lifecycle || 'abandoned'))
      setError('')
    },
    onError: (err) => setError((err as Error).message),
  })

  const provenanceLines = useMemo(() => {
    if (!provenance) return []
    return [
      `pose_id: ${provenance.pose_id ?? '—'}`,
      `pose_view: ${provenance.pose_view ?? '—'}`,
      `pose_method: ${provenance.pose_method ?? '—'}`,
      `pose_source: ${provenance.pose_source ?? '—'} ${provenance.pose_source_version ?? ''}`,
      `seed: ${attemptId ? '(from attempt)' : '—'}`,
    ]
  }, [provenance, attemptId])

  return (
    <section className="page" data-testid="image-studio-page">
      <h1 data-testid="image-studio-title">{t('home:quickTestTitle')}</h1>
      <p className="lede">{t('home:quickTestLede')}</p>
      {error && <ErrorBanner message={error} />}

      <div className="panel-card" data-testid="studio-setup">
        <h2>1. Character / Outfit</h2>
        <label className="field">
          <span>Character</span>
          <select
            data-testid="studio-character"
            value={characterId}
            onChange={(e) => {
              setCharacterId(e.target.value)
              setOutfitId('')
            }}
            disabled={phase !== 'setup'}
          >
            <option value="">—</option>
            {(characters.data ?? []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.display_name}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Outfit (existing OutfitProfile)</span>
          <select
            data-testid="studio-outfit"
            value={outfitId}
            onChange={(e) => setOutfitId(e.target.value)}
            disabled={!characterId || phase !== 'setup'}
          >
            <option value="">— none —</option>
            {outfitOptions.map((o) => (
              <option key={o.id} value={o.id}>
                {o.title}
              </option>
            ))}
          </select>
        </label>
        {phase === 'setup' && (
          <button
            type="button"
            className="btn primary"
            data-testid="studio-start"
            disabled={!canStart || start.isPending}
            onClick={() => start.mutate()}
          >
            Start session
          </button>
        )}
        {shotId && (
          <p className="meta" data-testid="studio-shot-id">
            scratch: {shotId} · lifecycle: <span data-testid="studio-lifecycle">{lifecycle}</span>
          </p>
        )}
      </div>

      {phase !== 'setup' && (
        <div className="panel-card" data-testid="studio-pose">
          <h2>2. Pose / Angle</h2>
          {!pose ? (
            <button
              type="button"
              className="btn primary"
              data-testid="studio-choose-pose"
              onClick={() => setGalleryOpen(true)}
            >
              Choose pose
            </button>
          ) : (
            <div className="row-between">
              <div>
                <strong data-testid="studio-pose-id">{pose.poseId}</strong>
                <p className="meta" data-testid="studio-pose-view">
                  view: {pose.poseView}
                </p>
                {pose.card.thumbUrl && (
                  <img src={pose.card.thumbUrl} alt="" className="pose-picker-thumb" />
                )}
              </div>
              <button type="button" className="btn" onClick={() => setGalleryOpen(true)}>
                Change
              </button>
            </div>
          )}
        </div>
      )}

      {phase !== 'setup' && (
        <div className="panel-card" data-testid="studio-prompt">
          <h2>3. Prompt</h2>
          <label className="field">
            <span>Positive</span>
            <textarea
              data-testid="studio-positive"
              rows={5}
              value={positive}
              onChange={(e) => setPositive(e.target.value)}
            />
          </label>
          <label className="field">
            <span>Negative</span>
            <textarea
              data-testid="studio-negative"
              rows={3}
              value={negative}
              onChange={(e) => setNegative(e.target.value)}
            />
          </label>
          <div className="cta-row">
            <button
              type="button"
              className="btn primary"
              data-testid="studio-generate"
              disabled={!canGenerate || generate.isPending}
              onClick={() => generate.mutate()}
            >
              Generate
            </button>
            {phase === 'generated' && (
              <>
                <button
                  type="button"
                  className="btn primary"
                  data-testid="studio-adopt"
                  disabled={adopt.isPending}
                  onClick={() => adopt.mutate()}
                >
                  Adopt → Story
                </button>
                <button
                  type="button"
                  className="btn"
                  data-testid="studio-abandon"
                  disabled={abandon.isPending || lifecycle === 'adopted'}
                  onClick={() => abandon.mutate()}
                >
                  Delete (abandon)
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {(phase === 'generated' || phase === 'adopted') && (
        <div className="panel-card" data-testid="studio-result">
          <h2>4. Result / Provenance</h2>
          <div className="asset-grid">
            {assetIds.map((id) => (
              <AssetImage key={id} assetId={id} alt="studio result" />
            ))}
          </div>
          <ul className="meta" data-testid="studio-provenance">
            {provenanceLines.map((line) => (
              <li key={line}>{line}</li>
            ))}
            {attemptId && <li>attempt: {attemptId}</li>}
          </ul>
          {formalShotId && (
            <p className="meta" data-testid="studio-formal-shot">
              formal shot: {formalShotId} (materialize = copy, not rerender)
            </p>
          )}
        </div>
      )}

      <PoseGallery
        open={galleryOpen}
        onClose={() => setGalleryOpen(false)}
        initialSelectedId={pose?.poseId}
        onApply={(sel) => {
          setPose(sel)
          setGalleryOpen(false)
          if (shotId) applyPose.mutate(sel)
        }}
      />
    </section>
  )
}
