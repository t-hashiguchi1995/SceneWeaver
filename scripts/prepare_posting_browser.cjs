const { createRequire } = require('node:module');
const { resolve } = require('node:path');
const { chromium } = createRequire(resolve('tests/e2e/package.json'))('@playwright/test');
(async () => {
  const browser = await chromium.connectOverCDP('http://127.0.0.1:9222');
  try {
    const context = browser.contexts().find(c => c.pages().some(p => p.url().includes('patreon.com')));
    for (const site of ['pixiv', 'patreon', 'x']) {
      const page = context.pages().find(p => new URL(p.url()).hostname.endsWith(site === 'pixiv' ? 'pixiv.net' : site === 'patreon' ? 'patreon.com' : 'x.com'));
      if (!page) throw new Error(`Missing ${site} tab`);
      if (site === 'pixiv') await page.goto('https://www.pixiv.net/upload.php');
      if (site === 'patreon') await page.getByRole('button', {name: '投稿を作成', exact: true}).first().click();
      if (site === 'x') await page.goto('https://x.com/compose/post');
      await page.waitForTimeout(1500);
      console.log(JSON.stringify({site, path:new URL(page.url()).pathname,
        controls:await page.locator('input, textarea, [contenteditable="true"], [role="menuitem"], [role="radio"], button').evaluateAll(nodes => nodes.filter(n=>n.getClientRects().length && !(n.tagName==='BUTTON' && n.parentElement?.innerText?.includes('よく使うタグ'))).map(n=>({tag:n.tagName,role:n.getAttribute('role'),type:n.getAttribute('type'),name:n.getAttribute('name'),label:n.getAttribute('aria-label'),placeholder:n.getAttribute('placeholder'),text:(n.innerText||'').slice(0,120)})).slice(-40))}));
    }
  } finally { await browser.close(); }
})().catch(e=>{console.error(e.message);process.exitCode=1;});
