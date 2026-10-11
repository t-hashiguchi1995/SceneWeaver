import { test, expect } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { ApiClient } from '../../support/api-client'
import { LIVE_TIMEOUT_MS, getAsset, requireComfyCapability, seedLive } from '../../support/live'

test('ZIP library → default prompt → real Comfy four images', async ({ page }, testInfo) => {
  test.setTimeout(LIVE_TIMEOUT_MS)
  const zip = process.env.SCENEWEAVER_LIVE_PROMPTS_ZIP ?? '/mnt/c/Users/hassy/Downloads/playwright_project-master/prompts.zip'
  test.skip(!existsSync(zip), 'Set SCENEWEAVER_LIVE_PROMPTS_ZIP to the prompt archive')
  await requireComfyCapability('BaseRender')
  const seeded = await seedLive('m4_visual')
  const runtime = resolve(process.env.SCENEWEAVER_RUNTIME_DIR ?? '../../runtime-live-test')
  execFileSync('uv', ['run', 'python', 'scripts/import_legacy_prompts.py', '--source', zip, '--apply'], {
    cwd: resolve('../..'), env: { ...process.env, SCENEWEAVER_DATABASE_URL: `sqlite:///${runtime}` + '/studio.db' },
  })
  const api = new ApiClient()
  const library = await (await fetch(`${api.baseUrl}/api/v1/prompt-library`)).json()
  const chosen = library.filter((p: any) => p.source_file === 'dynamic/sfw_cafe_date.yaml' && ['costume_cafe_casual_sfw:0', 'location_cafe_date_sfw:0'].some(key => p.label === key.replace(':', '-')))
  // String snippets use category-index labels.
  expect(chosen).toHaveLength(2)
  const dialogue = await api.generateDialogue(seeded.beat_id!, seeded.character_id!)
  await api.lockScript(dialogue.candidates[0].id)
  const shot = await api.planShot(seeded.beat_id!)
  await fetch(`${api.baseUrl}/api/v1/shots/${shot.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt_preset_ids: chosen.map((p: any) => p.id) }) })
  const draft = await (await fetch(`${api.baseUrl}/api/v1/shots/${shot.id}/prompt-draft`, { method: 'POST' })).json()
  expect(draft.rendered_base_positive).toContain('cozy cafe')
  expect(draft.rendered_base_positive).toContain('cardigan')
  expect(draft.rendered_base_positive).toContain('gentle shadows')
  const rendered = await api.renderShot(shot.id)
  expect(rendered.output_asset_ids).toHaveLength(4)
  await testInfo.attach('prompt-library-generation', { body: JSON.stringify({ chosen, draft, rendered, asset: await getAsset(rendered.output_asset_ids[0]) }, null, 2), contentType: 'application/json' })
  for (const id of rendered.output_asset_ids) {
    await page.goto(`${api.baseUrl}/api/v1/assets/${id}/content`)
    await expect.poll(() => page.locator('img').evaluate((img: HTMLImageElement) => img.naturalWidth)).toBeGreaterThan(100)
  }
  await page.screenshot({ path: testInfo.outputPath('real-library-image.png') })
})
