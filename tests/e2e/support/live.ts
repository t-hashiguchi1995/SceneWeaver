import { createHash } from 'node:crypto'
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { expect, type Page, type TestInfo } from '@playwright/test'
import { API_BASE } from './env'
import { ApiClient, type SeedResult } from './api-client'

/** Qwen first-load can exceed 5m; suite timeout is intentionally generous. */
export const LIVE_TIMEOUT_MS = 10 * 60 * 1000

/** MOSS / #B+ live bar: decodeable raster at least this edge length. */
export const MIN_LIVE_IMAGE_EDGE = 512

export type CapabilityMap = Record<
  string,
  {
    configured: boolean
    runtime_available: boolean
    model_id: string | null
    detail: string
  }
>

/** #B/#C merge gate: Comfy unreachable must FAIL (not skip). */
export function isLiveRequired(): boolean {
  const v = (process.env.SCENEWEAVER_LIVE_REQUIRED || '').toLowerCase()
  return v === '1' || v === 'true' || v === 'yes'
}

export async function fetchCapabilities(): Promise<CapabilityMap> {
  const res = await fetch(`${API_BASE}/api/v1/capabilities`)
  if (!res.ok) throw new Error(`capabilities failed: ${res.status}`)
  return res.json()
}

/** ComfyUI version string for Gate manifests (native MOSS boundary). */
export async function fetchComfyVersion(
  comfyUrl = process.env.COMFY_BASE_URL || process.env.SCENEWEAVER_COMFY_URL || 'http://127.0.0.1:8188',
): Promise<string> {
  try {
    const res = await fetch(`${comfyUrl.replace(/\/$/, '')}/system_stats`)
    if (!res.ok) return `unreachable:${res.status}`
    const data = (await res.json()) as { system?: { comfyui_version?: string } }
    return String(data.system?.comfyui_version || 'unknown')
  } catch (err) {
    return `unreachable:${err instanceof Error ? err.message : String(err)}`
  }
}

/**
 * Dev live (`pnpm test:e2e:live`): Comfy unreachable → skip.
 * Required live (`pnpm test:e2e:live:required` / SCENEWEAVER_LIVE_REQUIRED=1): FAIL.
 * Model/workflow errors after connect always fail.
 */
export async function requireComfyCapability(
  capability: string,
  opts?: { required?: boolean },
): Promise<CapabilityMap> {
  const required = opts?.required ?? isLiveRequired()
  const caps = await fetchCapabilities()
  const entry = caps[capability]
  if (!entry) {
    throw new Error(`capability missing from registry: ${capability}`)
  }
  if (!entry.configured) {
    throw new Error(`${capability} not configured in model registry`)
  }
  if (!entry.runtime_available) {
    const detail = entry.detail || 'runtime unavailable'
    if (required) {
      throw new Error(`COMFY_RUNTIME_UNAVAILABLE (${capability}): ${detail}`)
    }
    return Promise.reject(
      Object.assign(new Error(`SKIP_COMFY_UNREACHABLE: ${detail}`), {
        skip: true,
      }),
    )
  }
  return caps
}

export async function getAsset(assetId: string) {
  const res = await fetch(`${API_BASE}/api/v1/assets/${assetId}`)
  if (!res.ok) throw new Error(`get asset failed: ${res.status} ${await res.text()}`)
  return res.json() as Promise<{
    id: string
    sha256: string
    uri: string
    kind: string
    mime: string
    byte_size: number
    provenance: Record<string, unknown>
    metadata: Record<string, unknown>
  }>
}

export function sha256File(path: string): string {
  const buf = readFileSync(path)
  return createHash('sha256').update(buf).digest('hex')
}

export function resolveRuntimeAssetPath(uri: string, runtimeDir: string): string | null {
  if (!uri.startsWith('asset://')) return null
  const rest = uri.slice('asset://'.length)
  const [sha, ...nameParts] = rest.split('/')
  const filename = nameParts.join('/')
  const needle = `${sha}_${filename}`
  const root = join(runtimeDir, 'assets')
  if (!existsSync(root)) return null
  const stack = [root]
  while (stack.length) {
    const dir = stack.pop()!
    for (const ent of readdirSync(dir)) {
      const full = join(dir, ent)
      if (statSync(full).isDirectory()) stack.push(full)
      else if (ent === needle) return full
    }
  }
  return null
}

export async function seedLive(scenario: string): Promise<SeedResult> {
  const api = new ApiClient()
  await api.reset()
  return api.seed(scenario)
}

