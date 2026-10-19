import { test, expect } from '../fixtures/sceneweaver.fixture'

test.describe('CX-F0 Context / Job / Error UX', () => {
  test('context bar stays stable Story → Shot → Generate → Review → CSP', async ({
    page,
    api,
    seedScenario,
    applySeedContext,
    shots,
    review,
  }) => {
    const seeded = await seedScenario('m3_tryon')
    await applySeedContext(seeded)
    const dialogue = await api.generateDialogue(seeded.beat_id!, seeded.character_id!)
    await api.lockScript(dialogue.candidates[0].id, 'えへへ、まだ帰らなくてもいいですよ？')
    const projectPath = `/projects/${seeded.project_id}`

    await page.goto(`${projectPath}/story?sceneId=${seeded.scene_id}&beatId=${seeded.beat_id}`)
    await expect(page.getByTestId('project-context-bar')).toBeVisible()
    await expect(page.getByTestId('context-project')).toBeVisible()
    const projectTitle = (await page.getByTestId('context-project').textContent())!.trim()
    const beatTitle = (await page.getByTestId('context-beat').textContent())!.trim()
    expect(projectTitle.length).toBeGreaterThan(0)
    expect(beatTitle.length).toBeGreaterThan(0)

    const shot = await api.planShot(seeded.beat_id!)
    await applySeedContext(seeded, { shotId: shot.id, beatId: seeded.beat_id! })

    await page.goto(`${projectPath}/shots/${shot.id}`)
    await expect(page.getByTestId('project-context-bar')).toBeVisible()
    await expect(page.getByTestId('context-project')).toHaveText(projectTitle)
    await expect(page.getByTestId('context-beat')).toHaveText(beatTitle)
    await expect(page.getByTestId('context-shot')).toHaveText(/Shot 0?1/)
    const shotLabel = (await page.getByTestId('context-shot').textContent())!.trim()

    // Idle: no jobs indicator / no "0"
    await expect(page.getByTestId('jobs-indicator')).toHaveCount(0)
    await expect(page.getByText('処理状況')).toHaveCount(0)
    await expect(page.getByText(/処理状況\s*·\s*0/)).toHaveCount(0)

    await page.route('**/api/v1/shots/*/render', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 900))
      await route.continue()
    })

    const generateClick = shots.generate()
    await expect(page.getByTestId('jobs-indicator')).toBeVisible({ timeout: 5_000 })
    await expect(page.getByTestId('jobs-indicator-label')).toContainText(/生成|Generating/i)
    await generateClick

    await expect(page.getByTestId('generation-review')).toBeVisible()
    await expect(page.getByTestId('context-project')).toHaveText(projectTitle)
    await expect(page.getByTestId('context-beat')).toHaveText(beatTitle)
    await expect(page.getByTestId('context-shot')).toHaveText(shotLabel)

    await review.adoptCandidate(0)
    await page.getByTestId('review-next-csp-action').click()
    await expect(page).toHaveURL(new RegExp(`${projectPath}/csp`))
    await expect(page.getByTestId('project-context-bar')).toBeVisible()
    await expect(page.getByTestId('context-project')).toHaveText(projectTitle)
    await expect(page.getByTestId('context-beat')).toHaveText(beatTitle)
    await expect(page.getByTestId('context-shot')).toHaveText(shotLabel)
  })

  test('generation failure shows OperationError near generate with recovery', async ({
    page,
    api,
    seedScenario,
    applySeedContext,
  }) => {
    const seeded = await seedScenario('m3_tryon')
    const shot = await api.planShot(seeded.beat_id!)
    await applySeedContext(seeded, { shotId: shot.id })
    await page.goto(`/projects/${seeded.project_id}/shots/${shot.id}`)
    await expect(page.getByTestId('prompt-editor')).toBeVisible({ timeout: 20_000 })

    await page.route('**/api/v1/shots/*/render', async (route) => {
      await route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'COMFY_UNREACHABLE: Connection refused: 127.0.0.1:8188' }),
      })
    })

    await page.getByTestId('shot-generate').click()
    const error = page.getByTestId('operation-error')
    await expect(error).toBeVisible()
    await expect(page.getByTestId('operation-error-title')).toContainText(/生成できません|Could not generate/i)
    await expect(page.getByTestId('operation-error-retry')).toBeVisible()
    await expect(page.getByTestId('operation-error-integrations')).toBeVisible()
    await page.getByTestId('operation-error-details-toggle').click()
    await expect(page.getByTestId('operation-error-details')).toContainText(/COMFY_UNREACHABLE|8188/)
  })

  test('empty generation history is actionable', async ({ page, api, seedScenario, applySeedContext }) => {
    const seeded = await seedScenario('m3_tryon')
    const shot = await api.planShot(seeded.beat_id!)
    await applySeedContext(seeded, { shotId: shot.id })
    await page.goto(`/projects/${seeded.project_id}/shots/${shot.id}/generations`)
    await expect(page.getByTestId('actionable-empty')).toBeVisible()
    await expect(page.getByTestId('generation-history-empty-action')).toBeVisible()
    await expect(page.getByText('履歴はまだありません')).toHaveCount(0)
  })
})
