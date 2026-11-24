// Mobile-first composer layout (CC-006): one screen, no document scroll, required controls always reachable,
// regions never overlap, at real phone / iPad / desktop sizes. Plays a real turn on the thin client (player token only).
// Screenshots go to $SHOT_DIR (default: a temp dir).
const { chromium, devices } = require("playwright");
const { spawn } = require("child_process"); const path = require("path"), fs = require("fs"), os = require("os");
let fails = 0; const ok = (c, n, x) => { console.log((c ? "ok " : "FAIL ") + n + (c ? "" : " " + JSON.stringify(x == null ? "" : x).slice(0, 300))); if (!c) fails++; };
const dir = fs.mkdtempSync(path.join(os.tmpdir(), "lay-")), port = 26000 + Math.floor(Math.random() * 2000);
const shots = process.env.SHOT_DIR || fs.mkdtempSync(path.join(os.tmpdir(), "shots-")); fs.mkdirSync(shots, { recursive: true });
const srv = spawn("python3", ["-B", path.join(__dirname, "../preview/serve_preview.py"), "--port", String(port)], { env: Object.assign({}, process.env, { GENESIS_ATOMIC_DIR: dir }), stdio: "ignore" });
const base = "http://127.0.0.1:" + port, G = (p, fn, a) => p.evaluate(fn, a);
const VIEWPORTS = [
  ["iphone-se", { viewport: { width: 320, height: 568 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 }],
  ["iphone-13", devices["iPhone 13"]],
  ["iphone-13-landscape", devices["iPhone 13 landscape"]],
  ["ipad-pro-11-portrait", { viewport: { width: 834, height: 1194 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 }],
  ["ipad-pro-11-landscape", { viewport: { width: 1194, height: 834 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 }],
  ["ipad-pro-12.9-portrait", { viewport: { width: 1024, height: 1366 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 }],
  ["ipad-pro-12.9-landscape", { viewport: { width: 1366, height: 1024 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 }],
  ["ipad-split-view", { viewport: { width: 507, height: 1024 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 }],
  ["desktop-1280", { viewport: { width: 1280, height: 720 } }],
  ["desktop-1920", { viewport: { width: 1920, height: 1080 } }],
];
async function ready(p) { await p.waitForFunction(() => window.__genesisPlay && window.__genesisPlay.view() && !window.__genesisPlay.busy(), null, { timeout: 20000 }); }
async function geometry(p) {
  return G(p, () => {
    const W = window.innerWidth, H = window.innerHeight, d = document.documentElement;
    const box = (el) => { if (!el) return null; const r = el.getBoundingClientRect(), cs = getComputedStyle(el); return r.width && r.height && cs.display !== "none" && cs.visibility !== "hidden" ? { x: r.left, y: r.top, r: r.right, b: r.bottom, id: el.id } : null; };
    const regions = ["zoneActions", "zoneScene", "zoneTurn", "checkpoint", "planSum"].map((id) => box(document.getElementById(id))).filter(Boolean);
    const dock = box(document.querySelector(".dock")); if (dock) regions.push(Object.assign(dock, { id: "dock" }));
    const overlaps = []; for (let i = 0; i < regions.length; i++) for (let j = i + 1; j < regions.length; j++) { const a = regions[i], b = regions[j];
      if (a.id === "planSum" || b.id === "planSum") continue; if (a.x < b.r - 1 && b.x < a.r - 1 && a.y < b.b - 1 && b.y < a.b - 1) overlaps.push(a.id + "×" + b.id); }
    const offscreen = regions.filter((r) => r.x < -1 || r.y < -1 || r.r > W + 1 || r.b > H + 1).map((r) => r.id);
    const small = [...document.querySelectorAll("button, summary, select")].filter((e) => { const r = e.getBoundingClientRect(); const cs = getComputedStyle(e); return r.width && r.height && cs.visibility !== "hidden" && (r.height < 43.5 || r.width < 43.5); }).map((e) => e.outerHTML.slice(0, 70));
    return { scrollY: d.scrollHeight - H, scrollX: d.scrollWidth - W, bodyScroll: document.body.scrollHeight - H, overlaps, offscreen, small };
  });
}
async function inView(p, sel) { return G(p, (s) => { const e = document.querySelector(s); if (!e) return false; const r = e.getBoundingClientRect(); return r.width > 0 && r.top >= -1 && r.left >= -1 && r.bottom <= window.innerHeight + 1 && r.right <= window.innerWidth + 1; }, sel); }
async function showCard(p, pid) {   // reach a card the way a player would: switch to the Actions tab / its category if needed
  if (!(await p.locator(`[data-pid="${pid}"]`).isVisible())) { const t = p.locator('.tabs [data-tab="actions"]'); if (await t.isVisible()) await t.click(); }
  const cat = await p.locator(`[data-pid="${pid}"]`).getAttribute("data-cat").catch(() => null);
  if (cat && !(await p.locator(`[data-pid="${pid}"]`).isVisible())) { const r = p.locator(`[data-rail="${cat}"]`); if (await r.count()) await r.click(); }
}
(async () => {
  for (let i = 0; i < 100; i++) { try { await fetch(base + "/healthz"); break; } catch (e) { await new Promise((r) => setTimeout(r, 150)); } }
  const browser = await chromium.launch();
  try {
    for (const [name, dev] of VIEWPORTS) {
      const ctx = await browser.newContext(dev), p = await ctx.newPage(), errs = []; p.on("pageerror", (e) => errs.push(e.message));
      await p.goto(base + "/play.html"); await ready(p);
      let g = await geometry(p);
      ok(g.scrollY <= 1 && g.scrollX <= 1 && g.bodyScroll <= 1, name + ": planning — no document scroll", g);
      ok(g.overlaps.length === 0, name + ": planning — regions don't overlap", g.overlaps);
      ok(g.offscreen.length === 0, name + ": planning — no region clipped by the viewport", g.offscreen);
      ok(g.small.length === 0, name + ": planning — every control ≥ 44 px", g.small.slice(0, 3));
      ok(await inView(p, "#commit"), name + ": Commit is on screen");
      const zones = await G(p, () => ["zoneActions", "zoneScene", "zoneTurn"].map((id) => { const e = document.getElementById(id), r = e.getBoundingClientRect(); return getComputedStyle(e).display === "none" || !r.width ? null : [id, Math.round(r.left)]; }).filter(Boolean));
      const W = (dev.viewport || {}).width, want = W >= 1100 ? 3 : W >= 700 ? 2 : 1;
      ok(zones.length === want && zones.every((z, i) => !i || z[1] > zones[i - 1][1]), name + ": " + want + " zone(s) side by side for a " + W + " px wide screen", zones);
      await showCard(p, "move"); ok(await p.locator('[data-pid="move"]').isVisible(), name + ": abilities reachable");
      await p.screenshot({ path: path.join(shots, name + "-1-plan.png") });
      // build and commit a real turn (close the distance, then strike)
      for (const pid of ["move", "saber_strike"]) { await showCard(p, pid); await p.locator(`[data-pid="${pid}"]`).click(); if (await p.locator("#dlg[open]").count()) await p.locator("#dlgBody [data-o]").first().click(); await ready(p); }
      ok(await inView(p, "#commit") && !(await p.locator("#commit").isDisabled()), name + ": a legal plan can be committed without scrolling");
      ok(/Legal/.test(await p.locator("#planSum").innerText()), name + ": the dock states the server's legality verdict");
      await p.screenshot({ path: path.join(shots, name + "-2-planned.png") });
      await p.locator("#commit").click(); if (await p.locator("#cYes").count()) await p.locator("#cYes").click();
      await p.waitForFunction(() => { const v = window.__genesisPlay.view(); return !window.__genesisPlay.busy() && ["roll", "decision", "over", "plan"].includes(v.checkpoint.kind); }, null, { timeout: 20000 });
      const k = await G(p, () => window.__genesisPlay.view().checkpoint.kind);
      if (k === "roll") {
        ok(await inView(p, "#rollBtn"), name + ": the Roll button is on screen without scrolling (priority over browsing)");
        g = await geometry(p); ok(g.scrollY <= 1 && g.overlaps.length === 0 && g.offscreen.length === 0, name + ": roll checkpoint — single screen, nothing overlapping or clipped", g);
        const cpt = await p.locator("#checkpoint").innerText(); ok(!/\bnull\b|undefined|NaN/.test(cpt), name + ": the roll prompt has no null/undefined text", cpt);
        await p.screenshot({ path: path.join(shots, name + "-3-roll.png") });
        await p.locator("#rollBtn").click(); await ready(p);
      } else ok(true, name + ": (no roll was needed: " + k + ")");
      ok(errs.length === 0, name + ": no page errors", errs);
      await ctx.close();
    }
    // the on-screen keyboard / short viewport: shrink an iPhone viewport to ~half height
    const ctx = await browser.newContext(devices["iPhone 13"]), p = await ctx.newPage(); await p.goto(base + "/play.html"); await ready(p);
    await p.setViewportSize({ width: 390, height: 380 }); await p.waitForTimeout(150);
    const g = await geometry(p); ok(g.scrollY <= 1 && g.offscreen.length === 0 && (await inView(p, "#commit")), "short viewport (keyboard up): still one screen, Commit reachable", g);
    await ctx.close();
  } catch (e) { fails++; console.log("FAIL exception", e.stack); }
  finally { srv.kill(); await browser.close(); }
  console.log("screenshots: " + shots);
  console.log(fails ? fails + " FAILED" : "all passed"); process.exit(fails ? 1 : 0);
})();
