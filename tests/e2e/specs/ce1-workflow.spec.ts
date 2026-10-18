import { test, expect } from '../fixtures/sceneweaver.fixture'

test.describe('CE-1 Workflow Guidance', () => {
  test('Home shows three intent entries', async ({ page, seedScenario, applySeedContext }) => {
    const seeded = await seedScenario('m2_story')
    await applySeedContext(seeded)
    await page.goto('/')
    await expect(page.getByTestId('home-intent-cards')).toBeVisible()
    await expect(page.getByTestId('home-intent-continue')).toBeVisible()
    await expect(page.getByTestId('home-intent-quick-test')).toBeVisible()
    await expect(page.getByTestId('home-intent-visual-library')).toBeVisible()
    await expect(page.getByTestId('nav-quick-test')).toBeVisible()
    await expect(page.getByTestId('nav-visual-library')).toBeVisible()
  })

  test('Home create card appears when there are no projects', async ({ page, api }) => {
    await api.reset()
    await page.goto('/')
    await expect(page.getByTestId('home-intent-create')).toBeVisible()
    await expect(page.getByTestId('home-intent-quick-test')).toBeVisible()
    await expect(page.getByTestId('home-intent-visual-library')).toBeVisible()
  })

  test('Dashboard workflow and completion cards guide the next stage', async ({
    page,
    api,
    seedScenario,
    applySeedContext,
    story,
    wardrobe,
    tryon,
  }) => {
    const seeded = await seedScenario('m3_tryon')
    await applySeedContext(seeded)
    const projectPath = `/projects/${seeded.project_id}`

    await page.goto(projectPath)
    await expect(page.getByTestId('project-workflow')).toBeVisible()
    await expect(page.getByTestId('workflow-stage-story')).toBeVisible()
    await expect(page.getByTestId('workflow-stage-shots')).toBeVisible()
    await expect(page.getByTestId('workflow-stage-csp')).toBeVisible()
    await expect(page.getByTestId('workflow-stage-release')).toBeVisible()
    await expect(page.getByTestId('project-primary-next')).toContainText(/セリフ|dialogue|Lock/i)

    await page.goto(`${projectPath}/story`)
    await story.generateDialogue()
    await page.getByTestId('dialogue-lock-0').click()
    await expect(page.getByTestId('story-locked-banner')).toBeVisible()
    await expect(page.getByTestId('story-next-wardrobe')).toBeVisible()
    await page.getByTestId('story-next-wardrobe-action').click()
    await expect(page).toHaveURL(new RegExp(`${projectPath}/wardrobe`))

    const market = page.getByTestId('wardrobe-market-panel')
    await market.getByLabel('キャラクター').selectOption(seeded.character_id!)
    await market.getByLabel('シーン').selectOption(seeded.scene_id!)
    await wardrobe.openOutfit('Cardigan')
    await tryon.generate()
    await expect(tryon.statusLabel()).toHaveText('完了', { timeout: 30_000 })
    await tryon.adoptCandidate(0)
    await expect(page.getByTestId('wardrobe-next-shots')).toBeVisible()
    await page.getByTestId('wardrobe-next-shots-action').click()
    await expect(page).toHaveURL(new RegExp(`${projectPath}/shots`))

    const shot = await api.planShot(seeded.beat_id!)
    const rendered = await api.renderShot(shot.id, false)
    await page.goto(
      `${projectPath}/shots/${shot.id}/generations/${rendered.generation_attempt_id}`,
    )
    await page.getByTestId('generation-adopt').click()
    await expect(page.getByTestId('review-next-csp')).toBeVisible()
    await page.getByTestId('review-next-csp-action').click()
    await expect(page).toHaveURL(new RegExp(`${projectPath}/csp`))

    await page.getByTestId('csp-build-handoff').click()
    await expect(page.getByTestId('csp-revision')).toHaveText('r001')
    await expect(page.getByTestId('csp-next-release')).toBeVisible()
    await page.getByTestId('csp-next-release-action').click()
    await expect(page).toHaveURL(new RegExp(`${projectPath}/release`))

    await page.goto(`${projectPath}/shots/${shot.id}`)
    await expect(page.getByTestId('shot-basic-settings')).toBeVisible()
    await expect(page.getByTestId('workflow-completion-card')).toHaveCount(0)
    await expect(page.getByTestId('story-next-wardrobe')).toHaveCount(0)
    await expect(page.getByTestId('wardrobe-next-shots')).toHaveCount(0)
    await expect(page.getByTestId('review-next-csp')).toHaveCount(0)
    await expect(page.getByText('次へ：生成する')).toHaveCount(0)
  })

  test('Dashboard configure_shot primary CTA carries beatId into Shots', async ({
    page,
    api,
    seedScenario,
    applySeedContext,
  }) => {
    const seeded = await seedScenario('m3_tryon')
    await applySeedContext(seeded)
    const dialogue = await api.generateDialogue(seeded.beat_id!, seeded.character_id!)
    await api.lockScript(dialogue.candidates[0].id, 'もう少し一緒にいたい')

    const projectPath = `/projects/${seeded.project_id}`
    await page.goto(projectPath)
    await expect(page.getByTestId('project-primary-next')).toContainText(/ショットを設定|Configure a shot/i)
    await expect(page.getByTestId('project-next-actions')).toHaveCount(0)
    await page.getByTestId('project-primary-next-action').click()
    await expect(page).toHaveURL(new RegExp(`${projectPath}/shots\\?beatId=${seeded.beat_id}`))
    await expect(page.getByTestId('shots-entry-page')).toBeVisible()
    await expect(page.getByTestId('shot-beat-id')).toHaveValue(seeded.beat_id!)
  })

  test('Quick Test stub keeps escape hatch; Visual Library is real list', async ({ page }) => {
    await page.goto('/quick-test')
    await expect(page.getByTestId('quick-test-page')).toBeVisible()
    await expect(page.getByTestId('quick-test-fallback')).toBeVisible()
    await page.goto('/visual-library')
    await expect(page.getByTestId('visual-library-page')).toBeVisible()
    await expect(page.getByTestId('visual-library-title')).toBeVisible()
    await expect(page.getByTestId('visual-library-fallback')).toHaveCount(0)
  })
})
