import { test, expect } from '../fixtures/sceneweaver.fixture'

test.describe('PixAI stub tagging → Visual Library', () => {
  test('async stub tags appear and are searchable in Visual Library', async ({
    page,
    api,
    seedScenario,
  }) => {
    const seeded = await seedScenario('visual_library')
    const previewIds = (seeded.extras?.preview_asset_ids as string[] | undefined) || []
    expect(previewIds.length).toBeGreaterThan(0)
    const assetId = previewIds[0]

    // Worker (stub tagger) processes TAG_ASSET jobs enqueued on asset save.
    await expect
      .poll(
        async () => {
          const tags = await api.getAssetTags(assetId)
          return tags.some((t) => t.tag === 'stub_auto')
        },
        { timeout: 60_000, intervals: [500, 1000, 2000] },
      )
      .toBe(true)

    await page.goto('/visual-library')
    await expect(page.getByTestId('visual-library-page')).toBeVisible()
    await page.getByTestId('visual-library-search').fill('stub_auto')
    await expect(page.getByTestId('visual-library-card').first()).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('visual-library-card-tags').first()).toContainText('stub_auto')
  })
})
