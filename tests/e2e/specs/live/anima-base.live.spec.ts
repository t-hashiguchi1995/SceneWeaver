import { test, expect } from '@playwright/test'
import { ApiClient } from '../../support/api-client'
import {
  LIVE_TIMEOUT_MS,
  assertLiveProvenance,
  getAsset,
  requireComfyCapability,
  seedLive,
} from '../../support/live'

test.describe('live Anima Base', () => {
  test.setTimeout(LIVE_TIMEOUT_MS)

  test('UseCase → Comfy BaseRender → Asset + provenance', async () => {
    let caps
    try {
      caps = await requireComfyCapability('BaseRender')
    } catch (err: any) {
      if (err?.skip || String(err?.message || '').startsWith('SKIP_COMFY_UNREACHABLE')) {
        test.skip(true, err.message)
        return
      }
      throw err
    }

    expect(caps.BaseRender.configured).toBe(true)
    expect(caps.BaseRender.runtime_available).toBe(true)

    const seeded = await seedLive('m4_visual')
    const api = new ApiClient()
    const dialogue = await api.generateDialogue(seeded.beat_id!, seeded.character_id!)
    await api.lockScript(dialogue.candidates[0].id)
    const shot = await api.planShot(seeded.beat_id!)
    const rendered = await api.renderShot(shot.id, false)

    expect(rendered.output_asset_ids?.length).toBeGreaterThanOrEqual(1)
    expect(rendered.workflow_hash).toBeTruthy()
    expect(rendered.external_job_ref).toBeTruthy()

    const asset = await getAsset(rendered.output_asset_ids[0])
    expect(asset.byte_size).toBeGreaterThan(0)
    expect(asset.sha256).toMatch(/^[a-f0-9]{64}$/)
    assertLiveProvenance(asset.provenance, {
      provider: 'comfyui',
      workflow_template_id: 'anima_base_v1',
      requireSeed: true,
      requireWorkflowHash: true,
      requireExternalJobRef: true,
    })
    expect(asset.provenance.prompt_version).toBe('anima_compiler_v1')
    expect(asset.provenance.model_id).toBe(caps.BaseRender.model_id)
  })
})
