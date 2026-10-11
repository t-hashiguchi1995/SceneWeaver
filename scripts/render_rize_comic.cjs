const { createRequire } = require('node:module')
const { readFileSync, writeFileSync } = require('node:fs')
const { resolve } = require('node:path')
const { pathToFileURL } = require('node:url')
const requireE2E = createRequire(resolve('tests/e2e/package.json'))
const { chromium } = requireE2E('@playwright/test')
const escape = text => String(text).replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]))

async function main() {
  const root = resolve('docs/validation/rize-comic')
  const run = readFileSync(resolve(root, 'latest.txt'), 'utf8').trim()
  const dir = resolve(root, run)
  const report = JSON.parse(readFileSync(resolve(dir, 'results.json'), 'utf8'))
  const pattern = report.patterns[0]
  const picks = (process.argv[2] ?? '1,1,1,1').split(',').map(n => Number(n) - 1)
  if (picks.length !== 4 || picks.some(n => !Number.isInteger(n) || n < 0 || n > 3)) throw new Error('Use four candidate indexes between 1 and 4')
  const panels = pattern.beats.map((beat, i) => {
    const chosen = beat.assets[picks[i]]
    const options = beat.assets.map((asset, j) => `<option value="${escape(asset.file)}"${j === picks[i] ? ' selected' : ''}>候補${j + 1}</option>`).join('')
    return `<div class="panel-wrap"><label class="controls">${i + 1}コマ目の画像 <select data-panel="${i}">${options}</select></label><article class="panel"><span class="number">${i + 1}</span><img id="panel-${i}" src="${escape(chosen.file)}" alt="${escape(beat.intent)}"><div class="bubble">${escape(beat.locked_text).replace(/\n/g, '<br>')}</div></article></div>`
  }).join('')
  const gallery = pattern.beats.map((beat, i) => `<section><h2>${i + 1}コマ目の4候補</h2><div class="candidates">${beat.assets.map((asset, j) => `<figure><img src="${escape(asset.file)}" alt="${i + 1}コマ候補${j + 1}"><figcaption>候補${j + 1}</figcaption></figure>`).join('')}</div></section>`).join('')
  const doc = `<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escape(pattern.title)} — リゼ・ヘルエスタ</title><style>*{box-sizing:border-box}body{margin:0;background:#e7e8eb;color:#121821;font-family:"Noto Sans CJK JP","Yu Gothic",sans-serif}main{max-width:1680px;margin:auto;padding:28px}.comic-page{background:white;padding:24px;border-radius:8px}.heading{display:flex;align-items:baseline;gap:20px;flex-wrap:wrap;margin-bottom:20px}h1{font-size:38px;margin:0}.heading p{margin:0;font-size:19px}.panels{display:grid;grid-template-columns:1fr 1fr;gap:18px}.panel{position:relative;border:3px solid #151924;overflow:hidden;background:white;aspect-ratio:3/4}.panel>img{width:100%;height:100%;object-fit:cover;display:block}.number{position:absolute;top:12px;left:12px;background:white;border:2px solid #151924;border-radius:50%;width:36px;height:36px;text-align:center;line-height:32px;font-weight:700;z-index:2}.bubble{position:absolute;bottom:18px;left:6%;width:88%;border:3px solid #151924;border-radius:50% / 45%;padding:25px 28px;background:rgba(255,255,255,.98);text-align:center;font-weight:700;font-size:28px;line-height:1.6;box-shadow:0 3px 6px #0002}.bubble:before{content:"";position:absolute;left:66%;top:-18px;width:20px;height:28px;background:white;border-top:3px solid #151924;border-left:3px solid #151924;transform:skew(18deg) rotate(20deg)}.controls{display:flex;gap:12px;align-items:center;margin-bottom:8px;font-size:16px}select{font:inherit;padding:5px}.export .controls{display:none}.note{font-size:14px;margin:16px 0 0;color:#555}.candidates{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}figure{margin:0}figure img{width:100%;display:block}details{margin-top:28px}a{color:#164b95}@media(max-width:650px){main{padding:8px}.comic-page{padding:12px}h1{font-size:25px}.heading p{font-size:14px}.panels{grid-template-columns:1fr}.bubble{font-size:20px;padding:20px}.candidates{grid-template-columns:repeat(2,minmax(0,1fr))}}</style><main><div class="comic-page"><header class="heading"><h1>${escape(pattern.title)}</h1><p>リゼ・ヘルエスタ ／ 創作4コマ</p></header><div class="panels">${panels}</div><p class="note">台本：今回の創作。画像：実ComfyUI・Anima、既存品質/artistタグ、24 steps。本人の実発言・公式作品ではありません。</p></div><details><summary>他の画像候補を比較する</summary>${gallery}</details><details><summary>ストーリーと生成条件</summary><p>${escape(pattern.objective)}</p><p>画像選択は各コマの「候補」で切り替えられます。日本語のセリフは別レイヤーで表示しています。</p><a href="index.html">検証詳細</a> · <a href="results.json">条件と履歴JSON</a></details></main><script>document.querySelectorAll('select[data-panel]').forEach(select=>select.addEventListener('change',()=>{document.getElementById('panel-'+select.dataset.panel).src=select.value}))</script></html>`
  writeFileSync(resolve(dir, 'comic.html'), doc)
  const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--no-sandbox', '--disable-dev-shm-usage'] })
  try {
    const page = await browser.newPage({ viewport: { width: 1680, height: 1200 }, deviceScaleFactor: 1 })
    await page.goto(pathToFileURL(resolve(dir, 'comic.html')).href)
    await page.waitForFunction(() => [...document.querySelectorAll('.panel img')].every(i => i.complete && i.naturalWidth > 100))
    if (await page.locator('.bubble').count() !== 4) throw new Error('Missing dialogue bubble')
    await page.evaluate(() => document.body.classList.add('export'))
    await page.locator('.comic-page').screenshot({ path: resolve(dir, 'comic.png') })
    await page.evaluate(() => document.body.classList.remove('export'))
    await page.locator('details').first().evaluate(el => el.open = true)
    await page.waitForFunction(() => [...document.images].every(i => i.complete && i.naturalWidth > 100))
    await page.locator('details').first().screenshot({ path: resolve(dir, 'candidates.png') })
    await page.locator('details').first().evaluate(el => el.open = false)
    await page.setViewportSize({ width: 390, height: 844 })
    if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw new Error('Mobile overflow')
    await page.screenshot({ path: resolve(dir, 'comic-mobile.png') })
    writeFileSync(resolve(dir, 'comic-selection.json'), JSON.stringify({title:pattern.title,picks:picks.map(n=>n+1),panels:pattern.beats.map((beat,i)=>({text:beat.locked_text,asset:beat.assets[picks[i]],shot_id:beat.shot_id})), checks:{dialogueBubbles:4,imagesDecoded:true,mobileOverflow:false}},null,2)+'\n')
    process.stdout.write(JSON.stringify({comic:resolve(dir,'comic.html'),png:resolve(dir,'comic.png'),candidates:resolve(dir,'candidates.png')})+'\n')
  } finally { await browser.close() }
}
main().catch(error=>{process.stderr.write(error.stack+'\n');process.exitCode=1})
