const {chromium}=require('playwright');
const fs=require('fs');
const path=require('path');
const {pathToFileURL}=require('url');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.PLAYWRIGHT_CHANNEL?{channel:process.env.PLAYWRIGHT_CHANNEL}:{})});
 const page=await browser.newPage({viewport:{width:1440,height:1100},deviceScaleFactor:1});
 const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 const root=path.resolve(__dirname,'..');
 await page.goto(pathToFileURL(path.join(root,'dashboard/index.html')).href);
 await page.waitForSelector('#trend .main-svg');
 const out=[];
 async function check(label,needle){const text=await page.locator('main').innerText();if(!text.includes(needle))throw new Error(label+': missing '+needle);out.push({test:label,result:'PASS'});}
 await check('Default 2026 coverage','120 registros');
 await check('Default small groups warning','15 grupo(s)');
 await check('Price missing August','7/8 meses');
 await page.locator('#asset').selectOption('IN');await check('Asset selection','8 registros');
 await page.locator('#metric').selectOption('gas');await check('Gas units','MPC');
 await page.locator('#asset').selectOption('AB16');await check('Empty subset','No hay registros');
 await page.locator('#reset').click();await page.locator('#start').selectOption('2022-01');await page.locator('#end').selectOption('2026-08');
 await check('Full history','789 registros');await page.locator('#balanced').check();await check('Balanced cohort','616 registros');await check('Balanced assets','11 activos');
 await page.locator('#balanced').uncheck();await page.locator('#asset').selectOption('LA');await page.locator('#start').selectOption('2022-08');await page.locator('#end').selectOption('2022-08');await check('Conflict NA handling','1 valor(es)');
 await page.locator('#start').selectOption('2026-08');await page.locator('#end').selectOption('2022-01');await check('Invalid date range','inicio es posterior');
 await page.locator('#reset').click();
 const download=page.waitForEvent('download');await page.locator('#download').click();const dl=await download;await dl.saveAs(path.join(require('os').tmpdir(),'eda_selection_test.csv'));out.push({test:'CSV download',result:'PASS'});
 await page.getByRole('tab',{name:'Calidad y cobertura'}).click();await page.waitForSelector('#coverage .main-svg');await check('Quality tab','Celdas contradictorias');
 await page.getByRole('tab',{name:'Decisiones',exact:true}).click();await check('Decisions tab','Indillana');
 await page.getByRole('tab',{name:'Método y fuentes'}).click();await check('Method tab','siete pasos');
 await page.getByRole('tab',{name:'Explorar producción'}).click();
 await page.waitForFunction(()=>document.getElementById('trend')._fullLayout.yaxis.type==='linear');out.push({test:'Numerical axes remain linear after all filters',result:'PASS'});
 await page.screenshot({path:path.join(root,'docs/dashboard.png'),fullPage:true});
 await page.setViewportSize({width:390,height:844});await page.waitForFunction(()=>document.getElementById('trend').getBoundingClientRect().width>=document.querySelector('#trend .svg-container').getBoundingClientRect().width-1);await page.waitForFunction(()=>document.documentElement.scrollWidth<=window.innerWidth+1);await page.screenshot({path:path.join(require('os').tmpdir(),'eda_dashboard_mobile.png'),fullPage:true});
 if(await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+1)){console.log(await page.evaluate(()=>Array.from(document.querySelectorAll('body *')).filter(e=>e.getBoundingClientRect().right>innerWidth+1&&e.getBoundingClientRect().width>0).slice(0,15).map(e=>[e.tagName,e.id,e.className,e.getBoundingClientRect().right])));throw new Error('Mobile overflow')};out.push({test:'Mobile 390px no page overflow',result:'PASS'});
 if(errors.length)throw new Error(JSON.stringify(errors));
 fs.writeFileSync(path.join(root,'reportes/qa_dashboard.json'),JSON.stringify({surface:'Microsoft Edge headless, Playwright, archivo estático local',checks:out,javascript_errors:errors},null,2));
 console.log(JSON.stringify(out));await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});


