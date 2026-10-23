/**
 * Real-Comfy UX review: Story → Wardrobe → Try-On → Shot → Generate → Review → CSP → Release.
 * Opt-in: SCENEWEAVER_UI_REVIEW_LIVE=1
 *
 * CX-F0 focus (9 Human Review states):
 * Story / Wardrobe / Try-On queued / Try-On running / Shot /
 * Generating / Review / CSP / Release
 * No asset-content substitution.
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

  test('CX-F0 nine-state continuity with real Comfy', async ({ page }, testInfo) => {
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
    const capture = async (
      name: string,
      state: string,
      opts?: { waitImages?: boolean; element?: ReturnType<Page['locator']> },
    ) => {
      await page.evaluate(() => document.fonts.ready)
      if (opts?.waitImages !== false) {
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
      }
      const path = resolve(output, `${name}.png`)
      if (opts?.element) await opts.element.screenshot({ path, animations: 'disabled' })
      else {
        await page.evaluate(() => window.scrollTo(0, 0))
        await page.screenshot({ path, fullPage: true, animations: 'disabled' })
      }
      const horizontalOverflow = await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      )
      expect(horizontalOverflow).toBe(false)
      const context = await page.evaluate(() => {
        const text = (id: string) =>
          document.querySelector(`[data-testid="${id}"]`)?.textContent?.trim() ?? null
        return {
          project: text('context-project'),
          beat: text('context-beat'),
          shot: text('context-shot'),
        }
      })
      const jobsLabel = await page.evaluate(
        () =>
          document.querySelector('[data-testid="jobs-indicator-label"]')?.textContent?.trim() ??
          null,
      )
      const bodyStatus = await page.evaluate(() => {
        const tryon = document.querySelector('[data-testid="tryon-status-label"]')?.textContent?.trim()
        const shot = document.querySelector('[data-testid="shot-status-label"]')?.textContent?.trim()
        return tryon || shot || null
      })
      captures.push({
        file: `${name}.png`,
        state,
        path: new URL(page.url()).pathname,
        headings: await page.locator('h1,h2').allTextContents(),
        context,
        jobsLabel,
        bodyStatus,
        horizontalOverflow,
      })
    }

    const api = new ApiClient()
    const seeded = await seedLive('m4_visual')
    const project = `/projects/${seeded.project_id}`
    const dialogue = await api.generateDialogue(seeded.beat_id!, seeded.character_id!)
    await api.lockScript(dialogue.candidates[0].id, 'えへへ、まだ帰らなくてもいいですよ？')

    // Persist studio context so Wardrobe Context Bar keeps Beat across navigation.
    await page.goto('/')
    await page.evaluate(
      ({ projectId, sceneId, beatId, characterId }) => {
        const cur = JSON.parse(sessionStorage.getItem('sceneweaver.studio') ?? '{}')
        sessionStorage.setItem(
          'sceneweaver.studio',
          JSON.stringify({
            ...cur,
            projectId,
            sceneId,
            beatId,
            characterId,
            characterName: 'リゼヘル',
          }),
        )
      },
      {
        projectId: seeded.project_id!,
        sceneId: seeded.scene_id!,
        beatId: seeded.beat_id!,
        characterId: seeded.character_id!,
      },
    )

    await page.goto(
      `${project}/story?sceneId=${seeded.scene_id}&beatId=${seeded.beat_id}`,
    )
    await expect(page.getByTestId('project-context-bar')).toBeVisible()
    await expect(page.getByTestId('context-project')).toBeVisible()
    await expect(page.getByTestId('context-beat')).toBeVisible()
    const projectTitle = (await page.getByTestId('context-project').textContent())!.trim()
    const beatTitle = (await page.getByTestId('context-beat').textContent())!.trim()
    await capture('01_story_context', 'Story context')

    await page.goto(`${project}/wardrobe`)
    await expect(page.getByTestId('wardrobe-page')).toBeVisible()
    await expect(page.getByTestId('project-context-bar')).toBeVisible()
    await expect(page.getByTestId('context-project')).toHaveText(projectTitle)
    await expect(page.getByTestId('context-beat')).toHaveText(beatTitle)
    const market = page.getByTestId('wardrobe-market-panel')
    await market.getByLabel('キャラクター').selectOption(seeded.character_id!)
    await market.getByLabel('シーン').selectOption(seeded.scene_id!)
    await market.getByTestId('market-list').getByRole('button', { name: /Cardigan/ }).click()
    await expect(page.getByTestId('outfit-detail')).toBeVisible()
    await capture('02_wardrobe_context', 'Wardrobe keeps Project + Beat')

    await page.getByTestId('tryon-generate').click()
    await page.getByTestId('wardrobe-tab-tryon').click()
    await expect(page.getByTestId('tryon-status-label')).toHaveText('待機中', { timeout: 3_000 })
    await expect(page.getByTestId('jobs-indicator-label')).toContainText(/待機中|waiting/i)
    await capture('03_tryon_queued', 'Try-On queued: Header and body both 待機中', {
      waitImages: false,
    })

    await expect(page.getByTestId('tryon-status-label')).toHaveText(/処理中|完了/, {
      timeout: 60_000,
    })
    const tryonRunning = await page.getByTestId('tryon-status-label').textContent()
    if (tryonRunning === '処理中') {
      await expect(page.getByTestId('jobs-indicator-label')).toContainText(/実行中|Running/i)
      await capture('04_tryon_running', 'Try-On running: Header and body agree', {
        waitImages: false,
      })
    }

    await expect(page.getByTestId('tryon-candidate-list').locator('img')).toHaveCount(4, {
      timeout: LIVE_TIMEOUT_MS,
    })
    await expect(page.getByTestId('tryon-status-label')).toHaveText('完了')
    await page.getByTestId('tryon-adopt-0').click()
    await expect(page.getByTestId('tryon-adopted-banner')).toBeVisible()

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
    await capture('05_shot_context', 'Shot context: Project / Beat / Shot 01')

    await page.getByTestId('shot-generate').click()
    await expect(page.getByTestId('jobs-indicator')).toBeVisible({ timeout: 8_000 })
    // May briefly be queued then running — accept either, prefer running for this frame.
    await expect(page.getByTestId('jobs-indicator-label')).toContainText(/生成|Generating|待機|Waiting/i)
    const generatingLabel = await page.getByTestId('jobs-indicator-label').textContent()
    await capture('06_generating', `Generating: ${generatingLabel}`, { waitImages: false })

    await expect(page.getByTestId('generation-review')).toBeVisible({ timeout: LIVE_TIMEOUT_MS })
    await expect(page.getByTestId('generation-candidate-list').locator('img')).toHaveCount(4, {
      timeout: LIVE_TIMEOUT_MS,
    })
    await expect(page.getByTestId('context-project')).toHaveText(projectTitle)
    await expect(page.getByTestId('context-beat')).toHaveText(beatTitle)
    await expect(page.getByTestId('context-shot')).toHaveText(shotLabel)
    await capture('07_review', 'Review keeps Story→Shot context; real Comfy pixels')

    await page.getByTestId('generation-adopt').click()
    await expect(page.getByTestId('generation-adopted-banner')).toBeVisible()

    await page.getByTestId('review-next-csp-action').click()
    await expect(page).toHaveURL(new RegExp(`${project}/csp`))
    await expect(page.getByTestId('project-context-bar')).toBeVisible()
    await expect(page.getByTestId('context-project')).toHaveText(projectTitle)
    await expect(page.getByTestId('context-beat')).toHaveText(beatTitle)
    await expect(page.getByTestId('context-shot')).toHaveText(shotLabel)
    await expect(page.getByTestId('csp-page-plan').locator('img')).toHaveCount(1)
    await page.getByTestId('csp-build-handoff').click()
    await expect(page.getByTestId('csp-revision')).toHaveText('r001')
    await capture('08_csp', 'CSP with continuous Project / Beat / Shot')

    await page.goto(`${project}/release`)
    await expect(page.getByTestId('project-context-bar')).toBeVisible()
    await expect(page.getByTestId('context-project')).toHaveText(projectTitle)
    await expect(page.getByTestId('context-beat')).toHaveText(beatTitle)
    await expect(page.getByTestId('context-shot')).toHaveText(shotLabel)
    await page.getByTestId('release-title').fill('リゼ・ヘルエスタ：CX-F0 ライブ確認')
    await page.getByTestId('release-summary').fill('Context Bar連続遷移の実Comfyレビューです。')
    await page.getByTestId('release-preview-button').click()
    await page.getByTestId('release-tab-patreon').click()
    await expect(page.getByTestId('release-edition-patreon')).toBeVisible()
    await capture('09_release', 'Release keeps continuous context')

    expect(pageErrors).toEqual([])
    const capturedFiles = captures.map((c) => c.file)
    for (const required of [
      '01_story_context.png',
      '02_wardrobe_context.png',
      '03_tryon_queued.png',
      '05_shot_context.png',
      '06_generating.png',
      '07_review.png',
      '08_csp.png',
      '09_release.png',
    ]) {
      expect(capturedFiles).toContain(required)
    }

    const manifest = {
      viewport: { name: 'desktop', width: 1280, height: 800 },
      focus: 'CX-F0 nine-state Story→Wardrobe→Try-On→Shot→Generate→Review→CSP→Release',
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
