import { createHash } from 'node:crypto'
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { API_BASE } from './env'
import { ApiClient, type SeedResult } from './api-client'

/** Qwen first-load can exceed 5m; suite timeout is intentionally generous. */
export const LIVE_TIMEOUT_MS = 10 * 60 * 1000

export type CapabilityMap = Record<
  string,
  {
    configured: boolean
    runtime_available: boolean
    model_id: string | null
    detail: string
  }
>

export async function fetchCapabilities(): Promise<CapabilityMap> {
  const res = await fetch(`${API_BASE}/api/v1/capabilities`)
  if (!res.ok) throw new Error(`capabilities failed: ${res.status}`)
  return res.json()
}

/** Skip when Comfy URL unset / health unavailable. Fail after connect on model/workflow errors. */
export async function requireComfyCapability(capability: string): Promise<CapabilityMap> {
  const caps = await fetchCapabilities()
  const entry = caps[capability]
  if (!entry) {
    throw new Error(`capability missing from registry: ${capability}`)
  }
  if (!entry.configured) {
    throw new Error(`${capability} not configured in model registry`)
  }
  if (!entry.runtime_available) {
    return Promise.reject(
      Object.assign(new Error(`SKIP_COMFY_UNREACHABLE: ${entry.detail}`), {
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
