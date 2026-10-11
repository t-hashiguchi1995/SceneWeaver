import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams, useSearch } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { usePromptAutosave } from '../hooks/usePromptAutosave'
import { ErrorBanner } from '../components/ErrorBanner'
import { PromptEditor } from '../components/PromptEditor'
import { formatStatus } from '../i18n/format'
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

export function ShotStudioPage() {
  const { t } = useTranslation(['generation', 'common', 'prompt'])
  const navigate = useNavigate()
  const qc = useQueryClient()
  const library = useQuery({ queryKey: ['prompt-library'], queryFn: api.promptLibrary })
  const { shotId, projectId } = useParams({ strict: false })
  if (!shotId) throw new Error('Shot is required')
  const { sourceAttemptId } = useSearch({ strict: false })
  const [librarySearch, setLibrarySearch] = useState('')
  const [usePose, setUsePose] = useState(false)
  const [seedMode, setSeedMode] = useState("random")
  const [seed, setSeed] = useState(1234)
  const [poseUri, setPoseUri] = useState("")
  const [phase, setPhase] = useState<'idle' | 'queued' | 'running' | 'succeeded' | 'failed'>('idle')
  const [error, setError] = useState('')
  const [draft, setDraft] = useState<PromptDraft | null>(null)
  const [templateBody, setTemplateBody] = useState('')
  const [staleDismissed, setStaleDismissed] = useState(false)
  const [specSummary, setSpecSummary] = useState<Record<string, unknown>>({})

  const autosave = usePromptAutosave(shotId, draft)

  useEffect(() => {
    setDraft(null)
    setStaleDismissed(false)
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
    mutationFn: async () => { await autosave.flush(); return api.resetPromptEdits(shotId) },
    onSuccess: (updated) => setDraft(updated),
  })

  const rebuild = useMutation({
    mutationFn: async (confirm: boolean) => { await autosave.flush(); return api.rebuildPromptDraft(shotId, confirm) },
    onSuccess: (updated) => {
      setDraft(updated)
      setStaleDismissed(false)
    },
    onError: (err) => setError((err as Error).message),
  })

  const render = useMutation({
    mutationFn: async () => {
      await autosave.flush()
      setPhase('queued')
      await new Promise((r) => setTimeout(r, 120))
      setPhase('running')
      return api.renderShot(shotId, usePose, seedMode === "fixed" ? seed : undefined, usePose ? poseUri : undefined, sourceAttemptId)
    },
    onSuccess: (result) => {
      setPhase('succeeded')
      saveStudioContext({
        shotId: result.shot_id,
        generationAssetIds: result.output_asset_ids,
        generationAttemptId: result.generation_attempt_id,
      })
      void navigate({
        to: projectId ? '/projects/$projectId/shots/$shotId/generations/$attemptId' : '/shots/$shotId/generations/$attemptId',
        params: { projectId: projectId ?? '', shotId: result.shot_id, attemptId: result.generation_attempt_id },
      })
    },
    onError: (err) => {
      setPhase('failed')
      setError((err as Error).message)
    },
  })

  const saveSpec = useMutation({
    mutationFn: async () => { await autosave.flush(); return api.updateShot(shotId, specSummary) },
    onSuccess: async (shot) => { setSpecSummary(shot.render_spec); setDraft(await api.ensurePromptDraft(shotId)); setStaleDismissed(false) },
    onError: (err) => setError((err as Error).message),
  })
  const expression = (specSummary.expression as { id?: string } | undefined)?.id
  const characterTags = Array.isArray(specSummary.identity_tags)
    ? (specSummary.identity_tags as string[]).slice(0, 3).join(', ')
    : ''

  return (
    <section className="page" data-testid="shots-page">
      <div className="row-between">
        <div>
          <h1>{t('generation:title')}</h1>
          <p className="lede">{t('generation:lede')}</p>
        </div>
        <div className="cta-row">
          <Link
            to={projectId ? "/projects/$projectId/shots/$shotId/generations" : "/shots/$shotId/generations"}
            params={{ projectId: projectId ?? "", shotId }}
            className="btn"
            data-testid="shot-open-review"
          >
            {t('generation:openReview')}
          </Link>
        </div>
      </div>

      {sourceAttemptId && <p className="hint">{t("generation:usingAttemptControls")}</p>}
      <div className="stack panel-card" data-testid="shot-settings-summary">
        <h2>{t('generation:shotSettings')}</h2>
        <p className="meta">
          {t('generation:character')}: {characterTags || '—'}
        </p>
        <p className="meta">
          {t('generation:expression')}: {expression || '—'}
        </p>
        <details><summary>{t('prompt:library')}</summary>
          <p>{t('prompt:libraryHelp')}</p>
          <input aria-label={t('prompt:librarySearch')} placeholder={t('prompt:librarySearch')} value={librarySearch} onChange={e => setLibrarySearch(e.target.value)} />
          {(library.data ?? []).filter(p => p.content_rating === 'general' && `${p.label} ${p.category} ${p.source_file}`.toLowerCase().includes(librarySearch.toLowerCase())).map(p => <label key={p.id} title={p.prompt_fragment}>
            <input type="checkbox" checked={(specSummary.prompt_preset_ids as string[] ?? []).includes(p.id)} onChange={e => {
              const ids = specSummary.prompt_preset_ids as string[] ?? []
              setSpecSummary({ ...specSummary, prompt_profile_id: 'anima_story_panel', prompt_preset_ids: e.target.checked ? [...ids, p.id] : ids.filter(id => id !== p.id) })
            }} />{p.category} / {p.label} <small>{p.source_file}</small>
          </label>)}
          {library.error && <ErrorBanner message={library.error.message} />}
        </details>
        <label>{t('prompt:profile')}<select value={String(specSummary.prompt_profile_id ?? '')} onChange={(e) => setSpecSummary({ ...specSummary, prompt_profile_id: e.target.value })}><option value="">Anima Compiler v1</option><option value="anima_story_panel">Anima Story Panel v1</option></select></label>
        <label>{t('prompt:qualityProfile')}<select value={String(specSummary.prompt_quality_profile_id ?? 'builder_basic_v1')} onChange={e => setSpecSummary({ ...specSummary, prompt_profile_id: 'anima_story_panel', prompt_quality_profile_id: e.target.value })}><option value="anima_legacy_v1">{t('prompt:qualityLegacy')}</option><option value="builder_basic_v1">{t('prompt:qualityBasic')}</option></select></label>
        <div className="semantic-grid">
          <label>{t('generation:expression')}<input value={expression ?? ''} onChange={(e) => setSpecSummary({ ...specSummary, expression: { ...(specSummary.expression as object), id: e.target.value } })} /></label>
          <label>{t('generation:pose')}<input value={String((specSummary.pose as { id?: string })?.id ?? '')} onChange={(e) => setSpecSummary({ ...specSummary, pose: { ...(specSummary.pose as object), id: e.target.value } })} /></label>
          <label>{t('generation:camera')}<input value={String((specSummary.camera as { shot?: string })?.shot ?? '')} onChange={(e) => setSpecSummary({ ...specSummary, camera: { ...(specSummary.camera as object), shot: e.target.value } })} /></label>
          <label>{t('generation:angle')}<input value={String((specSummary.camera as { angle?: string })?.angle ?? '')} onChange={(e) => setSpecSummary({ ...specSummary, camera: { ...(specSummary.camera as object), angle: e.target.value } })} /></label>
          <label>{t('generation:controlStrength')}<input type="number" min={0} max={2} step={0.05} value={Number(specSummary.control_strength ?? 1)} onChange={(e) => setSpecSummary({ ...specSummary, control_strength: Number(e.target.value) })} /></label>
          <label>{t('prompt:samplingSteps')}<input type="number" min={1} max={100} step={1} value={Number(specSummary.sampling_steps ?? 8)} onChange={e => setSpecSummary({ ...specSummary, sampling_steps: Number(e.target.value) })} /></label>
          <label>{t('prompt:samplingCfg')}<input type="number" min={0} max={20} step={0.1} value={Number(specSummary.sampling_cfg ?? 4)} onChange={e => setSpecSummary({ ...specSummary, sampling_cfg: Number(e.target.value) })} /></label>
          <label>{t('generation:lighting')}<input value={String(specSummary.lighting ?? '')} onChange={(e) => setSpecSummary({ ...specSummary, lighting: e.target.value })} /></label>
          <label>{t('generation:background')}<input value={String(specSummary.background ?? '')} onChange={(e) => setSpecSummary({ ...specSummary, background: e.target.value })} /></label>
        </div>
        <button type="button" className="btn" disabled={saveSpec.isPending} onClick={() => saveSpec.mutate()}>{t('prompt:semanticSave')}</button>
        <label>{t('prompt:seedMode')}<select value={seedMode} onChange={(e) => setSeedMode(e.target.value)}><option value="random">{t('prompt:seedRandom')}</option><option value="fixed">{t('prompt:seedFixed')}</option></select></label>
        {seedMode === 'fixed' && <label>{t('prompt:seedValue')}<input type="number" min={0} max={2147483647} value={seed} onChange={(e) => setSeed(Number(e.target.value))} /></label>}
        {usePose && <label>{t('generation:poseReference')}<input value={poseUri} onChange={(e) => setPoseUri(e.target.value)} /></label>}
        <label className="checkbox">
          <input
            type="checkbox"
            data-testid="shot-use-pose"
            checked={usePose}
            onChange={(e) => setUsePose(e.target.checked)}
          />
          {t('generation:poseCamera')}
        </label>
      </div>

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
          generateDisabled={render.isPending || saveSpec.isPending || (usePose && !poseUri && !sourceAttemptId) || (draft.stale && !staleDismissed)}
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
          onGenerate={() => render.mutate()}
        />
      )}

      <p className="hint" data-testid="shot-phase">
        {t('generation:statusLabel')}:{' '}
        <span data-testid="shot-status-label">{formatStatus(t, phase)}</span>
      </p>
      <p className="meta" data-testid="shot-id">
        {t('generation:shotId', { id: shotId })}
      </p>
      {(error || autosave.error) && <ErrorBanner message={error || autosave.error} />}
    </section>
  )
}
