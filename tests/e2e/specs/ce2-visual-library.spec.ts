import { test, expect } from '../fixtures/sceneweaver.fixture'

test.describe('CE-2 Visual Library', () => {
  test.beforeEach(async ({ seedScenario }) => {
    await seedScenario('visual_library')
  })

  test('lists real cards with filters, search, detail, and hidden prompt', async ({ page }) => {
    await page.goto('/visual-library')
    await expect(page.getByTestId('visual-library-page')).toBeVisible()
    await expect(page.getByTestId('visual-library-title')).toBeVisible()
    await expect(page.getByTestId('visual-library-fallback')).toHaveCount(0)
    await expect(page.getByTestId('visual-library-grid')).toBeVisible()

    const cards = page.getByTestId('visual-library-card')
    await expect(cards.first()).toBeVisible()
    const cardCount = await cards.count()
    expect(cardCount).toBeGreaterThanOrEqual(10)

    // Prompt strings must not flood the list view.
    const listText = await page.getByTestId('visual-library-grid').innerText()
    expect(listText).not.toMatch(/looking back, over shoulder/)
    expect(listText).not.toMatch(/soft indoor lighting/)
    expect(await page.getByTestId('visual-library-prompt').count()).toBe(0)

    await expect(page.getByTestId('visual-library-no-preview').first()).toBeVisible()
    await expect(page.locator('[data-testid="visual-library-card"][data-has-preview="true"] img').first()).toBeVisible()

    await page.getByTestId('visual-library-filter-pose').click()
    await expect(page.getByTestId('visual-library-card')).toHaveCount(3)

    await page.getByTestId('visual-library-search').fill('振り向き')
    await expect(page.getByTestId('visual-library-card')).toHaveCount(1)
    await page.getByTestId('visual-library-card').click()

    await expect(page.getByTestId('visual-library-detail')).toBeVisible()
    await expect(page.getByTestId('visual-library-detail-title')).toContainText('振り向き')
    await expect(page.getByTestId('visual-library-overview')).toBeVisible()
    await expect(page.getByTestId('visual-library-prompt')).toHaveCount(0)
    await page.getByTestId('visual-library-prompt-toggle').click()
    await expect(page.getByTestId('visual-library-prompt')).toBeVisible()
    await expect(page.getByTestId('visual-library-prompt')).toContainText('looking back')
    await expect(page.getByTestId('visual-library-provenance')).toBeVisible()
  })

  test('mobile stays 2-column without horizontal overflow', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/visual-library')
    await expect(page.getByTestId('visual-library-grid')).toBeVisible()

    const columns = await page.getByTestId('visual-library-grid').evaluate((el) => {
      return getComputedStyle(el).gridTemplateColumns.split(' ').filter(Boolean).length
    })
    expect(columns).toBe(2)

    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    )
    expect(overflow).toBe(false)
  })

  test('outfit card can open wardrobe link from detail', async ({ page }) => {
    await page.goto('/visual-library')
    await page.getByTestId('visual-library-filter-outfit').click()
    await page.locator('[data-testid="visual-library-card"][data-kind="outfit"]').first().click()
    await expect(page.getByTestId('visual-library-detail')).toBeVisible()
    await expect(page.getByTestId('visual-library-open-wardrobe')).toBeVisible()
  })
})
