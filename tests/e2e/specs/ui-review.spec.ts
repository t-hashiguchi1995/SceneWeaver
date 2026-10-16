import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import type { Page } from '@playwright/test'
import { test, expect } from '../fixtures/sceneweaver.fixture'

// Opt-in review artifacts. Never connects to a logged-in browser or publishes.
const enabled = process.env.SCENEWEAVER_UI_REVIEW === '1'
const root = resolve('../..')
const output = resolve(root, 'docs/validation/ui-review-20261012')
const sources = [1, 2, 3, 4].map(n => resolve(root,
  `docs/validation/rize-comic/20261011T094102940732Z/images/cafe_four_panel-${n}-1.png`))
const sizes = [
  { name: 'desktop', width: 1280, height: 800 },
  { name: 'wide', width: 1920, height: 1080 },
  { name: 'mobile', width: 390, height: 844 },
]

for (const size of sizes) {
  test(`UI review screenshots: ${size.name}`, async ({ page, api, seedScenario }, testInfo) => {
    test.skip(!enabled, 'Set SCENEWEAVER_UI_REVIEW=1 to capture review artifacts')
    test.setTimeout(180_000)
    await page.setViewportSize({ width: size.width, height: size.height })
    const dir = resolve(output, size.name)
    await mkdir(dir, { recursive: true })
    const images = await Promise.all(sources.map(path => readFile(path)))
    const displayedAssets = new Map<string, number>()
    // Only generated/try-on asset content is substituted. State-changing APIs
    // remain real; this is a layout review, not a GPU/provenance test.
    await page.route('**/api/v1/assets/*/content', async route => {
      const id = new URL(route.request().url()).pathname.split('/').at(-2)!
      const index = displayedAssets.get(id)
      if (index === undefined) return route.continue()
      await route.fulfill({ status: 200, contentType: 'image/png', body: images[index % images.length] })
    })
    const pageErrors: string[] = []
    page.on('pageerror', error => pageErrors.push(error.message))
    const captures: Record<string, unknown>[] = []
    const capture = async (name: string, state: string, element?: ReturnType<Page['locator']>) => {
      await page.evaluate(() => document.fonts.ready)
      await expect.poll(() => page.locator('img').evaluateAll(nodes => nodes.every(n =>
        !n.getClientRects().length || (n.complete && n.naturalWidth > 0)))).toBe(true)
      const path = resolve(dir, `${name}.png`)
      if (element) await element.screenshot({ path, animations: 'disabled' })
      else {
        await page.evaluate(() => window.scrollTo(0, 0))
        await page.screenshot({ path, fullPage: true, animations: 'disabled' })
      }
      const horizontalOverflow = await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      )
      expect(horizontalOverflow).toBe(false)
      captures.push({
        file: `${name}.png`,
        state,
        path: new URL(page.url()).pathname,
        headings: await page.locator('h1,h2').allTextContents(),
        horizontalOverflow,
      })
    }
    const seeded = await seedScenario('m3_tryon')
    const project = `/projects/${seeded.project_id}`
    const dialogue = await api.generateDialogue(seeded.beat_id!, seeded.character_id!)
    await api.lockScript(dialogue.candidates[0].id, 'このお店の「普通」、強いですね。')

    await page.goto('/')
    await expect(page.getByTestId('recent-projects')).not.toBeEmpty()
    await capture('01_home', 'populated')
    await page.goto(project)
    await expect(page.getByRole('heading', { name: '次にすること' })).toBeVisible()
    await capture('02_project_dashboard', 'populated; next actions')
    await page.goto(`/characters/${seeded.character_id}`)
    await expect(page.getByTestId('character-field-first_person')).toBeVisible()
    await capture('03_character', 'persona populated')
    await page.goto(`${project}/story`)
    await expect(page.getByTestId('story-scene-select')).toHaveValue(seeded.scene_id!)
    await expect(page.getByTestId('story-page')).toContainText('このお店の「普通」、強いですね。')
    await capture('04_story', 'locked dialogue')
    await page.goto(`${project}/wardrobe`)
    await expect(page.getByTestId('market-item')).toHaveCount(1)
    await page.getByTestId('market-list').getByRole('button', { name: /Cardigan/ }).click()
    await capture('05_wardrobe_market', 'outfit selected')
    const tryon = await api.runTryOn(seeded.character_id!, seeded.marketplace_item_id!, seeded.scene_id)
    for (const [index, id] of (tryon.candidate_asset_ids as string[]).entries()) displayedAssets.set(id, index)
    await page.reload()
    await expect(page.getByTestId('tryon-candidate-list').locator('img')).toHaveCount(4)
    await capture('06_tryon_review', 'succeeded; display fixture images, not real try-on output')
    await page.getByTestId('tryon-adopt-0').click()
    await expect(page.getByTestId('tryon-adopted-banner')).toBeVisible()

    const shot = await api.planShot(seeded.beat_id!)
    const studio = `${project}/shots/${shot.id}`
    const review = `${studio}/generations`
    await page.goto(review)
    await expect(page.getByTestId('generation-history')).toContainText('履歴')
    await expect(page.getByTestId('generation-history').locator('li')).toHaveCount(0)
    await capture('14_empty_history', 'no generation attempts')
    await page.goto(studio)
    await expect(page.getByTestId('prompt-positive')).toBeVisible()
    await capture('07_shot_studio', 'semantic settings and prompt')
    await capture('08_prompt_editor', 'prompt editor detail', page.getByTestId('prompt-editor'))
    const draft = page.getByTestId('prompt-positive')
    await draft.fill(`${await draft.inputValue()}, warm cafe light`)
    await expect(page.getByTestId('prompt-template-label')).toContainText('編集済み')
    await capture('15_prompt_modified', 'edited; autosave may finish during screenshot')
    await expect(page.getByTestId('prompt-save-status')).toHaveText('保存済み')
    await page.getByLabel('表情', { exact: true }).fill('smile')
    await page.getByRole('button', { name: 'ショット設定を保存', exact: true }).click()
    await expect(page.getByTestId('prompt-stale-banner')).toBeVisible()
    await capture('16_prompt_stale', 'semantic setting changed; stale')
    await page.getByTestId('prompt-keep-stale').click()

    const renderUrl = `**/api/v1/shots/${shot.id}/render`
    await page.route(renderUrl, route => route.fulfill({ status: 503, contentType: 'application/json',
      body: JSON.stringify({ detail: 'COMFY_UNREACHABLE: UI review simulated connection failure' }) }))
    await page.getByTestId('shot-generate').click()
    await expect(page.getByTestId('shot-status-label')).toHaveText('失敗')
    await expect(page.getByTestId('error-banner')).toBeVisible()
    await capture('17_generation_failed', 'injected 503; error recovery link')
    await page.unroute(renderUrl)
    await page.goto(studio)
    await expect(page.getByTestId('prompt-positive')).toBeVisible()
    if (await page.getByTestId('prompt-stale-banner').isVisible()) await page.getByTestId('prompt-keep-stale').click()
    await page.route(renderUrl, async route => {
      await new Promise(resolveDelay => setTimeout(resolveDelay, 6000))
      const response = await route.fetch()
      const result = await response.json()
      for (const [index, id] of (result.output_asset_ids as string[]).entries()) displayedAssets.set(id, index)
      await route.fulfill({ response })
    })
    await page.getByTestId('shot-generate').click()
    await expect(page.getByTestId('shot-status-label')).toHaveText('処理中')
    await capture('18_generating', 'real fake-backend render delayed 6 seconds')
    await expect(page.getByTestId('generation-candidate-list').locator('img')).toHaveCount(4)
    await page.unroute(renderUrl)
    await capture('09_generation_review', 'succeeded; four display fixture images')
    await page.getByTestId('generation-adopt').click()
    await expect(page.getByTestId('generation-adopted-banner')).toBeVisible()
    await capture('19_adopted_candidate', 'adopted decision persisted')
    await page.goto(`${project}/csp`)
    await expect(page.getByTestId('csp-page-plan').locator('img')).toHaveCount(1)
    await page.getByTestId('csp-build-handoff').click()
    await expect(page.getByTestId('csp-revision')).toHaveText('r001')
    await capture('10_csp', 'page plan and successful handoff; bytes are fake backend bytes')
    await page.goto(`${project}/release`)
    await page.getByTestId('release-title').fill('リゼ・ヘルエスタ：カフェの寄り道')
    await page.getByTestId('release-summary').fill('創作4コマのプレビューです。\nAI生成画像を使用しています。')
    await page.getByTestId('release-preview-button').click()
    await page.getByTestId('release-tab-patreon').click()
    await expect(page.getByTestId('release-edition-patreon')).toBeVisible()
    await capture('11_release', 'master form and platform tab previews; no publishing')
    await page.goto('/integrations')
    await expect(page.getByTestId('integration-comfy')).toBeVisible()
    await capture('12_integrations', 'configured test integrations; no diagnosis request')
    await page.goto('/settings')
    await expect(page.getByTestId('settings-comfy-url')).toBeVisible()
    await expect(page.getByTestId('settings-llm-key')).toHaveValue('')
    await capture('13_settings', 'isolated test settings; no saved API key')
    expect(pageErrors).toEqual([])
    const manifest = { viewport: size,
      appCodeCommit: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim(),
      captureSpecSha256: createHash('sha256').update(await readFile(resolve(root, 'tests/e2e/specs/ui-review.spec.ts'))).digest('hex'),
      environment: 'isolated e2e; real API/DB; stub LLM; fake image backend',
      imageSubstitution: 'Generated/try-on image GET responses only. These display fixtures do not match fake Asset hashes or CSP bytes. No GPU or real outfit evaluation.',
      sourceImages: sources.map((path, index) => ({ path: path.slice(root.length + 1), sha256: createHash('sha256').update(images[index]).digest('hex') })),
      captures, pageErrors,
    }
    await writeFile(resolve(dir, 'manifest.json'), JSON.stringify(manifest, null, 2))
    await testInfo.attach('UI review manifest', { body: JSON.stringify(manifest, null, 2), contentType: 'application/json' })
  })
}
