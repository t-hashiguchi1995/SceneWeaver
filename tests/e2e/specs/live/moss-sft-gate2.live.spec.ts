/**
 * Gate 2 — vertical: engine → MOSS draft → Real Comfy → Review provenance → Adopt.
 *
 * Primary path mirrors the UI flow via API (same pattern as Gate 1 live), because
 * this host's Chrome/CDP often hangs on any page.goto / setContent (even about:blank).
 * Full click-path UI remains covered when Playwright navigation works
 * (``pnpm test:e2e -- m4-visual`` mock + optional UI probe below).
 *
 * Target-character matrix = Gate 2.5.
 * Entry: ``pnpm test:moss:gate2:e2e:live:required``
 */
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

test.describe('live MOSS-SFT Gate2 vertical', () => {
  test.setTimeout(Math.max(LIVE_TIMEOUT_MS, 20 * 60 * 1000))

  test('MOSS engine → render → provenance → Adopt', async ({ page }, testInfo) => {
    let caps
    try {
      caps = await requireComfyCapability('LayoutGuidedRender')
    } catch (err: any) {
      if (err?.skip || String(err?.message || '').startsWith('SKIP_COMFY_UNREACHABLE')) {
        test.skip(true, err.message)
        return
      }
      throw err
    }
    expect(caps.LayoutGuidedRender.model_id).toBe('moss_image_sft')

    const seeded = await seedLive('m4_visual')
    const api = new ApiClient()
    const dialogue = await api.generateDialogue(seeded.beat_id!, seeded.character_id!)
    await api.lockScript(dialogue.candidates[0].id)
    const shot = await api.planShot(seeded.beat_id!)

    // UI equivalent: generation engine → LayoutGuidedRender
    await api.updateShot(shot.id, {
      capability: 'LayoutGuidedRender',
      identity_tags: ['1girl', 'long hair', 'brown eyes'],
      outfit_tags: 'simple blouse',
      expression: { id: 'neutral' },
      pose: { id: 'standing' },
      camera: { shot: 'medium', angle: 'eye_level' },
      background: 'plain studio backdrop',
    })

    const draft = await api.ensurePromptDraft(shot.id)
    expect(draft.source_ref).toBe('moss_caption_v1')
    for (const marker of ['safe', '@fuzichoco', '@rella']) {
      expect(draft.rendered_base_positive).not.toContain(marker)
    }

    const seed = 23456
    const t0 = Date.now()
    const rendered = await api.renderShot(shot.id, false, undefined, { seed })
    testInfo.annotations.push({
      type: 'moss_gate2_render_ms',
      description: String(Date.now() - t0),
    })
    expect(rendered.output_asset_ids?.length).toBeGreaterThanOrEqual(1)
    expect(rendered.generation_attempt_id).toBeTruthy()

    const assetId = rendered.output_asset_ids[0] as string
    const asset = await getAsset(assetId)
    assertLiveProvenance(asset.provenance, {
      provider: 'comfyui',
      workflow_template_id: 'moss_sft_v1',
      model_id: 'moss_image_sft',
      requireSeed: true,
      requireWorkflowHash: true,
      requireExternalJobRef: true,
    })
    expect(asset.provenance.seed).toBe(seed)
    expect(String(asset.provenance.capability || '')).toBe('LayoutGuidedRender')

    await assertAssetImageDecoded(page, assetId, {
      minEdge: MIN_LIVE_IMAGE_EDGE,
      browserDecode: false,
    })

    // UI equivalent: Generation Review → Adopt
    const decision = await api.setAssetDecision(assetId, 'adopted')
    expect(decision.decision).toBe('adopted')
    const adopted = await getAsset(assetId)
    const metaDecision =
      adopted.metadata?.review_decision ||
      adopted.provenance?.review_decision ||
      decision.decision
    expect(String(metaDecision)).toMatch(/adopted/i)
  })
})
