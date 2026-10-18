/**
 * Real-Comfy UX review: full creator flow with NO asset-content substitution.
 * Opt-in: SCENEWEAVER_UI_REVIEW_LIVE=1
 *
 * Captures real try-on / generation pixels so Human Review can judge user experience.
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

  test('full creator flow screenshots with real Comfy outputs', async ({ page }, testInfo) => {
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
      captures.push({
        file: `${name}.png`,
        state,
        path: new URL(page.url()).pathname,
        headings: await page.locator('h1,h2').allTextContents(),
        horizontalOverflow,
      })
    }

    const api = new ApiClient()
    const seeded = await seedLive('m4_visual')
    const project = `/projects/${seeded.project_id}`
    const dialogue = await api.generateDialogue(seeded.beat_id!, seeded.character_id!)
    await api.lockScript(dialogue.candidates[0].id, 'このお店の「普通」、強いですね。')

    await page.goto('/')
    await expect(page.getByTestId('home-intent-visual-library')).toBeVisible()
    await capture('01_home', 'live stack; real Comfy backend')

    await page.goto('/visual-library')
    await expect(page.getByTestId('visual-library-grid')).toBeVisible()
    await page.getByTestId('visual-library-filter-pose').click()
    await capture('02_visual_library_pose', 'CE-2 catalog on live stack')

    await page.goto(project)
    await expect(page.getByTestId('project-workflow')).toBeVisible()
    await capture('03_project_dashboard', 'workflow guidance')

    // Wardrobe + Try-On via UI (real Qwen)
    await page.goto(`${project}/wardrobe`)
    await expect(page.getByTestId('wardrobe-page')).toBeVisible()
    const market = page.getByTestId('wardrobe-market-panel')
    await market.getByLabel('キャラクター').selectOption(seeded.character_id!)
    await market.getByLabel('シーン').selectOption(seeded.scene_id!)
    await market.getByTestId('market-list').getByRole('button', { name: /Cardigan/ }).click()
    await expect(page.getByTestId('outfit-detail')).toBeVisible()
    await capture('04_wardrobe_market', 'outfit selected before try-on')

    await page.getByTestId('tryon-generate').click()
    // Status lives on the try-on tab; market tab stays mounted until success.
    await page.getByTestId('wardrobe-tab-tryon').click()
    await expect(page.getByTestId('tryon-status-label')).toHaveText(/待機中|処理中|完了/, {
      timeout: 60_000,
    })
    const tryonPhase = await page.getByTestId('tryon-status-label').textContent()
    if (tryonPhase && /待機中|処理中/.test(tryonPhase)) {
      await capture('05_tryon_generating', `try-on ${tryonPhase}; real Comfy OutfitTryOn`)
    }
    await expect(page.getByTestId('tryon-candidate-list').locator('img')).toHaveCount(4, {
      timeout: LIVE_TIMEOUT_MS,
    })
    await expect(page.getByTestId('tryon-status-label')).toHaveText('完了')
    await capture('06_tryon_review', 'real Comfy try-on candidates (no image substitution)')
    await page.getByTestId('tryon-adopt-0').click()
    await expect(page.getByTestId('tryon-adopted-banner')).toBeVisible()
    await capture('07_tryon_adopted', 'adopted try-on look')

    // Shot plan + generate via UI (real Anima)
    const shot = await api.planShot(seeded.beat_id!)
    const studio = `${project}/shots/${shot.id}`
    await page.goto(studio)
    await expect(page.getByTestId('prompt-positive')).toBeVisible()
    await capture('08_shot_studio', 'shot ready; real backend')

    await page.getByTestId('shot-generate').click()
    // Processing status sits on Shot Studio; success navigates into Generation Review.
    const statusVisible = await page
      .getByTestId('shot-status-label')
      .isVisible()
      .catch(() => false)
    if (statusVisible) {
      await expect(page.getByTestId('shot-status-label')).toHaveText(/処理中|完了|失敗/, {
        timeout: 60_000,
      })
      const shotPhase = await page.getByTestId('shot-status-label').textContent()
      if (shotPhase === '処理中') {
        await capture('09_generating', 'real Comfy BaseRender in progress')
      }
    }
    await expect(page.getByTestId('generation-review')).toBeVisible({ timeout: LIVE_TIMEOUT_MS })
    await expect(page.getByTestId('generation-candidate-list').locator('img')).toHaveCount(4, {
      timeout: LIVE_TIMEOUT_MS,
    })
    await capture('10_generation_review', 'real Comfy generation candidates (no substitution)')

    await page.getByTestId('generation-adopt').click()
    await expect(page.getByTestId('generation-adopted-banner')).toBeVisible()
    await capture('11_adopted_candidate', 'adopted real generation asset')

    await page.goto(`${project}/csp`)
    await expect(page.getByTestId('csp-page-plan').locator('img')).toHaveCount(1)
    await page.getByTestId('csp-build-handoff').click()
    await expect(page.getByTestId('csp-revision')).toHaveText('r001')
    await capture('12_csp', 'CSP handoff with real adopted panel bytes')

    await page.goto(`${project}/release`)
    await page.getByTestId('release-title').fill('リゼ・ヘルエスタ：ライブComfy確認')
    await page.getByTestId('release-summary').fill('実Comfy生成のプレビューです。')
    await page.getByTestId('release-preview-button').click()
    await page.getByTestId('release-tab-patreon').click()
    await expect(page.getByTestId('release-edition-patreon')).toBeVisible()
    await capture('13_release', 'release preview after live generation')

    expect(pageErrors).toEqual([])
    const manifest = {
      viewport: { name: 'desktop', width: 1280, height: 800 },
      appCodeCommit: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim(),
      captureSpecSha256: createHash('sha256')
        .update(await readFile(resolve(root, 'tests/e2e/specs/live/ui-review-comfy.live.spec.ts')))
        .digest('hex'),
      environment: 'live-test; real ComfyUI; stub LLM; NO asset content substitution',
      imageBackend: 'comfy',
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
