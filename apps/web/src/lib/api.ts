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

  listCharacters: () => request<Character[]>('/api/v1/characters'),
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
  renderShot: (shotId: string, usePose = true) =>
    request<RenderResult>(`/api/v1/shots/${shotId}/render`, {
      method: 'POST',
      body: JSON.stringify({
        use_pose: usePose,
        pose_asset_uri: 'asset://pose/fixture.png',
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
  adoptedRenderAssetId?: string
  adoptedRenderSha256?: string
  handoffRevision?: string
  handoffPath?: string
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
