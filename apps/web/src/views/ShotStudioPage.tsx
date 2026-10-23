import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams, useSearch } from '@tanstack/react-router'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { usePromptAutosave } from '../hooks/usePromptAutosave'
import { ErrorBanner } from '../components/ErrorBanner'
import { OperationError } from '../components/OperationError'
import { ProjectContextBar } from '../components/ProjectContextBar'
import { PromptEditor } from '../components/PromptEditor'
import { formatStatus } from '../i18n/format'
import { endActiveOperation, startActiveOperation, updateActiveOperation } from '../lib/activeOperations'
import { api, saveStudioContext, type PromptDraft } from '../lib/api'

function withLocalEdits(
  draft: PromptDraft,
  editedPositive: string,
  editedNegative: string,
): PromptDraft {
  const modified_positive = editedPositive !== draft.rendered_base_positive
  const modified_negative = editedNegative !== draft.rendered_base_negative
  return {
    ...draft,
    edited_positive: editedPositive,
    edited_negative: editedNegative,
    modified_positive,
    modified_negative,
    modified: modified_positive || modified_negative,
  }
}

const LIBRARY_CATEGORIES = ['all', 'costume', 'expression', 'pose', 'background', 'lighting', 'style', 'quality'] as const

export function ShotStudioPage() {
  const { t } = useTranslation(['generation', 'common', 'prompt'])
  const navigate = useNavigate()
  const qc = useQueryClient()
  const library = useQuery({ queryKey: ['prompt-library'], queryFn: api.promptLibrary })
  const { shotId, projectId } = useParams({ strict: false })
  if (!shotId) throw new Error('Shot is required')
  const { sourceAttemptId } = useSearch({ strict: false })
  const [librarySearch, setLibrarySearch] = useState('')
  const [libraryCategory, setLibraryCategory] = useState<(typeof LIBRARY_CATEGORIES)[number]>('all')
  const [usePose, setUsePose] = useState(false)
  const [seedMode, setSeedMode] = useState('random')
  const [seed, setSeed] = useState(1234)
  const [poseUri, setPoseUri] = useState('')
  const [phase, setPhase] = useState<'idle' | 'queued' | 'running' | 'succeeded' | 'failed'>('idle')
  const [error, setError] = useState('')
  const [draft, setDraft] = useState<PromptDraft | null>(null)
  const [templateBody, setTemplateBody] = useState('')
  const [staleDismissed, setStaleDismissed] = useState(false)
  const [specSummary, setSpecSummary] = useState<Record<string, unknown>>({})
  const [beatId, setBeatId] = useState('')

  const autosave = usePromptAutosave(shotId, draft)
  const dashboard = useQuery({
    queryKey: ['project-dashboard', projectId],
    queryFn: () => api.projectDashboard(projectId!),
    enabled: Boolean(projectId),
  })
  const characters = useQuery({ queryKey: ['characters'], queryFn: api.listCharacters })

  useEffect(() => {
    setDraft(null)
    setStaleDismissed(false)
    setBeatId('')
    saveStudioContext({ shotId })
    let cancelled = false
    void (async () => {
      try {
        const [shot, existing] = await Promise.all([
          qc.fetchQuery({ queryKey: ['shot', shotId], queryFn: () => api.getShot(shotId) }),
          qc.fetchQuery({ queryKey: ['prompt-draft', shotId], queryFn: () => api.ensurePromptDraft(shotId) }),
        ])
        const tpl = await api.getPromptTemplate(shotId)
        if (cancelled) return
        setBeatId(shot.beat_id)
        setSpecSummary(shot.render_spec ?? {})
        setDraft(existing)
        if (!cancelled) setTemplateBody(tpl.body)
      } catch (err) {
        if (!cancelled) setError((err as Error).message)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [shotId, qc])

  const resetEdits = useMutation({
    mutationFn: async () => {
      await autosave.flush()
      return api.resetPromptEdits(shotId)
    },
    onSuccess: (updated) => setDraft(updated),
  })

  const rebuild = useMutation({
    mutationFn: async (confirm: boolean) => {
      await autosave.flush()
      return api.rebuildPromptDraft(shotId, confirm)
    },
    onSuccess: (updated) => {
      setDraft(updated)
      setStaleDismissed(false)
    },
    onError: (err) => setError((err as Error).message),
  })

  const render = useMutation({
    mutationFn: async () => {
      await autosave.flush()
      const opId = `render-${shotId}`
      startActiveOperation({
        id: opId,
        kind: 'render',
        detail: `Shot ${shotId.slice(0, 8)}`,
        status: 'queued',
        progress: 10,
      })
      setPhase('queued')
      await new Promise((r) => setTimeout(r, 500))
      setPhase('running')
      updateActiveOperation(opId, { status: 'running', progress: 55 })
      try {
        return await api.renderShot(
          shotId,
          usePose,
          seedMode === 'fixed' ? seed : undefined,
          usePose ? poseUri : undefined,
          sourceAttemptId,
        )
      } finally {
        endActiveOperation(opId)
      }
    },
    onSuccess: (result) => {
      setPhase('succeeded')
      saveStudioContext({
        shotId: result.shot_id,
        generationAssetIds: result.output_asset_ids,
        generationAttemptId: result.generation_attempt_id,
      })
      void navigate({
        to: projectId
          ? '/projects/$projectId/shots/$shotId/generations/$attemptId'
          : '/shots/$shotId/generations/$attemptId',
        params: {
          projectId: projectId ?? '',
          shotId: result.shot_id,
          attemptId: result.generation_attempt_id,
        },
      })
    },
    onError: (err) => {
      setPhase('failed')
      setError((err as Error).message)
    },
  })

  const saveSpec = useMutation({
    mutationFn: async () => {
      await autosave.flush()
      return api.updateShot(shotId, specSummary)
    },
    onSuccess: async (shot) => {
      setSpecSummary(shot.render_spec)
      setDraft(await api.ensurePromptDraft(shotId))
      setStaleDismissed(false)
    },
    onError: (err) => setError((err as Error).message),
  })

  const expression = (specSummary.expression as { id?: string } | undefined)?.id
  const characterName = useMemo(() => {
    const speakerId = dashboard.data?.beats.find((b) => b.id === beatId)?.speaker_id
    const fromBeat = characters.data?.find((c) => c.id === speakerId)?.display_name
    if (fromBeat) return fromBeat
    const fromSpec = (specSummary.character as { name?: string } | undefined)?.name
    if (fromSpec) return fromSpec
    return ''
  }, [beatId, characters.data, dashboard.data?.beats, specSummary.character])
  const selectedPresetIds = (specSummary.prompt_preset_ids as string[] | undefined) ?? []
  const selectedPresets = useMemo(
    () => (library.data ?? []).filter((p) => selectedPresetIds.includes(p.id)),
    [library.data, selectedPresetIds],
  )
  const filteredLibrary = useMemo(() => {
    const q = librarySearch.toLowerCase()
    return (library.data ?? []).filter((p) => {
      if (p.content_rating !== 'general') return false
      if (libraryCategory !== 'all' && !String(p.category || '').toLowerCase().includes(libraryCategory)) {
        return false
      }
      return `${p.label} ${p.category} ${p.source_file}`.toLowerCase().includes(q)
    })
  }, [library.data, libraryCategory, librarySearch])

  const togglePreset = (id: string, checked: boolean) => {
    const ids = selectedPresetIds
    setSpecSummary({
      ...specSummary,
      prompt_profile_id: 'anima_story_panel',
      prompt_preset_ids: checked ? [...ids, id] : ids.filter((x) => x !== id),
    })
  }

  return (
    <section className="page shot-studio" data-testid="shots-page">
      {projectId && <ProjectContextBar shotId={shotId} strict />}
      <div className="row-between">
        <div>
          <h1>{t('generation:title')}</h1>
          <p className="lede">{t('generation:lede')}</p>
        </div>
        <div className="cta-row">
          <Link
            to={
              projectId
                ? '/projects/$projectId/shots/$shotId/generations'
                : '/shots/$shotId/generations'
            }
            params={{ projectId: projectId ?? '', shotId }}
            className="btn"
            data-testid="shot-open-review"
          >
            {t('generation:openReview')}
          </Link>
        </div>
      </div>

      {sourceAttemptId && <p className="hint">{t('generation:usingAttemptControls')}</p>}

      <div className="stack panel-card" data-testid="shot-basic-settings">
        <h2>{t('generation:basicSettings')}</h2>
        <p className="meta">
          {t('generation:character')}:{' '}
          <span data-testid="shot-character-name">{characterName || '—'}</span>
        </p>
        <div className="semantic-grid">
          <label>
            {t('generation:expression')}
            <input
              value={expression ?? ''}
              onChange={(e) =>
                setSpecSummary({
                  ...specSummary,
                  expression: { ...(specSummary.expression as object), id: e.target.value },
                })
              }
            />
          </label>
          <label>
            {t('generation:pose')}
            <input
              value={String((specSummary.pose as { id?: string })?.id ?? '')}
              onChange={(e) =>
                setSpecSummary({
                  ...specSummary,
                  pose: { ...(specSummary.pose as object), id: e.target.value },
                })
              }
            />
          </label>
          <label>
            {t('generation:camera')}
            <input
              value={String((specSummary.camera as { shot?: string })?.shot ?? '')}
              onChange={(e) =>
                setSpecSummary({
                  ...specSummary,
                  camera: { ...(specSummary.camera as object), shot: e.target.value },
                })
              }
            />
          </label>
          <label>
            {t('generation:background')}
            <input
              value={String(specSummary.background ?? '')}
              onChange={(e) => setSpecSummary({ ...specSummary, background: e.target.value })}
            />
          </label>
          <label>
            {t('generation:lighting')}
            <input
              value={String(specSummary.lighting ?? '')}
              onChange={(e) => setSpecSummary({ ...specSummary, lighting: e.target.value })}
            />
          </label>
        </div>
        <button
          type="button"
          className="btn"
          disabled={saveSpec.isPending}
          onClick={() => saveSpec.mutate()}
        >
          {t('prompt:semanticSave')}
        </button>
      </div>

      <div className="stack" data-testid="shot-prompt-section">
        <h2>{t('generation:promptSection')}</h2>
        {!draft && !error && <p className="meta">{t('prompt:loading')}</p>}
        {draft && (
          <PromptEditor
            templateLabel={draft.template_label}
            sourceKind={draft.source_kind}
            templateSource={templateBody}
            renderedBasePositive={draft.rendered_base_positive}
            renderedBaseNegative={draft.rendered_base_negative}
            editedPositive={draft.edited_positive}
            editedNegative={draft.edited_negative}
            modifiedPositive={draft.modified_positive}
            modifiedNegative={draft.modified_negative}
            stale={draft.stale && !staleDismissed}
            components={draft.assembly_metadata?.components}
            warnings={draft.assembly_metadata?.warnings}
            saveStatus={t(`prompt:${autosave.status}`)}
            generateDisabled={
              render.isPending ||
              saveSpec.isPending ||
              (usePose && !poseUri && !sourceAttemptId) ||
              (draft.stale && !staleDismissed)
            }
            onPositiveChange={(value) =>
              setDraft(withLocalEdits(draft, value, draft.edited_negative))
            }
            onNegativeChange={(value) =>
              setDraft(withLocalEdits(draft, draft.edited_positive, value))
            }
            onResetEdits={() => resetEdits.mutate()}
            onRebuild={() => {
              if (draft.modified && !window.confirm(t('prompt:rebuildConfirm'))) return
              rebuild.mutate(draft.modified)
            }}
            onDismissStale={() => setStaleDismissed(true)}
            onGenerate={() => {
              setError('')
              render.mutate()
            }}
          />
        )}
        {error && (
          <OperationError
            title={t('common:errors.generationFailedTitle')}
            message={error}
            onRetry={() => {
              setError('')
              render.mutate()
            }}
          />
        )}
      </div>

      <details className="panel-card shot-advanced" data-testid="shot-advanced-settings">
        <summary>{t('generation:advancedSettings')}</summary>
        <div className="stack">
          <label>
            {t('prompt:profile')}
            <select
              value={String(specSummary.prompt_profile_id ?? '')}
              onChange={(e) => setSpecSummary({ ...specSummary, prompt_profile_id: e.target.value })}
            >
              <option value="">Anima Compiler v1</option>
              <option value="anima_story_panel">Anima Story Panel v1</option>
            </select>
          </label>
          <label>
            {t('prompt:qualityProfile')}
            <select
              value={String(specSummary.prompt_quality_profile_id ?? 'builder_basic_v1')}
              onChange={(e) =>
                setSpecSummary({
                  ...specSummary,
                  prompt_profile_id: 'anima_story_panel',
                  prompt_quality_profile_id: e.target.value,
                })
              }
            >
              <option value="anima_legacy_v1">{t('prompt:qualityLegacy')}</option>
              <option value="builder_basic_v1">{t('prompt:qualityBasic')}</option>
            </select>
          </label>
          <div className="semantic-grid">
            <label>
              {t('generation:angle')}
              <input
                value={String((specSummary.camera as { angle?: string })?.angle ?? '')}
                onChange={(e) =>
                  setSpecSummary({
                    ...specSummary,
                    camera: { ...(specSummary.camera as object), angle: e.target.value },
                  })
                }
              />
            </label>
            <label>
              {t('generation:controlStrength')}
              <input
                type="number"
                min={0}
                max={2}
                step={0.05}
                value={Number(specSummary.control_strength ?? 1)}
                onChange={(e) =>
                  setSpecSummary({ ...specSummary, control_strength: Number(e.target.value) })
                }
              />
            </label>
            <label>
              {t('prompt:samplingSteps')}
              <input
                type="number"
                min={1}
                max={100}
                step={1}
                value={Number(specSummary.sampling_steps ?? 8)}
                onChange={(e) =>
                  setSpecSummary({ ...specSummary, sampling_steps: Number(e.target.value) })
                }
              />
            </label>
            <label>
              {t('prompt:samplingCfg')}
              <input
                type="number"
                min={0}
                max={20}
                step={0.1}
                value={Number(specSummary.sampling_cfg ?? 4)}
                onChange={(e) =>
                  setSpecSummary({ ...specSummary, sampling_cfg: Number(e.target.value) })
                }
              />
            </label>
          </div>
          <label>
            {t('prompt:seedMode')}
            <select value={seedMode} onChange={(e) => setSeedMode(e.target.value)}>
              <option value="random">{t('prompt:seedRandom')}</option>
              <option value="fixed">{t('prompt:seedFixed')}</option>
            </select>
          </label>
          {seedMode === 'fixed' && (
            <label>
              {t('prompt:seedValue')}
              <input
                type="number"
                min={0}
                max={2147483647}
                value={seed}
                onChange={(e) => setSeed(Number(e.target.value))}
              />
            </label>
          )}
          <label className="checkbox">
            <input
              type="checkbox"
              data-testid="shot-use-pose"
              checked={usePose}
              onChange={(e) => setUsePose(e.target.checked)}
            />
            {t('generation:poseCamera')}
          </label>
          {usePose && (
            <label>
              {t('generation:poseReference')}
              <input
                data-testid="shot-pose-uri"
                value={poseUri}
                onChange={(e) => setPoseUri(e.target.value)}
                placeholder={t('generation:poseReferenceHint')}
              />
            </label>
          )}

          <div className="stack" data-testid="shot-prompt-library">
            <h3>{t('prompt:library')}</h3>
            <p className="meta">{t('prompt:libraryHelp')}</p>
            <div className="cta-row library-categories">
              {LIBRARY_CATEGORIES.map((cat) => (
                <button
                  key={cat}
                  type="button"
                  className={libraryCategory === cat ? 'btn primary' : 'btn'}
                  data-testid={`library-cat-${cat}`}
                  onClick={() => setLibraryCategory(cat)}
                >
                  {t(`generation:libraryCat.${cat}`)}
                </button>
              ))}
            </div>
            {selectedPresets.length > 0 && (
              <div className="selected-presets" data-testid="library-selected">
                <p className="meta">{t('prompt:librarySelected')}</p>
                <div className="cta-row">
                  {selectedPresets.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      className="btn"
                      onClick={() => togglePreset(p.id, false)}
                    >
                      {p.label} ×
                    </button>
                  ))}
                </div>
              </div>
            )}
            <input
              aria-label={t('prompt:librarySearch')}
              placeholder={t('prompt:librarySearch')}
              value={librarySearch}
              onChange={(e) => setLibrarySearch(e.target.value)}
            />
            <div className="library-results">
              {filteredLibrary.slice(0, 40).map((p) => (
                <label key={p.id} title={p.prompt_fragment}>
                  <input
                    type="checkbox"
                    checked={selectedPresetIds.includes(p.id)}
                    onChange={(e) => togglePreset(p.id, e.target.checked)}
                  />
                  {p.category} / {p.label}
                </label>
              ))}
              {filteredLibrary.length > 40 && (
                <p className="meta">
                  {t('prompt:libraryTruncated', { count: filteredLibrary.length - 40 })}
                </p>
              )}
            </div>
            {library.error && <ErrorBanner message={library.error.message} />}
          </div>

          <button
            type="button"
            className="btn"
            disabled={saveSpec.isPending}
            onClick={() => saveSpec.mutate()}
          >
            {t('prompt:semanticSave')}
          </button>
        </div>
      </details>

      <p className="hint" data-testid="shot-phase">
        {t('generation:statusLabel')}:{' '}
        <span data-testid="shot-status-label">{formatStatus(t, phase)}</span>
      </p>
      <details className="meta technical-details">
        <summary>{t('generation:technicalInfo')}</summary>
        <p data-testid="shot-id">{t('generation:shotId', { id: shotId })}</p>
      </details>
      {autosave.error && <ErrorBanner message={autosave.error} />}
    </section>
  )
}
