import { test, expect } from '@playwright/test'
import { ApiClient } from '../../support/api-client'
import {
  LIVE_TIMEOUT_MS,
  assertLiveProvenance,
  getAsset,
  requireComfyCapability,
  seedLive,
} from '../../support/live'

test.describe('live Qwen Try-On', () => {
  test.setTimeout(LIVE_TIMEOUT_MS)

  test('UseCase → Comfy → Asset + provenance', async ({}, testInfo) => {
    let caps
    try {
      caps = await requireComfyCapability('OutfitTryOn')
    } catch (err: any) {
      if (err?.skip || String(err?.message || '').startsWith('SKIP_COMFY_UNREACHABLE')) {
        test.skip(true, err.message)
        return
      }
      throw err
    }

    expect(caps.OutfitTryOn.configured).toBe(true)
    expect(caps.OutfitTryOn.runtime_available).toBe(true)
    expect(caps.OutfitTryOn.model_id).toBeTruthy()

    const seeded = await seedLive('m3_tryon')
    const api = new ApiClient()
    const result = await api.runTryOn(seeded.character_id!, seeded.marketplace_item_id!, seeded.scene_id)

    expect(result.status).toBe('succeeded')
    expect(result.candidate_asset_ids?.length).toBe(4)

    const asset = await getAsset(result.candidate_asset_ids[0])
    expect(asset.byte_size).toBeGreaterThan(0)
    expect(asset.sha256).toMatch(/^[a-f0-9]{64}$/)
    assertLiveProvenance(asset.provenance, {
      provider: 'comfyui',
      workflow_template_id: 'qwen_tryon_v1',
      requireSeed: true,
      requireWorkflowHash: true,
      requireExternalJobRef: true,
    })
    await testInfo.attach('real-comfy-result', { body: JSON.stringify({ result: result, asset }, null, 2), contentType: 'application/json' })
    expect(asset.provenance.model_id).toBe(caps.OutfitTryOn.model_id)
  })
})
