// Real browser engines over local HTTP. Emulated sizes/touch are NOT physical Safari evidence.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {spawn}=require('node:child_process');
const pw=require('playwright');
const engine=process.env.M12_ENGINE||'chromium';
const scenarios=[['iphone-portrait',390,844,true],['iphone-small',320,568,true],['iphone-landscape',844,390,true],
 ['ipad-portrait',820,1180,true],['ipad-landscape',1180,820,true],['desktop',1440,900,false]];
const results=[];
(async()=>{
 const srv=spawn('python3',['-B',path.join(__dirname,'serve_preview.py'),'--port','0'],{stdio:['ignore','pipe','inherit']});
 // Port 0 is allocated by the OS, reported by the server after bind.
 let browser;
 try {
  const origin=await new Promise((resolve,reject)=>{srv.on('exit',c=>reject(Error('server exit '+c)));srv.stdout.on('data',d=>{
   const m=String(d).match(/http:\/\/127\.0\.0\.1:(\d+)/);if(m)resolve('http://127.0.0.1:'+m[1]);});});
  browser=await pw[engine].launch(process.env.M12_CHANNEL?{channel:process.env.M12_CHANNEL}:{});
  for(const [name,width,height,touch] of scenarios){
   const ctx=await browser.newContext({viewport:{width,height},hasTouch:touch,isMobile:touch});
   const page=await ctx.newPage(),errors=[],writes=[];
   page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.method()!=='GET')writes.push(r.url());});
   const response=await page.goto(origin+'/');assert.equal(response.status(),200);
   assert.match(response.headers()['content-type'],/^text\/html/);assert.equal(response.headers()['content-disposition'],'inline');
   assert((await response.body()).length>10000);await page.waitForSelector('#intentPlans');
   assert.match(await page.locator('#devEnvBanner').innerText(),/M12/);
   assert.match(await page.locator('#testBanner').innerText(),/mobile-test-1/);
   assert.equal(await page.locator('#mechanicsCatalog').getAttribute('open'),null);
   await page.getByRole('button',{name:/^Ignite the lightsaber Available/}).click();
   assert.match(await page.locator('#colCenter').innerText(),/1 planned/);await page.locator('#clearTurn').click();
   await page.locator('#w_tb4_action').fill('Watch the crate line while protecting Wick.');
   // Immediate persistence: no debounce sleep before this assertion or navigation.
   assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('genesis-preview.datapad.ui')).sel.tb4custom.action),
     'Watch the crate line while protecting Wick.');
   await page.reload();await page.waitForSelector('#w_tb4_action');
   assert.equal(await page.locator('#w_tb4_action').inputValue(),'Watch the crate line while protecting Wick.');
   await page.locator('#mechanicsCatalog > summary').click();
   await page.locator('input[data-g="dialogue"][value="own"]').check();
   await page.locator('#w_own').fill('Wick, stay close.');
   await page.locator('#w_tb4_movement').fill('Step five feet along the crate line.');
   await page.locator('#w_tb4_action').focus();await page.locator('#w_tb4_action').press('End');
   await page.evaluate(()=>{window.__notify();});
   await page.waitForTimeout(100);
   assert.equal(await page.evaluate(()=>document.activeElement.id),'w_tb4_action');
   assert.equal(await page.locator('#w_tb4_action').inputValue(),'Watch the crate line while protecting Wick.');
   // Keyboard navigation: Tab must not submit or lose the plan.
   await page.keyboard.press('Tab');assert.equal(await page.locator('.act').count(),0);
   // Preserve simulated review editing across a reload.
   await page.locator('[data-whedit]').first().fill('I am shaken but still want to help.');
   await page.reload();await page.waitForSelector('#w_tb4_action');
   assert.equal(await page.locator('[data-whedit]').first().inputValue(),'I am shaken but still want to help.');
   await page.getByRole('button',{name:'Use my edit',exact:true}).click();
   await page.waitForFunction(()=>window.__store['view/state'].whisper.pending===null);
   const rev=await page.evaluate(()=>window.__store['view/state'].revision);
   await page.locator('#submitTurn').click();
   await page.waitForFunction(()=>Object.values(window.__store).some(a=>a&&a.preview&&a.status==='failed'));
   const row=await page.evaluate(()=>Object.entries(window.__store).filter(([k,a])=>k.startsWith('actions/')&&a.kind!=='whisper_response').pop()[1]);
   assert.equal(row.preview,true);assert.match(row.error,/no GM is attached/);
   assert.match(row.text,/Wick, stay close/);assert.match(row.text,/Step five feet along the crate line/);
   assert.match(row.text,/Watch the crate line/);
   assert.equal(await page.evaluate(()=>window.__store['view/state'].revision),rev);
   assert.equal(await page.evaluate(()=>window.__store['view/state'].processor),null);
   // Refresh the actual subscription path with a zero-economy fixture, never a ledger mutation.
   await page.evaluate(()=>{const s=window.__store['view/state'];s.turn_context.context_id+='-zero';
    s.turn_context.budget={action:0,bonus_action:0,movement_ft:0,object_interaction:0,reaction:0};window.__notify();});
   await page.waitForTimeout(100);
   assert.match(await page.locator('.composer > .budget').first().innerText(),/action:\s*0 remaining/i);
   assert.equal(await page.locator('#intentPlans [data-tb4pick]').count(),0);
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),name+' horizontal overflow');
   if(width<=960){
    for(const tab of ['aero','gear','journal','scene']){await page.locator('#tabbar [data-t="'+tab+'"]').click();
     assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),name+' '+tab+' overflow');}
   }
   await page.locator('#devEnvBanner > details > summary').click();
   const diag=await page.getByRole('link',{name:'WHISPER / evidence / causal diagnostics'}).getAttribute('href');
   const dr=await page.goto(origin+'/'+diag);assert.equal(dr.status(),200);assert.match(await page.locator('body').innerText(),/Algorithm A/);
   await page.goto(origin+'/');await page.waitForSelector('#intentPlans');
   await page.evaluate(()=>localStorage.setItem('m12-unrelated','keep'));
   await page.locator('#devEnvBanner > details > summary').click();await page.getByRole('button',{name:'Reset preview state',exact:true}).click();
   await page.waitForSelector('#intentPlans');
   assert.equal(await page.locator('#w_tb4_action').inputValue(),'');
   assert.equal(await page.evaluate(()=>localStorage.getItem('m12-unrelated')),'keep');
   assert.equal(await page.evaluate(()=>Object.keys(window.__store).filter(k=>k.startsWith('actions/')).length),0);
   assert.equal(await page.evaluate(()=>window.__store['view/state'].revision),4);
   assert(!await page.evaluate(()=>!!navigator.serviceWorker&&!!navigator.serviceWorker.controller));
   assert.deepEqual(errors,[]);assert.deepEqual(writes,[]);
   results.push({name,engine,platform:process.platform,width,height,touch,physical_device:false,passed:true});
   await ctx.close();
  }
  fs.mkdirSync(path.join(__dirname,'../.qa'),{recursive:true});
  fs.writeFileSync(path.join(__dirname,'../.qa/m12-'+engine+'-'+process.platform+'.json'),JSON.stringify(results,null,2));
  console.log(JSON.stringify(results));
 }finally{if(browser)await browser.close();srv.kill();}
})().catch(e=>{console.error(e);process.exit(1)});
