import { defineConfig, devices } from '@playwright/test'

import { API_BASE, WEB_BASE } from './support/env'

export default defineConfig({
  testDir: './specs',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [['list'], ['html', { open: 'never' }]],
  timeout: 90_000,
  expect: { timeout: 15_000 },
  use: {
    baseURL: WEB_BASE,
    // Ubuntu 20.04 WSL: bundled Chromium unsupported — use system Chrome.
    channel: process.env.PLAYWRIGHT_CHANNEL ?? 'chrome',
    headless: true,
    launchOptions: {
      args: ['--no-sandbox', '--disable-dev-shm-usage'],
    },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    // bundled ffmpeg unsupported on ubuntu20.04; keep screenshots+trace instead
    video: 'off',
    // Do NOT set Accept: application/json globally — document navigations to SPA
    // routes (e.g. /shots) then 404 and page.goto hangs / never reaches DOMContentLoaded.
    // ApiClient sets Accept on API requests explicitly.
  },
  projects: [
    {
      name: 'mock',
      use: {
        ...devices['Desktop Chrome'],
        channel: process.env.PLAYWRIGHT_CHANNEL ?? 'chrome',
      },
      testIgnore: [/live\//],
    },
    {
      name: 'live',
      timeout: 10 * 60_000,
      use: {
        ...devices['Desktop Chrome'],
        channel: process.env.PLAYWRIGHT_CHANNEL ?? 'chrome',
      },
      testMatch: [/live\//],
    },
  ],
  metadata: {
    apiBase: API_BASE,
    webBase: WEB_BASE,
  },
})