export function assertLiveProvenance(
  provenance: Record<string, unknown>,
  expected: {
    provider?: string
    workflow_template_id?: string
    model_id?: string
    capability?: string
    requireSeed?: boolean
    requireWorkflowHash?: boolean
    requireExternalJobRef?: boolean
    control?: boolean
  },
) {
  if (expected.provider && provenance.provider !== expected.provider) {
    throw new Error(`provider want ${expected.provider} got ${provenance.provider}`)
  }
  if (
    expected.workflow_template_id &&
    provenance.workflow_template_id !== expected.workflow_template_id
  ) {
    throw new Error(
      `workflow_template_id want ${expected.workflow_template_id} got ${provenance.workflow_template_id}`,
    )
  }
  if (expected.model_id && provenance.model_id !== expected.model_id) {
    throw new Error(`model_id want ${expected.model_id} got ${provenance.model_id}`)
  }
  if (expected.capability && provenance.capability !== expected.capability) {
    throw new Error(`capability want ${expected.capability} got ${provenance.capability}`)
  }
  if (expected.requireSeed && (provenance.seed === null || provenance.seed === undefined)) {
    throw new Error('seed missing in provenance')
  }
  if (expected.requireWorkflowHash && !provenance.workflow_hash) {
    throw new Error('workflow_hash missing in provenance')
  }
  if (expected.requireExternalJobRef && !provenance.external_job_ref) {
    throw new Error('external_job_ref missing in provenance')
  }
  if (expected.control) {
    if (!provenance.pose_asset_uri && !provenance.pose_asset_id) {
      throw new Error('pose/control ref missing in provenance')
    }
    if (!provenance.control_model) {
      throw new Error('control_model missing in provenance')
    }
    if (provenance.control_strength === null || provenance.control_strength === undefined) {
      throw new Error('control_strength missing in provenance')
    }
  }
}

/** Read width/height from PNG IHDR (no native image deps). */
export function readPngSize(buf: Buffer): { width: number; height: number } {
  if (buf.length < 24 || buf[0] !== 0x89 || buf[1] !== 0x50) {
    throw new Error('asset content is not a PNG')
  }
  return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) }
}

/**
 * Fetch Asset bytes and require a decodeable PNG with edge ≥ minEdge.
 *
 * Default: PNG IHDR parse (sufficient for Gate 1; avoids ~1MB+ data-URL hangs).
 * Set ``browserDecode: true`` to also load via &lt;img&gt; (Anima-sized fixtures OK).
 */
export async function assertAssetImageDecoded(
  page: Page,
  assetId: string,
  opts?: { minEdge?: number; apiBase?: string; browserDecode?: boolean },
): Promise<{ width: number; height: number; bytes: Buffer }> {
  const minEdge = opts?.minEdge ?? MIN_LIVE_IMAGE_EDGE
  const base = opts?.apiBase ?? API_BASE
  const url = `${base}/api/v1/assets/${encodeURIComponent(assetId)}/content`
  const res = await page.request.get(url)
  if (!res.ok()) {
    throw new Error(`asset content HTTP ${res.status()} for ${assetId}`)
  }
  const bytes = Buffer.from(await res.body())
  const ihdr = readPngSize(bytes)
  if (Math.min(ihdr.width, ihdr.height) < minEdge) {
    throw new Error(
      `PNG too small: ${ihdr.width}x${ihdr.height} (need >= ${minEdge})`,
    )
  }
  if (opts?.browserDecode === false || opts?.browserDecode === undefined) {
    // Gate 1 / large MOSS outputs: IHDR is the automated decode bar.
    return { width: ihdr.width, height: ihdr.height, bytes }
  }
  // Optional browser path for smaller fixtures (route fulfill — not data-URL).
  const routePattern = '**/__sceneweaver_live_asset.png'
  await page.route(routePattern, async (route) => {
    await route.fulfill({ status: 200, contentType: 'image/png', body: bytes })
  })
  try {
    await page.setContent(
      '<!doctype html><img id="live-asset" alt="live-asset" src="http://127.0.0.1/__sceneweaver_live_asset.png" />',
      { waitUntil: 'domcontentloaded' },
    )
    const img = page.locator('#live-asset')
    await expect
      .poll(async () => {
        const dims = await img.evaluate((el: HTMLImageElement) => ({
          w: el.naturalWidth,
          h: el.naturalHeight,
          complete: el.complete,
        }))
        return dims.complete ? Math.min(dims.w, dims.h) : 0
      })
      .toBeGreaterThanOrEqual(minEdge)
    const decoded = await img.evaluate((el: HTMLImageElement) => ({
      width: el.naturalWidth,
      height: el.naturalHeight,
    }))
    return { ...decoded, bytes }
  } finally {
    await page.unroute(routePattern)
  }
}

/** Attach PNG bytes + JSON manifest for human Gate review. */
export async function attachLiveImageArtifact(
  testInfo: TestInfo,
  name: string,
  bytes: Buffer,
  manifest: Record<string, unknown>,
): Promise<void> {
  await testInfo.attach(`${name}.png`, { body: bytes, contentType: 'image/png' })
  await testInfo.attach(`${name}.manifest.json`, {
    body: Buffer.from(JSON.stringify(manifest, null, 2)),
    contentType: 'application/json',
  })
}
