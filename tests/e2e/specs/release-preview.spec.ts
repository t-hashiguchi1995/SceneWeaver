import { mkdir, writeFile } from 'node:fs/promises'
import { test, expect } from '../fixtures/sceneweaver.fixture'

test('real release UI builds X, pixiv and Patreon editions and updates edited content', async ({ page, seedScenario }) => {
  const seeded = await seedScenario('m5_delivery')
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto(`/projects/${seeded.project_id}/release`)
  const title = '投稿テスト「夜の図書館」🌙'
  const summary = '創作イラストのテストです。\n二行目：日本語と改行の確認。'
  await page.getByLabel('作品タイトル').fill(title)
  await page.getByLabel('作品説明').fill(summary)
  const responsePromise = page.waitForResponse(response => response.url().endsWith('/api/v1/releases/preview') && response.request().method() === 'POST')
  await page.getByTestId('release-preview-button').click()
  const response = await responsePromise
  expect(response.status()).toBe(200)
  const result = await response.json()
  expect(result.editions.x.text).toBe(`${title} — ${summary}`)
  expect(result.editions.x.alt_text).toEqual([title])
  expect(result.editions.x.hashtags).toEqual(['#SceneWeaver'])
  expect(result.editions.pixiv).toMatchObject({ title, description: summary, tags: ['SceneWeaver'], ai_disclosure: true })
  expect(result.editions.patreon.title).toBe(title)
  expect(result.editions.patreon.body_markdown).toContain(summary)
  expect(result.editions.patreon.attachment_order).toEqual([])
  for (const platform of ['x', 'pixiv', 'patreon']) {
    await expect(page.getByTestId(`release-edition-${platform}`)).toContainText(title)
    await expect(page.getByTestId(`release-edition-${platform}`)).toContainText('二行目：日本語と改行の確認。')
  }
  await expect(page.getByTestId('release-edition-pixiv')).toContainText('AI生成の開示あり')
  await expect(page.getByText('公開前のプレビューです。投稿は行いません。')).toBeVisible()
  const artifactDir = '../../docs/validation/release-20261012'
  await mkdir(artifactDir, { recursive: true })
  await writeFile(`${artifactDir}/preview.json`, JSON.stringify(result, null, 2))
  await page.screenshot({ path: `${artifactDir}/desktop.png`, fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.screenshot({ path: `${artifactDir}/mobile.png`, fullPage: true })
  await page.getByLabel('作品タイトル').fill('編集後の投稿テスト')
  await page.getByLabel('作品説明').fill('変更後の説明')
  await page.getByTestId('release-preview-button').click()
  for (const platform of ['x', 'pixiv', 'patreon']) {
    await expect(page.getByTestId(`release-edition-${platform}`)).toContainText('編集後の投稿テスト')
    await expect(page.getByTestId(`release-edition-${platform}`)).toContainText('変更後の説明')
    await expect(page.getByTestId(`release-edition-${platform}`)).not.toContainText('二行目：')
  }
  expect(errors).toEqual([])
})
