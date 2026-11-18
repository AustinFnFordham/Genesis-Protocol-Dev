// M11: public-only deterministic recommendations + integration with the existing validator.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const TB = require('./src/tb4.js');
const T = require('./turn_contract.js');
const state = JSON.parse(fs.readFileSync(process.argv[3] || 'development/.qa/state_round1.json'));
const c = T.withEquipment(state.turn_context);
const availability = Object.fromEntries(T.availability(T.emptyDecl(c), c).map(a => [a.type + ':' + a.option, a]));
const before = JSON.stringify(c);
const p = TB.plans(c, {style:'cautious'}, availability);
assert.deepEqual(p, TB.plans(c, {style:'cautious'}, availability));
assert.equal(JSON.stringify(c), before);
assert(p.length <= 4);
assert.equal(new Set(p.map(x=>x.label.toLowerCase().replace(/[^a-z0-9]+/g,' ').trim())).size, p.length);
for (const x of p) assert.notEqual(x.status, 'blocked');
const zero = {...c, budget:{...c.budget, action:0, bonus_action:0, movement_ft:0, object_interaction:0}};
assert.equal(TB.plans(zero, {}, availability).length, 0);
const dup = {mode:'combat', budget:{action:1}, options:[{id:'a',slot:'action',label:'Watch carefully'},{id:'b',slot:'action',label:'Watch carefully'}]};
assert.equal(TB.plans(dup, {}, {}).length, 1);
assert.equal(TB.plans(dup, {}, {'action:a':{status:'needs_step'},'action:b':{status:'needs_choice'}}).length,0);
assert.equal(TB.plans(dup, {}, {'action:a':{status:'not_here',reasons:['blocked']},'action:b':{status:'ok'}})[0].id,'b');
// Composite plans preserve ordinary legality: a defensive action plus a published escape route.
const bundleContext={actor:'aero',mode:'combat',budget:{action:1,bonus_action:1,movement_ft:30},visible:[{id:'foe',label:'Visible threat',hostile:true}],
 options:[{id:'dodge',label:'Dodge',slot:'action'}],movement:[{id:'hold',label:'Hold',feet:0},{id:'back',label:'Fall back to cover',feet:10}]};
const bundle=TB.plans(bundleContext, {}, {})[0];
assert.equal(bundle.support.id,'back');
const combo=T.emptyDecl(bundleContext);combo.actions=[{option:bundle.id}];combo.movement={option:bundle.support.id};
assert(T.validate(combo,bundleContext).legal);
const noMove={...bundleContext,budget:{...bundleContext.budget,movement_ft:0}};
assert.equal(TB.plans(noMove, {}, {})[0].support,null);
const privatePoison = {...c, hidden:{secret:'PRIVATE_POISON'}, whisper:{motive:'PRIVATE_MOTIVE'}};
assert(!JSON.stringify(TB.plans(privatePoison, {}, availability)).includes('PRIVATE_'));
// A public blocked option is never promoted by a style preference.
const blocked = Object.fromEntries(Object.keys(availability).map(k=>[k,{status:'not_here',reasons:['not available']} ]));
assert.equal(TB.plans(c, {style:'bold'}, blocked).length, 0);
const text = 'Keep the hound away while I ask Wick to stay close.';
const d = TB.apply(T.emptyDecl(c), {tb4custom:{action:text}});
assert.equal(d.tb4.custom[0].text, text);
assert(d.unmapped.includes(text));
// No primary slot can be recovered by changing presentation.
const illegal = T.emptyDecl(zero); illegal.actions = [{option:c.options.find(o=>o.slot==='action').id}];
assert(!T.validate(illegal, zero).legal);
console.log('M11 pure checks passed');
if (process.argv.includes('--pure')) process.exit(0);
const {chromium} = require('playwright');
const MOCK = fs.readFileSync(path.join(__dirname,'test_datapad_ui.cjs'),'utf8').match(/const MOCK = `([\s\S]*?)`;/)[1];
(async()=>{
 const browser=await chromium.launch();
 try {
  for(const width of [390,820]) {
   const ctx=await browser.newContext({viewport:{width,height:1180},hasTouch:true});
   const page=await ctx.newPage(), errors=[];page.on('pageerror',e=>errors.push(e.message));
   const st=structuredClone(state);st.features={tb4_builder:true};st.processor=null;
   await page.addInitScript(({mock,st})=>{window.__store={'view/state':st};eval(mock)},{mock:MOCK,st});
   await page.goto('file://'+path.resolve(process.argv[2]));await page.waitForSelector('#submitTurn');
   assert.equal(await page.locator('#mechanicsCatalog').getAttribute('open'),null);
   assert(await page.locator('#intentPlans').isVisible());
   const cards=page.locator('#intentPlans [data-tb4pick]');
   const first=cards.first();const pick=(await first.getAttribute('data-tb4pick')).split('|');
   await first.click();
   assert(await page.locator(`input[${/objects|reactions/.test(pick[0])?"data-c":"data-g"}="${pick[0]}"][value="${pick[1]}"]`).isChecked());
   assert.equal(await page.locator('#mechanicsCatalog').getAttribute('open'),null);
   await page.locator('#w_tb4_action').fill(text);await page.waitForTimeout(400);
   await page.locator('#mechanicsCatalog > summary').click();
   assert(await page.locator('#w_tb4_secondary').isVisible());
   await page.locator('#w_tb4_secondary').fill('Signal Wick to keep close');await page.waitForTimeout(400);
   await page.locator('[data-tb4style="bold"]').click();
   assert(await page.locator('#w_tb4_secondary').isVisible()); // rerender keeps disclosure
   assert.equal(await page.locator('#w_tb4_action').inputValue(),text);
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   // Fresh server context with zero slots: badges and recommendations must agree.
   await page.evaluate(()=>{const v=window.__store['view/state'];v.turn_context.context_id+='-zero';v.turn_context.budget={action:0,bonus_action:0,reaction:0,object_interaction:0,movement_ft:0};window.__notify();});
   await page.waitForTimeout(150);await page.waitForSelector('#submitTurn');
   assert((await page.locator('.composer > .budget').first().innerText()).includes('Action: 0 remaining'));
   assert.equal(await page.locator('#intentPlans [data-tb4pick]').count(),0);
   assert.deepEqual(errors,[]);await ctx.close();
  }
  console.log('M11 browser checks passed');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
