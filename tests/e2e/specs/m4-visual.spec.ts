import { test, expect } from '../fixtures/sceneweaver.fixture'

test.describe('M4 Visual', () => {
  test('Locked Beat → ShotSpec → Prompt edit → Render → Attempt snapshot immutable', async ({
    seedScenario,
    applySeedContext,
    api,
    shots,
    review,
    page,
  }) => {
    const seeded = await seedScenario('m4_visual')
    const dialogue = await api.generateDialogue(seeded.beat_id!, seeded.character_id!)
    await api.lockScript(dialogue.candidates[0].id)
    await applySeedContext(seeded)

    await shots.goto()
    await shots.setBeatId(seeded.beat_id!)
    await shots.planShot()
    await page.locator('.technical-details summary').click()
    await expect(page.getByTestId('shot-id')).toBeVisible()
    await expect(page.getByTestId('prompt-editor')).toBeVisible()

    const before = await shots.positive().inputValue()
    await shots.appendPositive('bar_marker_e2e')
    await shots.enablePose(true)
    await shots.generate()
    await expect(review.candidate(0)).toBeVisible()
    await expect(review.candidate(3)).toBeVisible()
    await expect(review.finalPositive()).toContainText('bar_marker_e2e')

    const state = await api.state()
    const attempt = state.generation_attempts?.[0]
    expect(attempt?.payload?.final_positive_prompt || '').toContain('bar_marker_e2e')
    const snap = String(attempt?.payload?.final_positive_prompt || '')

    await review.openShotStudio()
    await expect(page.getByTestId('prompt-editor')).toBeVisible({ timeout: 20_000 })
    await shots.appendPositive('later_should_not_mutate_attempt')
    const state2 = await api.state()
    expect(state2.generation_attempts?.[0]?.payload?.final_positive_prompt).toBe(snap)
    expect(state2.generation_attempts?.[0]?.payload?.final_positive_prompt || '').not.toContain(
      'later_should_not_mutate_attempt',
    )

    await shots.resetEdits()
    await expect(shots.positive()).toHaveValue(before)

    await shots.openReview()
    await review.adoptCandidate(1)
    await expect(review.adoptedBanner()).toBeVisible()
  })
})
