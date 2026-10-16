import { test, expect } from '../fixtures/sceneweaver.fixture'
import { expectPanelMatchesAdopted, expectJsonFile } from '../support/assertions'

/**
 * MVP complete criterion — browser vertical slice.
 * Seed provides Character + Market fixtures; user actions run through UI.
 */
test('SceneWeaver MVP vertical slice (browser)', async ({
  page,
  home,
  projects,
  story,
  wardrobe,
  tryon,
  shots,
  csp,
  release,
  seedScenario,
  applySeedContext,
  api,
}) => {
  const seeded = await seedScenario('vertical_slice')
  await applySeedContext(seeded)

  await home.goto()
  await expect(page.getByRole('heading', { name: '制作を続けましょう' })).toBeVisible()

  await home.openProjects()
  await projects.create('Vertical Slice Project')
  await expect(projects.projectLink('Vertical Slice Project')).toBeVisible()

  // Point Studio context at the UI-created project while keeping character/market fixtures
  await page.evaluate(() => {
    const raw = sessionStorage.getItem('sceneweaver.studio')
    const ctx = raw ? JSON.parse(raw) : {}
    // keep character/market from seed; switch project after create via UI selection
    sessionStorage.setItem('sceneweaver.studio', JSON.stringify(ctx))
  })

  await home.openStory()
  await story.selectProject('Vertical Slice Project')
  await story.selectCharacter('リゼヘル')
  await story.createScene('Cafe')
  await story.createBeat('もう少し一緒にいたい')
  await story.generateDialogue()
  await expect(story.candidate(0)).toBeVisible()
  await expect(story.candidate(1)).toBeVisible()
  await expect(story.candidate(2)).toBeVisible()
  await story.lockCandidate(0)
  await expect(page.getByTestId('story-locked-banner')).toBeVisible()

  await home.openWardrobe()
  await wardrobe.openOutfit('Cardigan')
  await tryon.generate()
  await expect(tryon.statusLabel()).toHaveText('完了', { timeout: 40_000 })
  await expect(tryon.candidate(0)).toBeVisible()
  await expect(tryon.candidate(3)).toBeVisible()
  await tryon.adoptCandidate(2)
  await expect(page.getByTestId('tryon-adopted-banner')).toContainText('コーディネート')

  const studio = await page.evaluate(() =>
    JSON.parse(sessionStorage.getItem('sceneweaver.studio') ?? '{}'),
  )
  expect(studio.beatId).toBeTruthy()

  await home.openShots()
  await shots.setBeatId(studio.beatId)
  await shots.planShot()
  await expect(page.getByTestId('prompt-editor')).toBeVisible()
  await shots.enablePose(true)
  await shots.generate()
  await expect(page.getByTestId('generation-review')).toBeVisible()
  await expect(page.getByTestId('generation-candidate-0')).toBeVisible()
  await expect(page.getByTestId('generation-candidate-3')).toBeVisible()
  await page.getByTestId('generation-select-1').click()
  await page.getByTestId('generation-adopt').click()
  await expect(page.getByTestId('generation-adopted-banner')).toBeVisible()

  await home.openCsp()
  await csp.buildHandoff()
  await expect(csp.revision()).toHaveText('r001')

  await home.openRelease()
  await release.buildPreview()
  await release.openPlatform('x')
  await expect(release.edition('x')).toBeVisible()
  await release.openPlatform('pixiv')
  await expect(release.edition('pixiv')).toBeVisible()
  await release.openPlatform('patreon')
  await expect(release.edition('patreon')).toBeVisible()

  const after = await page.evaluate(() =>
    JSON.parse(sessionStorage.getItem('sceneweaver.studio') ?? '{}'),
  )
  expect(after.adoptedRenderSha256).toBeTruthy()
  expect(after.handoffPath).toBeTruthy()

  await expectPanelMatchesAdopted(after.handoffPath, after.adoptedRenderSha256)
  await expectJsonFile(after.handoffPath + '/project_manifest.json', (data) => {
    const panel = (data.pages as any)[0].panels[0]
    return (
      panel.asset_id === after.adoptedRenderAssetId &&
      panel.sha256 === after.adoptedRenderSha256 &&
      panel.shot_id === after.shotId &&
      Array.isArray(panel.script_event_ids)
    )
  })

  let state = await api.state()
  expect(state.shot_count).toBeGreaterThanOrEqual(1)
  expect(state.generation_attempt_count).toBeGreaterThanOrEqual(1)
  expect(state.adopted_asset_count).toBeGreaterThanOrEqual(1)
  expect(state.handoff_count).toBeGreaterThanOrEqual(1)

  // Soft process restart: drop container/engine, keep DB — state must survive
  await api.reload()
  state = await api.state()
  expect(state.shot_count).toBeGreaterThanOrEqual(1)
  expect(state.generation_attempt_count).toBeGreaterThanOrEqual(1)
  expect(state.adopted_asset_count).toBeGreaterThanOrEqual(1)
  expect(state.handoff_count).toBeGreaterThanOrEqual(1)
})
