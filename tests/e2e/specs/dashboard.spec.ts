import { test, expect } from '../fixtures/sceneweaver.fixture'

test('dashboard navigation fits desktop and mobile and recovers from API errors', async ({ page, api }) => {
  await api.reset()
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto('/')
  await expect(page.getByRole('heading', { name: '最近のプロジェクト' })).toBeVisible()
  await expect(page.getByTestId('home-jobs')).toBeVisible()
  await expect(page.getByTestId('recent-projects')).toContainText('プロジェクトはまだありません')
  await page.screenshot({ path: 'test-results/dashboard-desktop.png', fullPage: true })

  await page.setViewportSize({ width: 390, height: 844 })
  await page.getByRole('button', { name: 'メニュー' }).click()
  await expect(page.getByTestId('nav-settings')).toBeVisible()
  await page.getByRole('button', { name: '閉じる' }).click()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.screenshot({ path: 'test-results/dashboard-mobile.png', fullPage: true })
  await page.getByRole('link', { name: /新しいプロジェクト/ }).first().click()
  await expect(page).toHaveURL(/\/projects/)

  await page.route('**/api/v1/projects', (route) => route.fulfill({ status: 500, body: 'Unavailable' }))
  await page.goto('/')
  await expect(page.getByRole('alert')).toContainText('データを読み込めませんでした', { timeout: 20000 })
  await page.unroute('**/api/v1/projects')
  await page.getByRole('button', { name: '再読み込み' }).click()
  await expect(page.getByRole('alert')).toHaveCount(0)
  await expect(page.getByTestId('recent-projects')).toContainText('プロジェクトはまだありません')
})
