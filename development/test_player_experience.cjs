const fs=require("fs"),path=require("path"),assert=require("assert/strict");
const {chromium}=require("playwright");
(async()=>{
  const store={};
  const folder=path.join(__dirname,".qa/ui/view");
  for(const file of fs.readdirSync(folder)) store["view/"+file.replace(/\.json$/,"")]=JSON.parse(fs.readFileSync(path.join(folder,file)));
  const source=fs.readFileSync(path.join(__dirname,"../campaigns/starwars_litrpg/ui/test_datapad_history.cjs"),"utf8");
  const mock=source.match(/const MOCK = `([\s\S]*?)`;/)[1].replace("delete: () =>", "update: d => { Object.assign(store[p],d); setTimeout(window.__notify,5); return Promise.resolve(); }, delete: () =>");
  const browser=await chromium.launch(process.env.GENESIS_TEST_CHROMIUM?{executablePath:process.env.GENESIS_TEST_CHROMIUM}:{});
  try {
    const page=await browser.newPage({viewport:{width:390,height:844}});
    page.setDefaultTimeout(8000);
    const errors=[];
    page.on("pageerror",error=>errors.push(error.message));
    await page.addInitScript(({store,mock})=>{window.__store=store;eval(mock);},{store,mock});
    await page.goto("file://"+path.resolve(__dirname,"../campaigns/starwars_litrpg/ui/genesis_datapad.html"));
    await page.waitForSelector("#colCenter .feed > div");
    assert.equal(await page.locator("#colCenter .feed > div").count(),1);
    assert.deepEqual(await page.evaluate(()=>window.__gets),[]);
    await page.locator('[data-t="journal"]').click();
    await page.locator("summary",{hasText:"Previous Turns"}).click();
    for(let i=0;i<10 && await page.locator('[data-older="feed"]').count();i++) {
      await page.locator('[data-older="feed"]').click();
      await page.waitForTimeout(80);
    }
    assert.equal(await page.locator('[data-older="feed"]').count(),0);
    await page.locator("summary",{hasText:"Chapters"}).click();
    if(await page.locator('[data-older="chapters"]').count()) await page.locator('[data-older="chapters"]').click();
    await page.waitForTimeout(80);
    assert.match(await page.locator("#colRight").textContent(),/Sources evt_/);
    await page.locator('[data-t="scene"]').click();
    await page.evaluate(()=>{
      const now=Date.now();
      window.__store["actions/testprogress"]={campaign_id:window.__store["view/state"].campaign_id,status:"processing",
        created_ms:now,processing:{run:"test",started_ms:now-10000,heartbeat_ms:now,lease_ms:3000,
          stage:"dice",stage_started_ms:now-1000,stages:{claimed:now-10000,context:now-8000,rules:now-4000,dice:now-1000}}};
      window.__notify();
    });
    await page.waitForTimeout(100);
    const progress=page.locator('#colCenter [data-turn-progress]');
    assert.match(await progress.textContent(),/Turn progress · Dice/);
    assert.match(await progress.textContent(),/Elapsed/);
    assert.equal((await progress.textContent()).includes("%"),false);
    await page.evaluate(()=>{
      const a=window.__store["actions/testprogress"];a.status="resolved";a.publication={status:"pending"};window.__notify();
    });
    await page.waitForTimeout(80);
    assert.match(await progress.textContent(),/publication pending/);
    if(await page.locator("#submitTurn").count()) assert.equal(await page.locator("#submitTurn").isDisabled(),true);
    await page.locator("summary",{hasText:"This isn’t what I meant"}).click();
    await page.locator("#contestCategory").selectOption("unfavorable");
    await page.locator("#contestText").fill("I disliked the valid result; please explain it.");
    await page.locator("#sendContest").click();
    await page.waitForTimeout(100);
    const disputes=await page.evaluate(()=>Object.entries(window.__store).filter(([k])=>k.startsWith("disputes/")));
    assert.equal(disputes.length,1);
    assert.equal(disputes[0][1].status,"awaiting_adjudication");
    assert.equal(disputes[0][1].category,"unfavorable");
    const context=JSON.parse(fs.readFileSync(path.join(__dirname,"../campaigns/starwars_litrpg/ui/fixtures/hask_r2_sequencer.json")));
    await page.evaluate(context=>{
      window.__store["actions/testprogress"].status="committed";
      window.__store["view/state"].turn_context=context;
      window.__notify();
    },context);
    await page.waitForTimeout(80);
    await page.locator("#requestPlanReview").check();
    await page.locator("#w_say").fill("I wait here.");
    await page.locator("#addSay").click();
    await page.locator("#submitTurn").click();
    await page.waitForTimeout(100);
    const submitted=await page.evaluate(()=>Object.entries(window.__store).find(([key,value])=>key.startsWith("actions/")&&value.request_plan_review));
    assert.ok(submitted);
    const original=JSON.stringify(submitted[1].declaration);
    await page.evaluate(([key,value])=>{
      window.__store[key]={...value,status:"needs_plan_approval",review_plan:{review_id:"worker-review",summary:["Say I wait here."]}};
      window.__notify();
    },submitted);
    await page.waitForTimeout(80);
    await page.locator("[data-approve-plan]").click();
    await page.waitForTimeout(80);
    const approval=await page.evaluate(key=>window.__store["plan_approvals/"+key.slice(8)],submitted[0]);
    assert.equal(approval.review_id,"worker-review");
    assert.equal(approval.decision,"approved");
    assert.equal(JSON.stringify((await page.evaluate(key=>window.__store[key],submitted[0])).declaration),original);
    await page.locator("[data-revise-plan]").click();
    await page.waitForTimeout(80);
    const revision=await page.evaluate(key=>window.__store["plan_revisions/"+key.slice(8)],submitted[0]);
    assert.equal(revision.review_id,"worker-review");
    assert.equal((await page.evaluate(key=>window.__store[key],submitted[0])).status,"needs_plan_approval");
    assert.deepEqual(errors,[]);
    console.log("PASS mobile Scene, paginated previous turns/chapters, real progress and contest request isolation");
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
