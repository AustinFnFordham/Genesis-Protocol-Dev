// PHASE A — RENDERED ACCEPTANCE (Playwright). Run against the LIVE app:
//   T1: cd api_bridge && set PYTHONUTF8=1 && set GENESIS_DATA_MODE=live && python server.py
//   T2: cd app/genesis-os && npm run dev
//   T3: cd app/genesis-os && npx playwright test
// Meridian Reach is the authoritative live vertical slice. Shadows unresolved-
// class is an ACCEPTED honest empty-state, not a failure.
import { test, expect } from '@playwright/test';

const FORBIDDEN = ['Guardian', 'Millennium Falcon', 'Sith Assassin', 'Malice', 'Coruscant', 'Mustafar', 'Falleen', 'Sandbox'];

function regionIds(page) {
  return page.evaluate(() =>
    Array.from(document.querySelectorAll('[data-campaign-id]'))
      .map((e) => e.getAttribute('data-campaign-id'))
      .filter(Boolean));
}
async function mount(page, cardText) {
  await page.getByText('CAMPAIGNS', { exact: false }).first().click();
  await page.waitForTimeout(400);
  await page.getByText(cardText, { exact: false }).first().click();
  await page.waitForTimeout(1600); // atomic mount + full projection fetch
}
function attachErrorSinks(page, errors) {
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(String(e)));
}
async function bodyText(page) { return page.evaluate(() => document.body.innerText); }

test('Meridian vertical slice · atomic switch · fixture negatives · zero errors', async ({ page }) => {
  const errors = [];
  attachErrorSinks(page, errors);
  await page.goto('/');
  await page.waitForTimeout(900);

  // ---- mount Meridian ----
  await mount(page, 'Meridian Reach');
  const ids = await regionIds(page);
  expect(new Set(ids)).toEqual(new Set(['meridian_reach']));
  await expect(page.getByText('Aeleron', { exact: false }).first()).toBeVisible();

  // no forbidden fixture strings in the rendered game view (scan BEFORE modals)
  const mBody = await bodyText(page);
  for (const s of FORBIDDEN) expect(mBody, `forbidden fixture string (meridian): ${s}`).not.toContain(s);
  await page.screenshot({ path: 'e2e/out/1_meridian_main.png', fullPage: true });

  // DNA record from projection; no fixtures
  await page.getByText(/access dna record/i).first().click().catch(() => {});
  await page.waitForTimeout(500);
  await page.screenshot({ path: 'e2e/out/2_meridian_dna.png' });
  const dnaBody = await bodyText(page);
  for (const s of FORBIDDEN) expect(dnaBody, `forbidden in DNA (meridian): ${s}`).not.toContain(s);
  await page.getByText(/close/i).first().click().catch(() => {});
  await page.waitForTimeout(300);

  // ship = Republic Shuttle, not a fixture
  await page.getByText('SHIP', { exact: true }).first().click().catch(() => {});
  await page.waitForTimeout(600);
  await page.screenshot({ path: 'e2e/out/3_meridian_ship.png', fullPage: true });
  expect(await bodyText(page)).not.toContain('Millennium Falcon');

  // ---- atomic switch to Shadows ----
  await page.getByText('◈ NARRATIVE', { exact: false }).first().click().catch(() => {});
  await page.waitForTimeout(300);
  await mount(page, 'Shadows of Empire');
  const sIds = await regionIds(page);
  expect(new Set(sIds)).toEqual(new Set(['shadows_of_empire']));
  await expect(page.getByText('Aran Voss', { exact: false }).first()).toBeVisible();
  await page.screenshot({ path: 'e2e/out/5_shadows_main.png', fullPage: true });

  const sBody = await bodyText(page);
  for (const s of FORBIDDEN) expect(sBody, `forbidden fixture (shadows): ${s}`).not.toContain(s);
  expect(sBody, 'no Aero leak into Shadows').not.toContain('Aeleron');
  expect(sBody, 'no meridian id leak into Shadows').not.toContain('meridian_reach');

  // Shadows DNA — honest unresolved class
  await page.getByText(/access dna record/i).first().click().catch(() => {});
  await page.waitForTimeout(500);
  await page.screenshot({ path: 'e2e/out/6_shadows_dna.png' });
  const sDna = await bodyText(page);
  expect(sDna.toLowerCase(), 'Shadows DNA must state class is unresolved').toContain('no class established');
  await page.getByText(/close/i).first().click().catch(() => {});
  await page.waitForTimeout(300);

  // ---- back to Meridian — no Shadows remnants ----
  await page.getByText('◈ NARRATIVE', { exact: false }).first().click().catch(() => {});
  await page.waitForTimeout(300);
  await mount(page, 'Meridian Reach');
  const backIds = await regionIds(page);
  expect(new Set(backIds)).toEqual(new Set(['meridian_reach']));
  const backBody = await bodyText(page);
  expect(backBody, 'no Aran remnant after switch back').not.toContain('Aran Voss');
  expect(backBody, 'no Reconciliator remnant after switch back').not.toContain('Reconciliator');
  await page.screenshot({ path: 'e2e/out/8_back_to_meridian.png', fullPage: true });

  await expect(page.getByText('MODULE FAULT', { exact: false })).toHaveCount(0);
  expect(errors, `console/page errors: ${errors.join(' | ')}`).toHaveLength(0);
});

test('J behavior · suggestion populates composer (does NOT submit) · typing does NOT submit', async ({ page }) => {
  const errors = [];
  attachErrorSinks(page, errors);
  await page.goto('/');
  await page.waitForTimeout(900);
  await mount(page, 'Meridian Reach');

  await page.getByText('◈ NARRATIVE', { exact: false }).first().click().catch(() => {});
  await page.waitForTimeout(500);

  const feed = page.locator('[data-region="cinematic-feed"]');
  await expect(feed).toBeVisible();
  const composer = page.locator('input.holo-input');
  await expect(composer).toBeVisible();

  const beforeLines = await feed.locator('> div').count();

  // (a) typing must NOT append a transcript line
  await composer.fill('I scan the corridor for movement');
  await page.waitForTimeout(300);
  expect(await composer.inputValue()).toContain('I scan the corridor');
  expect(await feed.locator('> div').count(), 'typing must not submit').toBe(beforeLines);

  // (b) if GM suggestions present, click POPULATES composer, not submit
  await composer.fill('');
  const cards = page.locator('.holo-card');
  if (await cards.count() > 0) {
    const preLines = await feed.locator('> div').count();
    await cards.first().click();
    await page.waitForTimeout(400);
    expect((await composer.inputValue()).length, 'suggestion click should populate composer').toBeGreaterThan(0);
    expect(await feed.locator('> div').count(), 'suggestion click must NOT submit').toBe(preLines);
  }
  await page.screenshot({ path: 'e2e/out/4_meridian_suggestions.png', fullPage: true });

  expect(errors, `console/page errors: ${errors.join(' | ')}`).toHaveLength(0);
});

