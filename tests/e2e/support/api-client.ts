import { API_BASE } from './env'

export type SeedResult = {
  scenario: string
  project_id?: string
  character_id?: string
  scene_id?: string
  beat_id?: string
  marketplace_item_id?: string
  tryon_base_asset_id?: string
  extras?: Record<string, string>
}

export class ApiClient {
  constructor(private readonly base = API_BASE) {}

  async reset(): Promise<void> {
    const res = await fetch(`${this.base}/api/test/reset`, { method: 'POST' })
    if (!res.ok) throw new Error(`reset failed: ${res.status} ${await res.text()}`)
  }

  async seed(scenario: string): Promise<SeedResult> {
    const res = await fetch(`${this.base}/api/test/seed`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario }),
    })
    if (!res.ok) throw new Error(`seed failed: ${res.status} ${await res.text()}`)
    return res.json()
  }

  async reload(): Promise<void> {
    const res = await fetch(`${this.base}/api/test/reload`, { method: 'POST' })
    if (!res.ok) throw new Error(`reload failed: ${res.status}`)
  }

  async state(): Promise<Record<string, any>> {
    const res = await fetch(`${this.base}/api/test/state`)
    if (!res.ok) throw new Error(`state failed: ${res.status}`)
    return res.json()
  }

  async health(): Promise<Record<string, string>> {
    const res = await fetch(`${this.base}/health`)
    if (!res.ok) throw new Error(`health failed: ${res.status}`)
    return res.json()
  }

  async setAssetDecision(assetId: string, decision: 'adopted' | 'rejected') {
    const res = await fetch(`${this.base}/api/v1/assets/${assetId}/decision`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision }),
    })
    if (!res.ok) throw new Error(`decision failed: ${res.status} ${await res.text()}`)
    return res.json() as Promise<{ asset_id: string; decision: string; sha256: string }>
  }

  async generateDialogue(beatId: string, characterId: string) {
    const res = await fetch(`${this.base}/api/v1/beats/${beatId}/script-events/candidates`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ character_id: characterId }),
    })
    if (!res.ok) throw new Error(`dialogue failed: ${res.status} ${await res.text()}`)
    return res.json()
  }

  async lockScript(eventId: string, text?: string) {
    const res = await fetch(`${this.base}/api/v1/script-events/${eventId}/lock`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    })
    if (!res.ok) throw new Error(`lock failed: ${res.status}`)
    return res.json()
  }

  async runTryOn(characterId: string, marketplaceItemId: string, sceneId?: string) {
    const res = await fetch(`${this.base}/api/v1/tryon/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        character_id: characterId,
        marketplace_item_id: marketplaceItemId,
        scene_id: sceneId,
      }),
    })
    if (!res.ok) throw new Error(`tryon failed: ${res.status} ${await res.text()}`)
    return res.json()
  }

  async adoptTryOn(sessionId: string, assetId: string, sceneId?: string) {
    const res = await fetch(`${this.base}/api/v1/tryon/sessions/${sessionId}/adopt`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ asset_id: assetId, scene_id: sceneId }),
    })
    if (!res.ok) throw new Error(`adopt failed: ${res.status}`)
    return res.json()
  }

  async planShot(beatId: string) {
    const res = await fetch(`${this.base}/api/v1/beats/${beatId}/shots/plan`, { method: 'POST' })
    if (!res.ok) throw new Error(`shot plan failed: ${res.status}`)
    return res.json()
  }

  async renderShot(shotId: string, usePose = false, poseAssetUri?: string) {
    const res = await fetch(`${this.base}/api/v1/shots/${shotId}/render`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        use_pose: usePose,
        pose_asset_uri: usePose
          ? poseAssetUri ?? 'asset://pose/fixture.png'
          : poseAssetUri ?? null,
      }),
    })
    if (!res.ok) throw new Error(`render failed: ${res.status} ${await res.text()}`)
    return res.json()
  }

  get baseUrl() {
    return this.base
  }

  async cspHandoff(body: Record<string, unknown>) {
    const res = await fetch(`${this.base}/api/v1/csp/handoffs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) throw new Error(`handoff failed: ${res.status} ${await res.text()}`)
    return res.json()
  }

  async releasePreview(title: string, summary: string) {
    const res = await fetch(`${this.base}/api/v1/releases/preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, summary, hashtags: ['#SceneWeaver'] }),
    })
    if (!res.ok) throw new Error(`preview failed: ${res.status}`)
    return res.json()
  }
}
