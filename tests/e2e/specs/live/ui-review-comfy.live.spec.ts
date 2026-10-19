/**
 * Real-Comfy UX review: Story → Generate → Adopt continuous flow.
 * Opt-in: SCENEWEAVER_UI_REVIEW_LIVE=1
 *
 * CX-F0 focus: Project Context Bar stays stable across screens while real
 * Comfy pixels are shown (no asset-content substitution).
 */
import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import type { Page } from '@playwright/test'
import { test, expect } from '@playwright/test'

import { ApiClient } from '../../support/api-client'
import {
  LIVE_TIMEOUT_MS,
  requireComfyCapability,
  seedLive,
} from '../../support/live'

const enabled = process.env.SCENEWEAVER_UI_REVIEW_LIVE === '1'
const root = resolve('../..')
const output = resolve(root, 'docs/validation/ui-review-live-comfy/desktop')

test.describe('live Comfy UX review', () => {
  test.setTimeout(LIVE_TIMEOUT_MS * 2)

  test('Story→Generate→Adopt context continuity with real Comfy', async ({ page }, testInfo) => {
    test.skip(!enabled, 'Set SCENEWEAVER_UI_REVIEW_LIVE=1 to capture live Comfy UX artifacts')

    let caps
    try {
      caps = await requireComfyCapability('BaseRender')
      await requireComfyCapability('OutfitTryOn')
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err)
      if (message.startsWith('SKIP_COMFY_UNREACHABLE') || (err as { skip?: boolean })?.skip) {
        test.skip(true, message)
        return
      }
      throw err
    }

    await mkdir(output, { recursive: true })
    await page.setViewportSize({ width: 1280, height: 800 })

    const pageErrors: string[] = []
    page.on('pageerror', (error) => pageErrors.push(error.message))

    const captures: Record<string, unknown>[] = []
    const capture = async (name: string, state: string, element?: ReturnType<Page['locator']>) => {
      await page.evaluate(() => document.fonts.ready)
      await page.evaluate(() => {
        for (const img of document.querySelectorAll('img')) {
          img.loading = 'eager'
        }
      })
      await expect
        .poll(
          () =>
            page.locator('img').evaluateAll((nodes) =>
              nodes.every(
                (n) =>
                  !n.getClientRects().length ||
                  (n.complete && n.naturalWidth > 0) ||
                  (n.complete && n.naturalWidth === 0),
              ),
            ),
          { timeout: 60_000 },
        )
        .toBe(true)
      const path = resolve(output, `${name}.png`)
      if (element) await element.screenshot({ path, animations: 'disabled' })
      else {
        await page.evaluate(() => window.scrollTo(0, 0))
        await page.screenshot({ path, fullPage: true, animations: 'disabled' })
      }
      const horizontalOverflow = await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      )
      expect(horizontalOverflow).toBe(false)
      const context = {
        project: await page.getByTestId('context-project').textContent().catch(() => null),
        beat: await page.getByTestId('context-beat').textContent().catch(() => null),
        shot: await page.getByTestId('context-shot').textContent().catch(() => null),
      }
      captures.push({
        file: `${name}.png`,
        state,
        path: new URL(page.url()).pathname,
        headings: await page.locator('h1,h2').allTextContents(),
        context,
        horizontalOverflow,
      })
    }

    const api = new ApiClient()
    const seeded = await seedLive('m4_visual')
    const project = `/projects/${seeded.project_id}`
    const dialogue = await api.generateDialogue(seeded.beat_id!, seeded.character_id!)
    await api.lockScript(dialogue.candidates[0].id, 'えへへ、まだ帰らなくてもいいですよ？')

    await page.goto('/')
    await expect(page.getByTestId('home-intent-visual-library')).toBeVisible()
    await expect(page.getByTestId('jobs-indicator')).toHaveCount(0)
    await capture('01_home', 'idle header: no jobs indicator')

    await page.goto(
      `${project}/story?sceneId=${seeded.scene_id}&beatId=${seeded.beat_id}`,
    )
    await expect(page.getByTestId('project-context-bar')).toBeVisible()
    await expect(page.getByTestId('context-project')).toBeVisible()
    await expect(page.getByTestId('context-beat')).toBeVisible()
    const projectTitle = (await page.getByTestId('context-project').textContent())!.trim()
    const beatTitle = (await page.getByTestId('context-beat').textContent())!.trim()
    await capture('02_story_context', 'CX-F0 context bar on Story')

    // Wardrobe + Try-On via UI (real Qwen) — outfit feeds later context chips
    await page.goto(`${project}/wardrobe`)
    await expect(page.getByTestId('wardrobe-page')).toBeVisible()
    await expect(page.getByTestId('project-context-bar')).toBeVisible()
    const market = page.getByTestId('wardrobe-market-panel')
    await market.getByLabel('キャラクター').selectOption(seeded.character_id!)
    await market.getByLabel('シーン').selectOption(seeded.scene_id!)
    await market.getByTestId('market-list').getByRole('button', { name: /Cardigan/ }).click()
    await expect(page.getByTestId('outfit-detail')).toBeVisible()
    await capture('03_wardrobe_market', 'outfit selected before try-on')

    await page.getByTestId('tryon-generate').click()
    await page.getByTestId('wardrobe-tab-tryon').click()
    await expect(page.getByTestId('tryon-status-label')).toHaveText(/待機中|処理中|完了/, {
      timeout: 60_000,
    })
    const tryonPhase = await page.getByTestId('tryon-status-label').textContent()
    if (tryonPhase && /待機中|処理中/.test(tryonPhase)) {
      await capture('04_tryon_generating', `try-on ${tryonPhase}; jobs/indicator may show`)
    }
    await expect(page.getByTestId('tryon-candidate-list').locator('img')).toHaveCount(4, {
      timeout: LIVE_TIMEOUT_MS,
    })
    await expect(page.getByTestId('tryon-status-label')).toHaveText('完了')
    await capture('05_tryon_review', 'real Comfy try-on candidates')
    await page.getByTestId('tryon-adopt-0').click()
    await expect(page.getByTestId('tryon-adopted-banner')).toBeVisible()
    await capture('06_tryon_adopted', 'adopted try-on look')

    const shot = await api.planShot(seeded.beat_id!)
    const studio = `${project}/shots/${shot.id}`
    await page.goto(studio)
    await expect(page.getByTestId('prompt-positive')).toBeVisible()
    await expect(page.getByTestId('project-context-bar')).toBeVisible()
    await expect(page.getByTestId('context-project')).toHaveText(projectTitle)
    await expect(page.getByTestId('context-beat')).toHaveText(beatTitle)
    await expect(page.getByTestId('context-shot')).toHaveText(/Shot 0?1/)
    const shotLabel = (await page.getByTestId('context-shot').textContent())!.trim()
    await expect(page.getByTestId('jobs-indicator')).toHaveCount(0)
    await capture('07_shot_studio', 'same Project/Beat/Shot context; idle jobs')

    await page.getByTestId('shot-generate').click()
    const jobsVisible = await page
      .getByTestId('jobs-indicator')
      .waitFor({ state: 'visible', timeout: 8_000 })
      .then(() => true)
      .catch(() => false)
    if (jobsVisible) {
      await capture('08_generating_jobs', 'JobsIndicator while real Comfy render runs')
    } else {
      const statusVisible = await page
        .getByTestId('shot-status-label')
        .isVisible()
        .catch(() => false)
      if (statusVisible) {
        const shotPhase = await page.getByTestId('shot-status-label').textContent()
        if (shotPhase === '処理中') {
          await capture('08_generating_jobs', 'render in progress (jobs indicator raced past)')
        }
      }
    }

    await expect(page.getByTestId('generation-review')).toBeVisible({ timeout: LIVE_TIMEOUT_MS })
    await expect(page.getByTestId('generation-candidate-list').locator('img')).toHaveCount(4, {
      timeout: LIVE_TIMEOUT_MS,
    })
    await expect(page.getByTestId('context-project')).toHaveText(projectTitle)
    await expect(page.getByTestId('context-beat')).toHaveText(beatTitle)
    await expect(page.getByTestId('context-shot')).toHaveText(shotLabel)
    await capture('09_generation_review', 'Review keeps Story→Shot context; real Comfy pixels')

    await page.getByTestId('generation-adopt').click()
    await expect(page.getByTestId('generation-adopted-banner')).toBeVisible()
    await capture('10_adopted_candidate', 'adopted real generation asset')

    await page.getByTestId('review-next-csp-action').click()
    await expect(page).toHaveURL(new RegExp(`${project}/csp`))
    await expect(page.getByTestId('project-context-bar')).toBeVisible()
    await expect(page.getByTestId('context-project')).toHaveText(projectTitle)
    await expect(page.getByTestId('context-beat')).toHaveText(beatTitle)
    await expect(page.getByTestId('context-shot')).toHaveText(shotLabel)
    await expect(page.getByTestId('csp-page-plan').locator('img')).toHaveCount(1)
    await page.getByTestId('csp-build-handoff').click()
    await expect(page.getByTestId('csp-revision')).toHaveText('r001')
    await capture('11_csp', 'CSP with continuous context from Story')

    await page.goto(`${project}/release`)
    await expect(page.getByTestId('project-context-bar')).toBeVisible()
    await page.getByTestId('release-title').fill('リゼ・ヘルエスタ：CX-F0 ライブ確認')
    await page.getByTestId('release-summary').fill('Context Bar連続遷移の実Comfyレビューです。')
    await page.getByTestId('release-preview-button').click()
    await page.getByTestId('release-tab-patreon').click()
    await expect(page.getByTestId('release-edition-patreon')).toBeVisible()
    await capture('12_release', 'release after continuous Story→Adopt path')

    expect(pageErrors).toEqual([])
    const manifest = {
      viewport: { name: 'desktop', width: 1280, height: 800 },
      focus: 'CX-F0 Story→Generate→Adopt context continuity',
      appCodeCommit: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim(),
      captureSpecSha256: createHash('sha256')
        .update(await readFile(resolve(root, 'tests/e2e/specs/live/ui-review-comfy.live.spec.ts')))
        .digest('hex'),
      environment: 'live-test; real ComfyUI; stub LLM; NO asset content substitution',
      imageBackend: 'comfy',
      contextChecked: { projectTitle, beatTitle, shotLabel },
      capabilities: {
        BaseRender: caps.BaseRender,
        OutfitTryOn: caps.OutfitTryOn,
      },
      captures,
      pageErrors,
    }
    await writeFile(resolve(output, 'manifest.json'), JSON.stringify(manifest, null, 2))
    await testInfo.attach('live Comfy UX manifest', {
      body: JSON.stringify(manifest, null, 2),
      contentType: 'application/json',
    })
  })
})
