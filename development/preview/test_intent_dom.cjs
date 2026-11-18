// Functional DOM fallback when this executor cannot launch Chromium. This is NOT a visual/mobile browser test.
// npm install --prefix development/.qa/dom --ignore-scripts jsdom
// NODE_PATH="$PWD/development/.qa/dom/node_modules" node development/preview/test_intent_dom.cjs
const {JSDOM,VirtualConsole}=require('jsdom');
const fs=require('fs'),assert=require('node:assert/strict');
const page=fs.readFileSync('development/preview/out/index.html','utf8');
const wait=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 const errors=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
 const dom=new JSDOM(page,{url:'https://preview.example.test/',runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,
  beforeParse(w){w.scrollTo=()=>{};w.matchMedia=()=>({matches:false,addListener(){},addEventListener(){}});w.HTMLElement.prototype.scrollIntoView=function(){};}});
 try{
  await wait(600);const w=dom.window,d=w.document;
  const q=s=>{const e=d.querySelector(s);assert(e,s+' missing');return e;};
  const fill=(s,v)=>{const e=q(s);e.value=v;e.dispatchEvent(new w.Event('input',{bubbles:true}));};
  assert(q('#intentPlans'));assert(!q('#mechanicsCatalog').open);
  const first=q('#intentPlans [data-tb4pick]'),[group,id]=first.dataset.tb4pick.split('|');first.click();await wait(50);
  assert(q(`input[${/objects|reactions/.test(group)?"data-c":"data-g"}="${group}"][value="${id}"]`).checked);
  assert(!q('#mechanicsCatalog').open);
  fill('#w_tb4_action','Watch the door while I cover Wick.');await wait(350);
  q('#mechanicsCatalog').open=true;await wait(30);
  fill('#w_tb4_secondary','Signal Wick to keep close.');await wait(350);
  q('[data-tb4style="bold"]').click();await wait(50);
  assert(q('#mechanicsCatalog').open);
  assert.equal(q('#w_tb4_action').value,'Watch the door while I cover Wick.');
  // Clear the primary and submit a literal custom plan; only mock/local data may change.
  const clear=d.querySelector('#intentPlans [data-tb4pick="action|"]');if(clear)clear.click();await wait(50);
  assert(!q('#submitTurn').disabled);q('#submitTurn').click();await wait(700);
  const row=Object.entries(w.__store).find(([k])=>k.startsWith('actions/'))[1];
  assert.equal(row.campaign_id,'mobile-test-1');assert.equal(row.preview,true);
  assert.equal(row.declaration.tb4.custom.find(x=>x.category==='action').text,'Watch the door while I cover Wick.');
  assert(row.declaration.unmapped.includes('Signal Wick to keep close.'));
  assert(!errors.length,errors.join('\n'));
  // Zero-economy refresh uses a new context and the actual subscription/render path.
  const state=w.__store['view/state'];state.turn_context.context_id+='-zero';
  state.turn_context.budget={action:0,bonus_action:0,reaction:0,object_interaction:0,movement_ft:0};w.__notify();await wait(100);
  assert(q('.composer > .budget').textContent.includes('Action: 0 remaining'));
  assert.equal(d.querySelectorAll('#intentPlans [data-tb4pick]').length,0);
  assert(!w.__lastValidation.crashed);
  console.log('M11 DOM: collapsed catalog, choose/edit/combine, style/disclosure persistence, immutable mock submission, zero-budget refresh passed');
 }finally{dom.window.close()}
})().catch(e=>{console.error(e);process.exit(1)});
