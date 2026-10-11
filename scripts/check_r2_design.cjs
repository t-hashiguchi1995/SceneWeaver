const { createRequire } = require('node:module');
const { resolve } = require('node:path');
const { pathToFileURL, fileURLToPath } = require('node:url');
const { mkdirSync, writeFileSync, existsSync } = require('node:fs');
const assert = require('node:assert/strict');
const { chromium } = createRequire(resolve('tests/e2e/package.json'))('@playwright/test');

(async () => {
  const doc = resolve('docs/architecture/sceneweaver_ui_integration_design_r2.html');
  const out = resolve('docs/validation/r2-design-20261012');
  mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto(pathToFileURL(doc).href);
    const links = await page.locator('a').evaluateAll(nodes => nodes.map(n => n.href));
    for (const href of links) {
      const url = new URL(href);
      if (url.hash && fileURLToPath(url) === doc) assert(await page.locator(url.hash).count(), `Missing anchor: ${href}`);
      else if (url.protocol === 'file:') assert(existsSync(fileURLToPath(url)), `Missing file: ${href}`);
    }
    const allCount = await page.locator('#status-table tbody tr').count();
    for (const value of ['done', 'partial', 'todo']) {
      await page.locator('#status-filter').selectOption(value);
      assert.equal(await page.locator('#status-table tbody tr:visible').count(), await page.locator(`#status-table tbody tr[data-status="${value}"]`).count());
    }
    await page.locator('#status-filter').selectOption('all');
    assert.equal(await page.locator('#status-table tbody tr:visible').count(), allCount);
    await page.locator('#tab-x').focus();
    await page.keyboard.press('ArrowRight');
    assert.equal(await page.locator('#tab-pixiv').getAttribute('aria-selected'), 'true');
    assert.equal(await page.locator('#edition-panel').getAttribute('aria-labelledby'), 'tab-pixiv');
    await page.locator('#mock-approval').check();
    await page.locator('#mock-submit').click();
    assert.match(await page.locator('#mock-approval-result').innerText(), /実際の承認・公開は行っていません/);
    await page.locator('#mock-body').fill('変更後の本文\n次の行');
    assert.equal(await page.locator('#mock-approval').isChecked(), false);
    assert.match(await page.locator('#edition-text').innerText(), /変更後の本文\n次の行/);
    await page.locator('#simulate-confirm').click();
    assert.match(await page.locator('#simulation-state').innerText(), /^succeeded/);
    await page.locator('#simulate-retry').click();
    assert.match(await page.locator('#simulation-state').innerText(), /^queued/);
    await page.locator('#simulate-reset').click();
    assert.match(await page.locator('#simulation-state').innerText(), /^ambiguous/);
    await page.locator('h1').scrollIntoViewIfNeeded();
    await page.screenshot({ path: resolve(out, 'desktop.png'), fullPage: true });
    await page.screenshot({ path: resolve(out, 'desktop-top.png') });
    await page.locator('#release-ui .shell').screenshot({ path: resolve(out, 'release-wireframe.png') });
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, 'Mobile overflow');
    await page.screenshot({ path: resolve(out, 'mobile.png'), fullPage: true });
    assert.deepEqual(errors, []);
    const result = { document: doc, sections: await page.locator('main > section').count(), statusRows: allCount, linksChecked: links.length, desktopWidth: 1440, mobileWidth: 390, pageErrors: errors, checks: ['local links and anchors', 'status filters', 'keyboard tabs', 'approval reset on edit', 'multiline preview', 'recovery demo', 'mobile overflow'], scope: 'Design HTML only; no GPU generation or external publishing' };
    writeFileSync(resolve(out, 'checks.json'), JSON.stringify(result, null, 2) + '\n');
    console.log(JSON.stringify(result));
  } finally { await browser.close(); }
})().catch(e => { console.error(e.stack); process.exitCode = 1; });
