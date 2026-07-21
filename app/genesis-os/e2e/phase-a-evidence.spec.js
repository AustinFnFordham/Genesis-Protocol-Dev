// Phase A evidence corrections (owner-required):
// 1. Rendered New Messages control with transcript scrolled upward + screenshot.
// 2. EXECUTED delayed-response campaign-switch race (not a code-guard claim).
import { test, expect } from '@playwright/test';

const APP = 'http://localhost:1420';
const API = 'http://localhost:8788/api/v1/gm';

async function mount(page, cid) {
  await page.evaluate(async (c) => {
    await fetch('http://localhost:8788/api/v1/gm/mount', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ campaign_id: c }),
    });
    await window.__genesis.getState().refreshGmRuntime();
    window.__genesis.getState().mountProjection?.();
  }, cid);
  await page.waitForTimeout(1500);
}

test('New Messages control renders while scrolled upward (screenshot)', async ({ page }) => {
  await page.goto(APP);
  await page.waitForTimeout(2500);
  await mount(page, 'meridian_reach');
  await page.evaluate(() => window.__genesis.getState().setEngagement('dialogue'));
  await page.waitForTimeout(800);
  // scroll the transcript to the top, then introduce a new entry via the
  // supported session-store path (shared projection, not component state)
  await page.evaluate(() => {
    const feeds = document.querySelectorAll('[data-region] div, div');
    // scroll the transcript container upward
    const g = window.__genesis.getState();
    // pad the feed so there is something to scroll through
    const pad = Array.from({ length: 24 }, (_, i) => ({ who: 'NARRATOR', text: `history line ${i} — the Reach remembers.` }));
    window.__genesis.setState({ gmFeed: [...pad, ...g.gmFeed] });
  });
  await page.waitForTimeout(400);
  const feed = page.locator('div').filter({ hasText: 'history line 0' }).last();
  await page.evaluate(() => {
    // find the scrollable transcript ancestor and scroll to top
    const el = [...document.querySelectorAll('div')].find((d) => d.scrollHeight > d.clientHeight + 100 && d.innerText.includes('history line 0'));
    if (el) el.scrollTop = 0;
  });
  await page.waitForTimeout(300);
  // new content arrives while scrolled up
  await page.evaluate(() => {
    const g = window.__genesis.getState();
    window.__genesis.setState({ gmFeed: [...g.gmFeed, { who: 'NARRATOR', text: 'NEW BEAT — arrives while reading history.' }] });
  });
  await page.waitForTimeout(600);
  const hasControl = await page.getByText(/new message/i).first().isVisible().catch(() => false);
  await page.screenshot({ path: 'e2e/out/9_transcript_scrolled_new_messages.png', fullPage: true });
  expect(hasControl).toBeTruthy();
});

test('EXECUTED race: delayed Meridian response cannot paint Shadows', async ({ page }) => {
  await page.goto(APP);
  await page.waitForTimeout(2500);
  // delay every meridian-epoch gm/state response by 4s
  let delayNext = false;
  await page.route('**/api/v1/gm/state', async (route) => {
    if (delayNext) { delayNext = false; await new Promise((r) => setTimeout(r, 4000)); }
    await route.continue();
  });
  await mount(page, 'meridian_reach');
  // begin a delayed Meridian operation
  delayNext = true;
  await page.evaluate(() => { window.__genesis.getState().refreshGmRuntime(); }); // in-flight, delayed 4s
  await page.waitForTimeout(300);
  // switch to Shadows while the Meridian response is still in flight
  await mount(page, 'shadows_of_empire');
  await page.evaluate(() => window.__genesis.getState().setEngagement('dialogue'));
  // allow the delayed Meridian response to complete
  await page.waitForTimeout(5000);
  const state = await page.evaluate(() => ({
    campaign: window.__genesis.getState().gmCampaign,
    mounted: window.__genesis.getState().gmRuntime?.mounted,
    anchor: document.body.innerText.includes('Aran Voss'),
    aeroLeak: document.body.innerText.split('CAMPAIGN')[0].includes('Aeleron'),
  }));
  expect(state.campaign).toBe('shadows_of_empire');
  expect(state.mounted).toBe('shadows_of_empire');
  expect(state.anchor).toBeTruthy();
  await page.screenshot({ path: 'e2e/out/10_race_shadows_not_painted_by_meridian.png', fullPage: true });
  // return to Meridian and confirm its own state intact
  await mount(page, 'meridian_reach');
  await page.waitForTimeout(1000);
  const back = await page.evaluate(() => window.__genesis.getState().gmRuntime?.mounted);
  expect(back).toBe('meridian_reach');
});
