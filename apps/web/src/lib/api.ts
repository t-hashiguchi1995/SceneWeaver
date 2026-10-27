const API_BASE = ''

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status}: ${text}`)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export type Project = {
  id: string
  title: string
  status: string
  content_rating: string
  created_at: string
  updated_at: string
}

export type WorkflowPrimaryNextKind =
  | 'create_story'
  | 'continue_story'
  | 'choose_outfit'
  | 'configure_shot'
  | 'review_generation'
  | 'create_csp_handoff'
  | 'prepare_release'
  | 'complete'

export type ProjectWorkflow = {
  story: { done: number; total: number }
  shots: { done: number; total: number }
  csp: { ready: boolean; done: boolean }
  release: { ready: boolean; done: null }
  primary_next: {
    kind: WorkflowPrimaryNextKind
    scene_id?: string
    beat_id?: string
    shot_id?: string
    attempt_id?: string
  }
}

export type ProjectDashboard = {
  counts: Record<string, number>
  workflow: ProjectWorkflow
  next_actions: { kind: string; shot_id?: string; attempt_id?: string; scene_id?: string; beat_id?: string }[]
  recent_shots: { id: string; beat_id: string; revision: number; stale_reason: string | null; prompt_stale: boolean }[]
  recent_generations: { id: string; shot_id: string; output_asset_ids: string[]; created_at: string }[]
  latest_handoff: { revision: string; path: string; manifest: Record<string, unknown> } | null
  scenes: Scene[]
  beats: Beat[]
  script_events: (DialogueCandidate & { beat_id: string; locked: boolean; speaker_id: string | null })[]
  adopted_assets: { asset_id: string; shot_id: string; beat_id: string }[]
  tryon_sessions: (TryOnResult & { scene_id: string; character_id: string; outfit_profile_id: string; adopted_asset_id: string | null })[]
  character_ids: string[]
}

export type Job = {
  id: string
  kind: string
  status: string
  payload: Record<string, unknown>
  progress: Record<string, unknown>
  attempts: number
  max_attempts: number
  lease_owner: string | null
  error_message: string | null
  created_at: string
  updated_at: string
}

export type Capability = {
  configured: boolean
  runtime_available: boolean
  model_id: string | null
  detail: string
}

export type Character = {
  id: string
  display_name: string
  visual_identity: Record<string, unknown>
  persona: Record<string, unknown>
}

export type Scene = {
  id: string
  project_id: string
  title: string
  objective: string
}

export type Beat = {
  id: string
  scene_id: string
  intent: string
  speaker_id: string | null
}

export type DialogueCandidate = {
  id: string
  text: string
  tone: string
  critic_scores: Record<string, unknown>
}

export type MarketItem = {
  id: string
  title: string
  category: string
  region: string
  garment_description: string
  style_tags: string[]
  canonical_plate_asset_id: string | null
}

export type VisualLibraryKind =
  | 'outfit'
  | 'pose'
  | 'expression'
  | 'camera'
  | 'lighting'
  | 'background'
  | 'other'

export type VisualLibraryPreviewKind = 'curated' | 'generated' | 'imported_reference'

export type VisualLibraryItemSummary = {
  ref: string
  source_type: 'prompt_preset' | 'marketplace_item'
  source_id: string
  kind: VisualLibraryKind
  label: string
  label_ja?: string | null
  description?: string | null
  thumbnail_asset_id?: string | null
  preview_kind?: VisualLibraryPreviewKind | null
  tags: string[]
  subcategory?: string | null
  content_rating: string
  model_scope: string[]
  related_refs: string[]
  has_preview: boolean
}

export type VisualLibraryItemDetail = VisualLibraryItemSummary & {
  prompt_fragment?: string | null
  source?: string | null
  source_file?: string | null
}

export type TryOnResult = {
  session_id: string
  candidate_asset_ids: string[]
  status: string
}

export type Shot = {
  id: string
  beat_id: string
  revision: number
  render_spec: Record<string, unknown>
  stale_reason: string | null
}

export type RenderResult = {
  shot_id: string
  shot_revision: number
  render_plan_id: string
  generation_attempt_id: string
  output_asset_ids: string[]
  workflow_hash: string
  is_current: boolean
  prompt_hash?: string
  final_positive_prompt?: string
  final_negative_prompt?: string
}

export type GenerationAttemptSummary = {
  id: string
  render_plan_id: string
  based_on_shot_revision: number
  status: string
  seed: number
  payload: Record<string, unknown>
  workflow_hash: string
  output_asset_ids: string[]
  created_at: string
  is_current: boolean
  capability?: string
  workflow_template_id?: string
  model_id?: string
  final_positive_prompt?: string
  final_negative_prompt?: string
  prompt_hash?: string
  source_kind?: string
  source_ref?: string
  template_id?: string
  template_version?: string
  modified?: boolean
  asset_decisions?: Record<string, string>
}

export type PromptDraft = {
  assembly_metadata?: { components?: { ref: string; kind: string; text: string }[]; warnings?: string[]; model_modifiers?: Record<string, unknown>[] }
  id: string
  shot_id: string
  template_id: string
  template_version: string
  source_kind: string
  source_ref: string
  template_label: string
  source_shot_revision: number
  context_hash: string
  rendered_base_positive: string
  rendered_base_negative: string
  edited_positive: string
  edited_negative: string
  modified: boolean
  modified_positive: boolean
  modified_negative: boolean
  stale: boolean
}

export type UserSettings = {
  setup_completed: boolean
  workspace_label: string
  comfy_url: string
  image_backend: string
  llm_provider: string
  llm_base_url: string
  llm_model: string
  llm_api_key_set: boolean
  secrets_backend: string
  eagle_enabled: boolean
  eagle_base_url: string
  csp_export_dir: string
  recent_project_ids: string[]
}

export type DiagnoseCheck = { name: string; ok: boolean; detail: string }

export type ComfyDiagnose = {
  endpoint: string
  reachable: boolean
  detail: string
  ok: boolean
  models: DiagnoseCheck[]
  nodes: DiagnoseCheck[]
  capabilities: DiagnoseCheck[]
}

export type SetupStatus = {
  setup_completed: boolean
  workspace_label: string
  comfy: { url: string; reachable: boolean; detail: string; ok: boolean }
  llm: { provider: string; api_key_set: boolean }
  eagle: { enabled: boolean; base_url: string }
  csp_export_dir: string
  secrets_backend: string
  models: DiagnoseCheck[]
  nodes: DiagnoseCheck[]
}

export const api = {
  listProjects: () => request<Project[]>('/api/v1/projects'),
  createProject: (title: string) =>
    request<Project>('/api/v1/projects', {
      method: 'POST',
      body: JSON.stringify({ title }),
    }),
  getProject: (id: string) => request<Project>(`/api/v1/projects/${id}`),
  listJobs: () => request<Job[]>('/api/v1/jobs'),
  getJob: (id: string) => request<Job>(`/api/v1/jobs/${id}`),
  enqueueStubJob: (payload: Record<string, unknown> = {}) =>
    request<Job>('/api/v1/jobs', {
      method: 'POST',
      body: JSON.stringify({ kind: 'stub', payload }),
    }),
  capabilities: () => request<Record<string, Capability>>('/api/v1/capabilities'),
  getSettings: () => request<UserSettings>('/api/v1/settings'),
  updateSettings: (patch: Partial<UserSettings> & { llm_api_key?: string }) =>
    request<UserSettings>('/api/v1/settings', {
      method: 'PUT',
      body: JSON.stringify(patch),
    }),
  setupStatus: () => request<SetupStatus>('/api/v1/setup/status'),
  completeSetup: () =>
    request<UserSettings>('/api/v1/setup/complete', { method: 'POST' }),
  diagnoseComfy: () =>
    request<ComfyDiagnose>('/api/v1/integrations/comfy/diagnose', { method: 'POST' }),

  getCharacter: (id: string) => request<Character>(`/api/v1/characters/${id}`),
  updatePersona: (id: string, body: Record<string, unknown>) => request<Character>(`/api/v1/characters/${id}/persona`, { method: "PUT", body: JSON.stringify(body) }),
  updateVisualIdentity: (id: string, body: Record<string, unknown>) => request<Character>(`/api/v1/characters/${id}/visual-identity`, { method: "PUT", body: JSON.stringify(body) }),
  assetContentUrl: (id: string) => `/api/v1/assets/${encodeURIComponent(id)}/content`,
  replayGeneration: (id: string, seedMode: "new" | "same") => request<RenderResult>(`/api/v1/generations/${id}/replay`, { method: "POST", body: JSON.stringify({ seed_mode: seedMode }) }),
  updateShot: (id: string, patch: Record<string, unknown>) => request<Shot>(`/api/v1/shots/${id}`, { method: "PUT", body: JSON.stringify(patch) }),
  projectDashboard: (id: string) => request<ProjectDashboard>(`/api/v1/projects/${id}/dashboard`),
  listCharacters: () => request<Character[]>('/api/v1/characters'),
  createCharacter: (displayName: string) =>
    request<Character>('/api/v1/characters', {
      method: 'POST',
      body: JSON.stringify({ display_name: displayName }),
    }),

  createScene: (projectId: string, title: string, objective = '') =>
    request<Scene>(`/api/v1/projects/${projectId}/scenes`, {
      method: 'POST',
      body: JSON.stringify({ title, objective }),
    }),
  createBeat: (sceneId: string, intent: string, speakerId?: string) =>
    request<Beat>(`/api/v1/scenes/${sceneId}/beats`, {
      method: 'POST',
      body: JSON.stringify({ intent, speaker_id: speakerId }),
    }),
  generateDialogue: (beatId: string, characterId: string) =>
    request<{ candidates: DialogueCandidate[]; director_plan: Record<string, unknown> }>(
      `/api/v1/beats/${beatId}/script-events/candidates`,
      {
        method: 'POST',
        body: JSON.stringify({ character_id: characterId }),
      },
    ),
  lockScript: (eventId: string, text?: string) =>
    request<{ id: string; locked: boolean; text: string; revision: number }>(
      `/api/v1/script-events/${eventId}/lock`,
      {
        method: 'PUT',
        body: JSON.stringify({ text }),
      },
    ),

  listMarket: (q = '') =>
    request<MarketItem[]>(`/api/v1/market/items${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  listVisualLibrary: (params: {
    q?: string
    kind?: string
    content_rating?: string
    model?: string
    has_preview?: boolean
  } = {}) => {
    const qs = new URLSearchParams()
    if (params.q) qs.set('q', params.q)
    if (params.kind) qs.set('kind', params.kind)
    if (params.content_rating) qs.set('content_rating', params.content_rating)
    if (params.model) qs.set('model', params.model)
    if (params.has_preview !== undefined) qs.set('has_preview', String(params.has_preview))
    const suffix = qs.toString() ? `?${qs}` : ''
    return request<VisualLibraryItemSummary[]>(`/api/v1/visual-library${suffix}`)
  },
  getVisualLibraryItem: (sourceType: string, sourceId: string) =>
    request<VisualLibraryItemDetail>(
      `/api/v1/visual-library/${encodeURIComponent(sourceType)}/${encodeURIComponent(sourceId)}`,
    ),

  runTryOn: (characterId: string, marketplaceItemId: string, sceneId?: string) =>
    request<TryOnResult>('/api/v1/tryon/sessions', {
      method: 'POST',
      body: JSON.stringify({
        character_id: characterId,
        marketplace_item_id: marketplaceItemId,
        scene_id: sceneId,
      }),
    }),
  adoptTryOn: (sessionId: string, assetId: string, sceneId?: string) =>
    request<{ outfit_profile_id: string; adopted_asset_id: string; references: unknown[] }>(
      `/api/v1/tryon/sessions/${sessionId}/adopt`,
      {
        method: 'POST',
        body: JSON.stringify({ asset_id: assetId, scene_id: sceneId }),
      },
    ),

  planShot: (beatId: string) =>
    request<Shot>(`/api/v1/beats/${beatId}/shots/plan`, { method: 'POST' }),
  promptLibrary: () => request<{ id: string; label: string; category: string; prompt_fragment: string; content_rating: string; source_file: string; version: string }[]>('/api/v1/prompt-library'),
  ensurePromptDraft: (shotId: string) =>
    request<PromptDraft>(`/api/v1/shots/${shotId}/prompt-draft`, { method: 'POST' }),
  getPromptDraft: (shotId: string) => request<PromptDraft>(`/api/v1/shots/${shotId}/prompt-draft`),
  updatePromptDraft: (shotId: string, editedPositive: string, editedNegative: string) =>
    request<PromptDraft>(`/api/v1/shots/${shotId}/prompt-draft`, {
      method: 'PUT',
      body: JSON.stringify({
        edited_positive: editedPositive,
        edited_negative: editedNegative,
      }),
    }),
  resetPromptEdits: (shotId: string) =>
    request<PromptDraft>(`/api/v1/shots/${shotId}/prompt-draft/reset-edits`, { method: 'POST' }),
  rebuildPromptDraft: (shotId: string, confirm = false) =>
    request<PromptDraft>(`/api/v1/shots/${shotId}/prompt-draft/rebuild`, {
      method: 'POST',
      body: JSON.stringify({ confirm }),
    }),
  getPromptTemplate: (shotId: string) =>
    request<{ source_kind: string; source_ref: string; label: string; body: string }>(
      `/api/v1/shots/${shotId}/prompt-template`,
    ),
  getGenerationAttempt: (attemptId: string) =>
    request<GenerationAttemptSummary>(`/api/v1/generation-attempts/${attemptId}`),
  listGenerationAttempts: (shotId: string) =>
    request<{ items: GenerationAttemptSummary[]; count: number }>(
      `/api/v1/shots/${shotId}/generations`,
    ),
  getShot: (shotId: string) => request<Shot>(`/api/v1/shots/${shotId}`),
  getAsset: (assetId: string) =>
    request<{
      id: string
      uri: string
      sha256: string
      mime: string
      kind: string
      provenance: Record<string, unknown>
    }>(`/api/v1/assets/${assetId}`),
  renderShot: (shotId: string, usePose = true, seed?: number, poseAssetUri?: string, sourceAttemptId?: string) =>
    request<RenderResult>(`/api/v1/shots/${shotId}/render`, {
      method: 'POST',
      body: JSON.stringify({
        use_pose: usePose,
        seed,
        source_attempt_id: sourceAttemptId,
        pose_asset_uri: poseAssetUri,
      }),
    }),
  setAssetDecision: (assetId: string, decision: 'adopted' | 'rejected') =>
    request<{ asset_id: string; decision: string; sha256: string }>(
      `/api/v1/assets/${assetId}/decision`,
      {
        method: 'PUT',
        body: JSON.stringify({ decision }),
      },
    ),

  cspHandoff: (body: Record<string, unknown>) =>
    request<{ revision: string; path: string; manifest: Record<string, unknown> }>(
      '/api/v1/csp/handoffs',
      {
        method: 'POST',
        body: JSON.stringify(body),
      },
    ),
  releasePreview: (title: string, summary: string) =>
    request<{ editions: Record<string, unknown>; note: string }>('/api/v1/releases/preview', {
      method: 'POST',
      body: JSON.stringify({ title, summary, hashtags: ['#SceneWeaver'] }),
    }),
}

const CTX_KEY = 'sceneweaver.studio'

export type StudioContext = {
  projectId?: string
  characterId?: string
  characterName?: string
  sceneId?: string
  beatId?: string
  lockedEventId?: string
  lockedText?: string
  marketplaceItemId?: string
  tryonSessionId?: string
  tryonAdoptedAssetId?: string
  outfitProfileId?: string
  shotId?: string
  generationAssetIds?: string[]
  generationAttemptId?: string
  adoptedRenderAssetId?: string
  adoptedRenderSha256?: string
  handoffRevision?: string
  handoffPath?: string
  /** Pose Gallery apply — asset:// URI for LLLite / OpenPose when present. */
  poseAssetUri?: string
  poseId?: string
}

export function loadStudioContext(): StudioContext {
  try {
    return JSON.parse(sessionStorage.getItem(CTX_KEY) ?? '{}') as StudioContext
  } catch {
    return {}
  }
}

export function saveStudioContext(patch: StudioContext): StudioContext {
  const next = { ...loadStudioContext(), ...patch }
  sessionStorage.setItem(CTX_KEY, JSON.stringify(next))
  return next
}
