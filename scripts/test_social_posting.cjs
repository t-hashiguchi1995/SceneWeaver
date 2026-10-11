const { createRequire } = require('node:module');
const { resolve } = require('node:path');
const fs = require('node:fs');
const { chromium } = createRequire(resolve('tests/e2e/package.json'))('@playwright/test');
const asset = resolve('docs/validation/rize-comic/20261011T094102940732Z/comic.png');
const caption = 'patreonに追加画像を投稿しております。\n\nよければフォローお願いします。\npatreon：https://www.patreon.com/GenerativeAI410\nX（Twitter）：https://twitter.com/otk_LeiazelHets\n\nお題箱\nhttps://odaibako.net/u/thash';
const upload = {name:'lize-cafe-comic.png', mimeType:'image/png', buffer:fs.readFileSync(asset)};
const recordDir=resolve('docs/validation/social-posting-20261012');
fs.mkdirSync(recordDir,{recursive:true});
async function inspect(page, site) {
  const root = site === 'x' ? page.getByRole('dialog').last() : page.locator('body');
  console.log(JSON.stringify({site,url:page.url(), controls:await root.locator('input:not([type="password"]), textarea, [contenteditable="true"], [role="menuitem"], [role="radio"], button').evaluateAll(nodes=>nodes.filter(n=>n.type==='file'||n.getClientRects().length).map(n=>({tag:n.tagName,type:n.getAttribute('type'),role:n.getAttribute('role'),name:n.getAttribute('name'),label:n.getAttribute('aria-label'),placeholder:n.getAttribute('placeholder'),value:['radio','checkbox'].includes(n.type)?n.value:undefined,checked:n.checked,text:(n.innerText||'').slice(0,80),context:n.tagName==='INPUT'?(n.closest('label')?.innerText||'').slice(0,80):undefined})).filter(n=>!n.text||!/^(月村|椎名|フェラ|リゼ・|にじさんじ|VTuber|R-18|女の子|Vtuber|美少女|ヘル絵)/.test(n.text)).slice(-65))}));
}
(async()=>{
 const browser=await chromium.connectOverCDP('http://127.0.0.1:9222');
 try {
  const pages=browser.contexts().flatMap(c=>c.pages());
  const site=process.argv[2]; const action=process.argv[3]||'inspect';
  const host={pixiv:'pixiv.net',patreon:'patreon.com',x:'x.com'}[site];
  const page=pages.find(p=>new URL(p.url()).hostname.endsWith(host));
  if(!page)throw new Error('Missing tab');
  if(action==='verify'&&site==='pixiv'){
   const url='https://www.pixiv.net/artworks/150746419';await page.goto(url);
   await page.getByText('patreonにも同じ画像を投稿しております。',{exact:false}).first().waitFor();
   const info={status:'published',url,asset,title:'リゼ・ヘルエスタ',audience:'public',aiDisclosure:await page.getByText('AI生成',{exact:true}).count()>0,images:await page.locator('img').evaluateAll(ns=>ns.filter(n=>n.complete&&n.naturalWidth>500).map(n=>({width:n.naturalWidth,height:n.naturalHeight,alt:n.alt})).slice(0,5))};
   if(!info.images.length)throw new Error('Published image not loaded');
   fs.writeFileSync(resolve(recordDir,'pixiv.json'),JSON.stringify(info,null,2));console.log(JSON.stringify(info));
   await page.locator('main').first().screenshot({path:resolve(recordDir,'pixiv.png')});return;
  }
  if(action==='verify'&&site==='patreon'){
   const url=page.url().split('?')[0];if(!url.includes('/posts/rizeheruesuta-172069779'))throw new Error('Unexpected published URL');
   await page.getByText('今回は4コマ完成画像1枚の投稿テストです。',{exact:false}).first().waitFor();
   const anon=await browser.newContext();
   try{
    const publicPage=await anon.newPage();await publicPage.goto(url);await publicPage.getByText('今回は4コマ完成画像1枚の投稿テストです。',{exact:false}).first().waitFor();
    await publicPage.waitForFunction(()=>Array.from(document.images).some(i=>i.complete&&i.naturalWidth>500));
    const result={status:'published',url,asset,title:'リゼ・ヘルエスタ',audience:'public',anonymousAccessVerified:true};
    fs.writeFileSync(resolve(recordDir,'patreon.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
    await publicPage.screenshot({path:resolve(recordDir,'patreon.png')});
   }finally{await anon.close();}return;
  }
  if(action==='prepare'&&site==='pixiv'){
   await page.getByRole('textbox',{name:'タイトル',exact:true}).fill('リゼ・ヘルエスタ');
   await page.getByRole('textbox',{name:'キャプション',exact:true}).fill(caption);
   await page.locator('input[type="file"]').first().setInputFiles(upload);
  }
  if(action==='prepare'&&site==='x'){
   const dialog=page.getByRole('dialog').last();
   await dialog.locator('[contenteditable="true"]').fill('テスト');
   await dialog.locator('input[type="file"]').setInputFiles(upload);
  }
  if(action==='prepare'&&site==='patreon'){
   const item=page.getByRole('menuitem',{name:'投稿する',exact:true});
   if(await item.count())await item.click();
   else {await page.getByRole('button',{name:'投稿を作成',exact:true}).first().click();await page.getByRole('menuitem',{name:'投稿する',exact:true}).click();}
  }
  if(action==='configure'&&site==='pixiv'){
   await page.getByText('全年齢',{exact:true}).click();
   await page.locator('label').filter({has:page.locator('input[name="ai_type"][value="aiGenerated"]')}).click();
   await page.getByText('全体に公開',{exact:true}).click();
   await page.locator('label').filter({has:page.locator('input[name="sexual"][value="false"]')}).click();
   const tags=page.locator('input[placeholder^="タグ"]');
   for(const tag of ['リゼ・ヘルエスタ','にじさんじ','AI生成','4コマ']){await tags.fill(tag);await tags.press('Enter');}
  }
  if(action==='publish'&&site==='pixiv'){
   const record=resolve(recordDir,'pixiv.json');
   if(fs.existsSync(record))throw new Error('Submission already recorded; inspect before retry');
   for(const [name,value]of [['restrict','public'],['x_restrict','general'],['ai_type','aiGenerated'],['sexual','false']]){
    if(!await page.locator(`input[name="${name}"][value="${value}"]`).isChecked())throw new Error(`Unexpected ${name}`);
   }
   await page.getByRole('textbox',{name:'キャプション',exact:true}).fill(caption.replace('patreonに追加画像を投稿しております。','テスト\n\npatreonにも同じ画像を投稿しております。'));
   fs.writeFileSync(record,JSON.stringify({status:'submission_started',asset,title:'リゼ・ヘルエスタ',audience:'public'},null,2));
   await page.getByRole('button',{name:'投稿する',exact:true}).last().click();
   await page.waitForTimeout(5000);
   console.log(JSON.stringify({site,url:page.url(),messages:await page.locator('[role="alert"]').allTextContents(),links:await page.locator('a[href*="/artworks/"]').evaluateAll(ns=>ns.map(n=>({href:n.href,text:n.innerText})).slice(0,10))}));
   return;
  }
  if(action==='public-image'&&site==='patreon'){
   await page.getByRole('radio',{name:'無料でアクセス'}).check();
   await page.getByRole('button',{name:'ダイアログを閉じる'}).click();
   await page.locator('#photosInput').setInputFiles(upload);
  }
  if(action==='publish'&&site==='patreon'){
   const record=resolve(recordDir,'patreon.json');
   if(fs.existsSync(record))throw new Error('Submission already recorded; inspect before retry');
   if(await page.getByRole('button',{name:'無料',exact:true}).count()!==1)throw new Error('Public audience not configured');
   if(await page.getByRole('textbox',{name:'タイトル',exact:true}).inputValue()!=='リゼ・ヘルエスタ')throw new Error('Unexpected title');
   console.log(JSON.stringify({images:await page.locator('img').evaluateAll(ns=>ns.map(n=>({alt:n.alt,loaded:n.complete,width:n.naturalWidth})).filter(n=>n.width>300))}));
   fs.writeFileSync(record,JSON.stringify({status:'submission_started',draftUrl:page.url(),asset,audience:'public'},null,2));
   await page.getByRole('button',{name:'掲載する',exact:true}).click();
   await page.waitForTimeout(2000);
  }
  if(action==='fields'){
   console.log(JSON.stringify({site,fields:await page.locator('input:not([type="password"]),textarea').evaluateAll(ns=>ns.map(n=>({type:n.type,name:n.name,placeholder:n.placeholder,label:n.getAttribute('aria-label'),value:n.type==='file'?undefined:n.value,checked:n.checked})))}));return;
  }
  if(action==='configure'&&site==='patreon'){
   await page.getByRole('textbox',{name:'タイトル',exact:true}).fill('リゼ・ヘルエスタ');
   await page.getByRole('textbox',{name:'投稿コンテンツのテキスト入力フィールド'}).fill('テスト\n\n今回は4コマ完成画像1枚の投稿テストです。\n\npixivにもサンプル投稿しております。');
   console.log(JSON.stringify(await page.locator('input[type="file"]').evaluateAll(nodes=>nodes.map(n=>({accept:n.accept,multiple:n.multiple,html:n.outerHTML.slice(0,350)})))));
   await page.getByRole('button',{name:'支払済み',exact:true}).click();
  }
  if(action==='publish'&&site==='x'){
   const record=resolve(recordDir,'x.json');
   if(fs.existsSync(record))throw new Error('Submission already recorded; inspect before any retry');
   const dialog=page.getByRole('dialog').last();
   if(await dialog.getByRole('textbox',{name:'ポスト本文'}).innerText()!=='テスト')throw new Error('Unexpected post text');
   if(await dialog.getByRole('button',{name:'メディアを削除'}).count()!==1)throw new Error('Expected one image');
   fs.writeFileSync(record,JSON.stringify({status:'submission_started',text:'テスト',asset},null,2));
   const responsePromise=page.waitForResponse(r=>r.url().includes('/CreateTweet')&&r.request().method()==='POST',{timeout:30000});
   await dialog.getByRole('button',{name:'ポストする',exact:true}).click();
   const response=await responsePromise;const data=await response.json();
   const tweet=data.data?.create_tweet?.tweet_results?.result;
   const id=tweet?.rest_id||tweet?.tweet?.rest_id;
   if(!id)throw new Error('Submission response has no tweet id; inspect page before retry');
   const result={status:'published',url:`https://x.com/otk_LeiazelHets/status/${id}`,text:'テスト',asset};
   fs.writeFileSync(record,JSON.stringify(result,null,2));console.log(JSON.stringify(result));
   await page.goto(result.url);await page.getByTestId('tweetText').filter({hasText:'テスト'}).first().waitFor();
   console.log('X published post verified in browser');return;
  }
  await page.waitForTimeout(1500);
  await inspect(page,site);
 }finally{await browser.close();}
})().catch(e=>{console.error(e.message);process.exitCode=1;});
