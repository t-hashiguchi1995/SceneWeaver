import { test, expect } from '../fixtures/sceneweaver.fixture'

test.describe('M3 Wardrobe', () => {
  test('Market → Outfit → Try-On Queued/Running/Succeeded → 4 candidates → Adopt', async ({
    seedScenario,
    applySeedContext,
    wardrobe,
    tryon,
    page,
  }) => {
    const seeded = await seedScenario('m3_tryon')
    await applySeedContext(seeded)

    await wardrobe.goto()
    await expect(page.getByRole('heading', { name: '衣装マーケット' })).toBeVisible()
    await wardrobe.openOutfit('Cardigan')
    await expect(page.getByTestId('outfit-detail')).toBeVisible()

    await tryon.generate()
    await expect(tryon.statusLabel()).toHaveText(/待機中|処理中|完了/, { timeout: 20_000 })
    await expect(tryon.statusLabel()).toHaveText('完了', { timeout: 30_000 })
    await expect(tryon.candidate(0)).toBeVisible()
    await expect(tryon.candidate(3)).toBeVisible()
    await tryon.adoptCandidate(3)
    await expect(page.getByTestId('tryon-adopted-banner')).toContainText('コーディネート')
  })
})
