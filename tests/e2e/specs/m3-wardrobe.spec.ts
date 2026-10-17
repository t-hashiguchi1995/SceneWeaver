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
    await expect(page.getByRole('heading', { name: '衣装' })).toBeVisible()
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

  test('My Wardrobe lists every adopted look without reload', async ({
    seedScenario,
    applySeedContext,
    tryon,
    page,
  }) => {
    const seeded = await seedScenario('m3_tryon')
    await applySeedContext(seeded)

    await page.goto(`/projects/${seeded.project_id}/wardrobe`)
    await expect(page.getByTestId('wardrobe-page')).toBeVisible()
    const market = page.getByTestId('wardrobe-market-panel')
    await market.getByLabel('キャラクター').selectOption(seeded.character_id!)
    await market.getByLabel('シーン').selectOption(seeded.scene_id!)
    await market.getByTestId('market-list').getByRole('button', { name: /Cardigan/ }).click()
    await expect(page.getByTestId('outfit-detail')).toBeVisible()

    await tryon.generate()
    await expect(tryon.statusLabel()).toHaveText('完了', { timeout: 30_000 })
    await tryon.adoptCandidate(0)
    await expect(page.getByTestId('wardrobe-adopted-list').locator('li')).toHaveCount(1)

    await page.getByTestId('wardrobe-tab-market').click()
    await tryon.generate()
    await expect(tryon.statusLabel()).toHaveText('完了', { timeout: 30_000 })
    await tryon.adoptCandidate(1)
    await expect(page.getByTestId('tryon-adopted-banner')).toContainText('2着')
    await expect(page.getByTestId('wardrobe-adopted-list').locator('li')).toHaveCount(2)
    await expect(page.getByTestId('wardrobe-adopted-0')).toBeVisible()
    await expect(page.getByTestId('wardrobe-adopted-1')).toBeVisible()
  })
})
