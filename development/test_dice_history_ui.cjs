const fs = require("fs");
const path = require("path");
const assert = require("assert/strict");
const { chromium } = require("playwright");
(async () => {
  const [html, directory] = process.argv.slice(2);
  const store = {};
  for (const file of fs.readdirSync(directory)) store["view/" + file.replace(/\.json$/, "")] = JSON.parse(fs.readFileSync(path.join(directory, file)));
  const original = fs.readFileSync(path.join(__dirname, "../campaigns/starwars_litrpg/ui/test_datapad_history.cjs"),"utf8");
  const mock = original.match(/const MOCK = `([\s\S]*?)`;/)[1];
  const browser = await chromium.launch(process.env.GENESIS_TEST_CHROMIUM ? {executablePath:process.env.GENESIS_TEST_CHROMIUM} : {});
  try {
    const page = await browser.newPage({viewport:{width:390,height:844}});
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    await page.addInitScript(({store,mock})=>{window.__store=store;eval(mock);},{store,mock});
    await page.goto("file://" + path.resolve(html));
    await page.locator('[data-t="journal"]').click();
    await page.locator('[data-older="dice_history"]').click();
    await page.waitForFunction(()=>document.body.textContent.includes("roll_history_one"));
    assert.match(await page.locator("body").textContent(), /1d20.*-2/);
    assert.equal((await page.locator("body").textContent()).includes("SECRET_CANARY"),false);
    assert.deepEqual(errors,[]);
    console.log("PASS mobile dice-history page loads the roll, escapes content and omits hidden data");
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
