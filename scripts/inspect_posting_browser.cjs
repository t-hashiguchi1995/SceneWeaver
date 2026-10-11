const { createRequire } = require('node:module');
const { resolve } = require('node:path');
const { chromium } = createRequire(resolve('tests/e2e/package.json'))('@playwright/test');

(async () => {
  const browser = await chromium.connectOverCDP('http://127.0.0.1:9222');
  try {
    for (const context of browser.contexts()) {
      for (const page of context.pages()) {
        const url = new URL(page.url());
        if (!/(^|\.)(patreon\.com|pixiv\.net|x\.com|twitter\.com)$/.test(url.hostname)) continue;
        console.log(JSON.stringify({ site: url.hostname, path: url.pathname, title: await page.title(),
          controls: await page.locator('[role="menu"], [role="dialog"], input:not([type="password"]), textarea, [contenteditable="true"], [role="menuitem"]').evaluateAll(nodes => nodes
            .filter(n => n.getClientRects().length).map(n => ({text: (n.innerText || n.getAttribute('aria-label') || '').slice(0,100), href: n.getAttribute('href')})).slice(0,70)) }));
      }
    }
  } finally { await browser.close(); }
})().catch(e => { console.error(e.message); process.exitCode = 1; });
