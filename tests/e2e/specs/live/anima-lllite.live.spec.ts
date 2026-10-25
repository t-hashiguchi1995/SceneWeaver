import { test, expect } from '@playwright/test'
import { ApiClient } from '../../support/api-client'
import {
  LIVE_TIMEOUT_MS,
  MIN_LIVE_IMAGE_EDGE,
  assertAssetImageDecoded,
  assertLiveProvenance,
  getAsset,
  requireComfyCapability,
  seedLive,
} from '../../support/live'

test.describe('live Anima LLLite', () => {
  test.setTimeout(LIVE_TIMEOUT_MS)

  test('UseCase → PoseControlledRender → control provenance', async ({ page }, testInfo) => {
    let caps
    try {
      caps = await requireComfyCapability('PoseControlledRender')
    } catch (err: any) {
      if (err?.skip || String(err?.message || '').startsWith('SKIP_COMFY_UNREACHABLE')) {
        test.skip(true, err.message)
        return
      }
      throw err
    }

    expect(caps.PoseControlledRender.configured).toBe(true)
    expect(caps.PoseControlledRender.runtime_available).toBe(true)

    const seeded = await seedLive('m4_visual')
    const poseUri = seeded.extras?.pose_asset_uri
    expect(typeof poseUri).toBe('string')
    const poseAssetUri = String(poseUri)

    const api = new ApiClient()
    const dialogue = await api.generateDialogue(seeded.beat_id!, seeded.character_id!)
    await api.lockScript(dialogue.candidates[0].id)
    const shot = await api.planShot(seeded.beat_id!)

    let rendered: Record<string, any>
    try {
      rendered = await api.renderShot(shot.id, true, poseAssetUri)
    } catch (err: any) {
      // Real Comfy errors after connect must fail (not skip)
      throw new Error(`LLLite render failed: ${err?.message ?? err}`)
    }

    expect(rendered.output_asset_ids?.length).toBe(4)
    expect(rendered.external_job_ref).toBeTruthy()

    const asset = await getAsset(rendered.output_asset_ids[0])
    expect(asset.byte_size).toBeGreaterThan(0)
    assertLiveProvenance(asset.provenance, {
      provider: 'comfyui',
      workflow_template_id: 'anima_pose_v1',
      requireSeed: true,
      requireWorkflowHash: true,
      requireExternalJobRef: true,
      control: true,
    })
    expect(asset.provenance.pose_asset_uri).toBe(poseAssetUri)
    const dims = await assertAssetImageDecoded(page, rendered.output_asset_ids[0], {
      minEdge: MIN_LIVE_IMAGE_EDGE,
    })
    await testInfo.attach('real-comfy-result', {
      body: JSON.stringify({ result: rendered, asset, dims }, null, 2),
      contentType: 'application/json',
    })
  })
})
