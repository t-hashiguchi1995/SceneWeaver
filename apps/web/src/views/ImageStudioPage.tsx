import { useMutation, useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { AssetImage } from '../components/AssetImage'
import { ErrorBanner } from '../components/ErrorBanner'
import { PoseGallery } from '../components/PoseGallery'
import { api, type GenerationAttemptSummary } from '../lib/api'
import type { SelectedPose } from '../pose/types'

type StudioPhase = 'setup' | 'ready' | 'generated' | 'adopted' | 'discarded'
type ModelProfile = 'anima'

export function ImageStudioPage() {
  const { t } = useTranslation(['home'])
  const characters = useQuery({ queryKey: ['characters'], queryFn: api.listCharacters })
  const [characterId, setCharacterId] = useState('')
  const [outfitId, setOutfitId] = useState('')
  const [modelProfile, setModelProfile] = useState<ModelProfile>('anima')
  const [pose, setPose] = useState<SelectedPose | null>(null)
  const [galleryOpen, setGalleryOpen] = useState(false)
  const [shotId, setShotId] = useState('')
  const [lifecycle, setLifecycle] = useState('draft')
  const [positive, setPositive] = useState('')
  const [negative, setNegative] = useState('')
  const [assetIds, setAssetIds] = useState<string[]>([])
  const [attemptId, setAttemptId] = useState('')
  const [attempt, setAttempt] = useState<GenerationAttemptSummary | null>(null)
  const [provenance, setProvenance] = useState<Record<string, unknown> | null>(null)
  const [formalShotId, setFormalShotId] = useState<string | null>(null)
  const [formalProjectId, setFormalProjectId] = useState<string | null>(null)
  const [phase, setPhase] = useState<StudioPhase>('setup')
  const [error, setError] = useState('')

  const outfits = useQuery({
    queryKey: ['outfit-profiles', characterId],
    queryFn: () => api.listOutfitProfiles(characterId),
    enabled: Boolean(characterId),
  })

  const outfitOptions = outfits.data ?? []
  const canStart = Boolean(characterId)
  const canGenerate = Boolean(shotId && pose && phase !== 'discarded' && phase !== 'adopted')

  const resetSessionLocal = () => {
    setPose(null)
    setShotId('')
    setLifecycle('draft')
    setPositive('')
    setNegative('')
    setAssetIds([])
    setAttemptId('')
    setAttempt(null)
    setProvenance(null)
    setFormalShotId(null)
    setFormalProjectId(null)
    setPhase('setup')
    setError('')
  }

  const start = useMutation({
    mutationFn: async () => {
      const session = await api.createStudioSession({
        character_id: characterId,
        outfit_profile_id: outfitId || null,
        model_profile: modelProfile,
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
      const result = await api.renderStudioSession(shotId)
      const summary = await api.getGenerationAttempt(result.generation_attempt_id)
      return { result, summary }
    },
    onSuccess: ({ result, summary }) => {
      setAssetIds(result.output_asset_ids || [])
      setAttemptId(result.generation_attempt_id)
      setAttempt(summary)
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
      setFormalProjectId(result.formal_project_id)
      setPhase('adopted')
      setError('')
    },
    onError: (err) => setError((err as Error).message),
  })

  const discard = useMutation({
    mutationFn: async () => {
      if (!shotId) throw new Error('no session')
      return api.abandonStudioSession(shotId)
    },
    onSuccess: (session) => {
      setLifecycle(String(session.lifecycle || 'abandoned'))
      setPhase('discarded')
      setError('')
    },
    onError: (err) => setError((err as Error).message),
  })

  const provenanceLines = useMemo(() => {
    const modelId =
      attempt?.model_id ||
      (typeof attempt?.payload?.model_id === 'string' ? attempt.payload.model_id : null)
    const capability =
      attempt?.capability ||
      (typeof attempt?.payload?.capability === 'string' ? attempt.payload.capability : null)
    const workflow =
      attempt?.workflow_template_id ||
      (typeof attempt?.payload?.workflow_template_id === 'string'
        ? attempt.payload.workflow_template_id
        : null)
    const seed = attempt?.seed
    return [
      `Model: ${modelId ?? modelProfile}`,
      `Seed: ${seed ?? '—'}`,
      `Capability: ${capability ?? '—'}`,
      `Workflow: ${workflow ?? '—'}`,
      `Pose: ${provenance?.pose_id ?? '—'} / ${provenance?.pose_view ?? '—'}`,
      `pose_method: ${provenance?.pose_method ?? '—'}`,
      `pose_source: ${provenance?.pose_source ?? '—'} ${provenance?.pose_source_version ?? ''}`,
      `flipped: ${String(provenance?.flipped ?? false)}`,
      `pose_asset_sha256: ${provenance?.pose_asset_sha256 ?? '—'}`,
    ]
  }, [attempt, provenance, modelProfile])

  return (
    <section className="page image-studio-page" data-testid="image-studio-page">
      <h1 data-testid="image-studio-title">{t('home:quickTestTitle')}</h1>
      <p className="lede">{t('home:quickTestLede')}</p>
      {error && <ErrorBanner message={error} />}

      <div className="panel-card" data-testid="studio-setup">
        <h2>1. Character / Outfit / Model</h2>
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
        <label className="field">
          <span>Model</span>
          <select
            data-testid="studio-model"
            value={modelProfile}
            onChange={(e) => setModelProfile(e.target.value as ModelProfile)}
            disabled={phase !== 'setup'}
          >
            <option value="anima">Anima</option>
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
        {(phase === 'adopted' || phase === 'discarded') && (
          <button
            type="button"
            className="btn primary"
            data-testid="studio-start-new"
            onClick={resetSessionLocal}
          >
            Start New
          </button>
        )}
        {shotId && (
          <p className="meta" data-testid="studio-shot-id">
            scratch: {shotId} · lifecycle: <span data-testid="studio-lifecycle">{lifecycle}</span>
          </p>
        )}
      </div>

      {phase !== 'setup' && phase !== 'discarded' && (
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
                  {pose.flipHorizontal ? ' · flipped' : ''}
                </p>
                {pose.card.thumbUrl && (
                  <img src={pose.card.thumbUrl} alt="" className="pose-picker-thumb" />
                )}
              </div>
              <button
                type="button"
                className="btn"
                disabled={phase === 'adopted'}
                onClick={() => setGalleryOpen(true)}
              >
                Change
              </button>
            </div>
          )}
        </div>
      )}

      {phase !== 'setup' && phase !== 'discarded' && (
        <div className="panel-card" data-testid="studio-prompt">
          <h2>3. Prompt</h2>
          <label className="field">
            <span>Positive</span>
            <textarea
              data-testid="studio-positive"
              rows={5}
              value={positive}
              disabled={phase === 'adopted'}
              onChange={(e) => setPositive(e.target.value)}
            />
          </label>
          <label className="field">
            <span>Negative</span>
            <textarea
              data-testid="studio-negative"
              rows={3}
              value={negative}
              disabled={phase === 'adopted'}
              onChange={(e) => setNegative(e.target.value)}
            />
          </label>
          <div className="studio-actions cta-row">
            <button
              type="button"
              className="btn primary"
              data-testid="studio-generate"
              disabled={!canGenerate || generate.isPending}
              onClick={() => generate.mutate()}
            >
              {phase === 'generated' ? 'Regenerate' : 'Generate'}
            </button>
            {phase === 'generated' && (
              <>
                {attemptId && (
                  <Link
                    to="/shots/$shotId/generations/$attemptId"
                    params={{ shotId, attemptId }}
                    className="btn"
                    data-testid="studio-review"
                  >
                    Review generation
                  </Link>
                )}
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
                  data-testid="studio-discard"
                  disabled={discard.isPending}
                  onClick={() => discard.mutate()}
                >
                  Discard
                </button>
              </>
            )}
            {phase === 'ready' && shotId && (
              <button
                type="button"
                className="btn"
                data-testid="studio-discard"
                disabled={discard.isPending}
                onClick={() => discard.mutate()}
              >
                Discard
              </button>
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
              {formalProjectId ? ` · project ${formalProjectId}` : ''}
            </p>
          )}
          {phase === 'adopted' && formalProjectId && formalShotId && (
            <div className="cta-row">
              <Link
                to="/projects/$projectId/shots/$shotId"
                params={{ projectId: formalProjectId, shotId: formalShotId }}
                className="btn"
                data-testid="studio-open-formal"
              >
                Open formal shot
              </Link>
              <button type="button" className="btn primary" data-testid="studio-start-new" onClick={resetSessionLocal}>
                Start New
              </button>
            </div>
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
