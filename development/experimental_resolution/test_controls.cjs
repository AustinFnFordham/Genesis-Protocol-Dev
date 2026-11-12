const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const {chromium}=require('playwright');
(async()=>{
 const root=path.resolve(__dirname,'../..');
 const source=fs.readFileSync(path.join(root,'campaigns/starwars_litrpg/ui/test_datapad_ui.cjs'),'utf8');
 const mock=source.match(/const MOCK = `([\s\S]*?)`;/)[1];
 const state=JSON.parse(fs.readFileSync(path.join(root,'development/.qa/ui/view/state.json')));
 state.turn_context=JSON.parse(fs.readFileSync(path.join(root,'campaigns/starwars_litrpg/ui/fixtures/hask_r2_sequencer.json')));
 state.processor=null;
 const browser=await chromium.launch(process.env.GENESIS_TEST_CHROMIUM?{executablePath:process.env.GENESIS_TEST_CHROMIUM}:{});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.addInitScript(({mock,state})=>{window.__store={'view/state':state};eval(mock);},{mock,state});
  await page.goto('file://'+path.join(root,'campaigns/starwars_litrpg/ui/genesis_datapad.html'));
  await page.waitForSelector('#submitTurn');
  assert.equal(await page.locator('#diceTemperature').count(),0);
  await page.evaluate(()=>{window.__store['view/state'].experimental_resolution={enabled:true};window.__notify();});
  await page.waitForSelector('#diceTemperature');
  assert.equal(await page.locator('#diceTemperature').inputValue(),'regular');
  assert.equal(await page.locator('#narrativeConsequences').inputValue(),'off');
  await page.locator('#diceTemperature').selectOption('heroic');
  await page.locator('#narrativeConsequences').selectOption('on');
  await page.locator('#w_say').fill('I wait and watch.');await page.locator('#addSay').click();
  await page.locator('#submitTurn').click();
  await page.waitForTimeout(120);
  const first=await page.evaluate(()=>Object.entries(window.__store).find(([k])=>k.startsWith('actions/')));
  assert.deepEqual(first[1].resolution_settings,{temperature:'heroic',narrative_consequences:true});
  assert.equal(await page.locator('#diceTemperature').isDisabled(),true);
  assert.match(await page.locator('.act').first().innerText(),/heroic.*Narrative Consequences: On/);
  await page.evaluate(key=>{
   window.__store[key].status='committed';const v=window.__store['view/state'];
   v.revision++;v.turn_context={...v.turn_context,context_id:'evt_9999'};window.__notify();
  },first[0]);
  await page.waitForTimeout(100);
  assert.equal(await page.locator('#diceTemperature').inputValue(),'regular');
  assert.equal(await page.locator('#narrativeConsequences').inputValue(),'off');
  await page.locator('#diceTemperature').selectOption('legendary');
  await page.locator('#w_say').fill('I keep watching.');await page.locator('#addSay').click();
  await page.locator('#submitTurn').click();await page.waitForTimeout(120);
  const all=await page.evaluate(()=>Object.entries(window.__store).filter(([k])=>k.startsWith('actions/')));
  assert.equal(all.length,2);
  assert.deepEqual(all.find(([k])=>k===first[0])[1],{...first[1],status:'committed'});
  assert.deepEqual(all.find(([k])=>k!==first[0])[1].resolution_settings,{temperature:'legendary',narrative_consequences:false});
  assert.deepEqual(errors,[]);
  console.log('PASS gated mobile controls, immutable settings, disabled pending turn, fresh scene defaults and history');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
