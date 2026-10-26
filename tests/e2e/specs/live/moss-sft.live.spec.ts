/**
 * Gate 1 — Stock MOSS-SFT real Comfy smoke (LayoutGuidedRender).
 *
 * Neutral smoke only (generic woman) — NOT target-character fixture validation.
 * Target fixtures = Gate 2.5 (see docs/validation/).
 *
 * Pass = real PNG (≥512), SHA256, provenance, moss_caption path, artifact attach.
 * Same-seed Comfy replay is covered by ``pnpm test:moss:live`` (pytest) to keep
 * this Playwright budget on one generation.
 *
 * Entry: ``pnpm test:moss:e2e:live:required``
 */
import { test, expect } from '@playwright/test'
import { ApiClient } from '../../support/api-client'
import {
  LIVE_TIMEOUT_MS,
  MIN_LIVE_IMAGE_EDGE,
  assertAssetImageDecoded,
  assertLiveProvenance,
  attachLiveImageArtifact,
  fetchComfyVersion,
  getAsset,
  requireComfyCapability,
  seedLive,
} from '../../support/live'

test.describe('live MOSS-SFT Gate1', () => {
  // One MOSS batch (often 4 candidates × 50 steps) after cold load.
  test.setTimeout(Math.max(LIVE_TIMEOUT_MS, 20 * 60 * 1000))

  test('UseCase → Comfy LayoutGuidedRender → decodeable PNG + provenance', async ({
    page,
  }, testInfo) => {
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

    expect(caps.LayoutGuidedRender.configured).toBe(true)
    expect(caps.LayoutGuidedRender.runtime_available).toBe(true)
    expect(caps.LayoutGuidedRender.model_id).toBe('moss_image_sft')

    const seeded = await seedLive('m4_visual')
    const api = new ApiClient()
    const dialogue = await api.generateDialogue(seeded.beat_id!, seeded.character_id!)
    await api.lockScript(dialogue.candidates[0].id)
    const shot = await api.planShot(seeded.beat_id!)
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
    for (const marker of ['safe', '@fuzichoco', '@rella', 'score_9', 'masterpiece']) {
      expect(draft.rendered_base_positive).not.toContain(marker)
    }

    const seed = 12345
    const t0 = Date.now()
    const rendered = await api.renderShot(shot.id, false, undefined, { seed })
    testInfo.annotations.push({
      type: 'moss_render_ms',
      description: String(Date.now() - t0),
    })
    expect(rendered.output_asset_ids?.length).toBeGreaterThanOrEqual(1)
    expect(rendered.workflow_hash).toBeTruthy()
    expect(rendered.external_job_ref).toBeTruthy()
    expect(rendered.generation_attempt_id).toBeTruthy()

    const assetId = rendered.output_asset_ids[0] as string
    const asset = await getAsset(assetId)
    expect(asset.byte_size).toBeGreaterThan(0)
    expect(asset.sha256).toMatch(/^[a-f0-9]{64}$/)
    assertLiveProvenance(asset.provenance, {
      provider: 'comfyui',
      workflow_template_id: 'moss_sft_v1',
      model_id: 'moss_image_sft',
      requireSeed: true,
      requireWorkflowHash: true,
      requireExternalJobRef: true,
    })
    expect(asset.provenance.seed).toBe(seed)
    expect(String(asset.provenance.final_positive_prompt || '')).not.toContain('safe')
    expect(String(asset.provenance.final_positive_prompt || '')).not.toContain('@fuzichoco')

    const dims = await assertAssetImageDecoded(page, assetId, {
      minEdge: MIN_LIVE_IMAGE_EDGE,
      browserDecode: false,
    })
    expect(dims.width).toBeGreaterThanOrEqual(MIN_LIVE_IMAGE_EDGE)
    expect(dims.height).toBeGreaterThanOrEqual(MIN_LIVE_IMAGE_EDGE)
    const comfyVersion = await fetchComfyVersion()
    await attachLiveImageArtifact(testInfo, 'moss-gate1', dims.bytes, {
      gate: 'moss-sft-gate1',
      status: 'passed',
      capability: 'LayoutGuidedRender',
      model_id: 'moss_image_sft',
      workflow_template_id: 'moss_sft_v1',
      workflow_hash: rendered.workflow_hash,
      seed,
      prompt_hash: asset.provenance.prompt_hash ?? null,
      width: dims.width,
      height: dims.height,
      mime: asset.mime || 'image/png',
      sha256: asset.sha256,
      external_job_ref: rendered.external_job_ref ?? asset.provenance.external_job_ref,
      comfy_version: comfyVersion,
      image_file: 'moss-gate1.png',
      asset_id: assetId,
      source_ref: draft.source_ref,
      generation_attempt_id: rendered.generation_attempt_id,
      note: 'neutral smoke — not target-character fixture validation',
    })
  })
})
