import { test, expect } from '../fixtures/sceneweaver.fixture'

test.describe('M4 Visual', () => {
  test('Locked Beat → ShotSpec → Render → 4 candidates → Adopt', async ({
    seedScenario,
    applySeedContext,
    api,
    shots,
    page,
  }) => {
    const seeded = await seedScenario('m4_visual')
    const dialogue = await api.generateDialogue(seeded.beat_id!, seeded.character_id!)
    await api.lockScript(dialogue.candidates[0].id)
    await applySeedContext(seeded)

    await shots.goto()
    await shots.setBeatId(seeded.beat_id!)
    await shots.planShot()
    await expect(page.getByTestId('shot-id')).toBeVisible()
    await shots.enablePose(true)
    await shots.generate()
    await expect(shots.statusLabel()).toHaveText(/Queued|Running|Succeeded/, { timeout: 20_000 })
    await expect(shots.statusLabel()).toHaveText('Succeeded', { timeout: 40_000 })
    await expect(shots.candidate(0)).toBeVisible()
    await expect(shots.candidate(3)).toBeVisible()
    await shots.adoptCandidate(1)
    await expect(page.getByTestId('generation-adopted-banner')).toBeVisible()
  })
})
