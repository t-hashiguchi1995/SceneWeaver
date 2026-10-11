const { createRequire } = require('node:module')
const { readFileSync, writeFileSync } = require('node:fs')
const { resolve } = require('node:path')
const { pathToFileURL } = require('node:url')
const requireE2E = createRequire(resolve('tests/e2e/package.json'))
const { chromium } = requireE2E('@playwright/test')

async function main() {
  const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] })
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
    const results = []
    for (const [folder, expected] of [['rize', 36], ['rize-quality', 12]]) {
      const root = resolve('docs/validation', folder)
      const run = readFileSync(resolve(root, 'latest.txt'), 'utf8').trim()
      const dir = resolve(root, run)
      await page.goto(pathToFileURL(resolve(dir, 'index.html')).href)
      await page.locator('img').last().scrollIntoViewIfNeeded()
      await page.waitForFunction(count => {
        const images = [...document.images]
        images.forEach(i => i.loading = 'eager')
        return images.length === count && images.every(i => i.complete && i.naturalWidth > 100)
      }, expected)
      await page.locator('h1').scrollIntoViewIfNeeded()
      await page.screenshot({ path: resolve(dir, 'gallery-desktop.png'), fullPage: true })
      await page.setViewportSize({ width: 390, height: 844 })
      const mobileOverflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)
      if (mobileOverflow) throw new Error(`${folder} overflows mobile viewport`)
      await page.screenshot({ path: resolve(dir, 'gallery-mobile.png') })
      results.push({ folder, imagesDecoded: expected, mobileOverflow })
      await page.setViewportSize({ width: 1440, height: 1000 })
    }
    writeFileSync(resolve('docs/validation/rize-browser-check.json'), JSON.stringify(results, null, 2) + '\n')
    process.stdout.write(JSON.stringify(results) + '\n')
  } finally { await browser.close() }
}
main().catch(error => { process.stderr.write(error.stack + '\n'); process.exitCode = 1 })
