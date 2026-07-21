// PHASE A — Playwright config. Runs the rendered acceptance suite against the
// live dev app (vite :1420 + api_bridge :8788, both started separately).
// Artifacts: HTML report -> e2e/report, traces/screenshots -> e2e/out.
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  outputDir: './e2e/out/artifacts',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [
    ['list'],
    ['html', { outputFolder: 'e2e/report', open: 'never' }],
    ['json', { outputFile: 'e2e/out/results.json' }],
  ],
  use: {
    baseURL: 'http://localhost:1420',
    headless: true,
    viewport: { width: 1600, height: 900 },
    trace: 'on',
    screenshot: 'on',
    video: 'retain-on-failure',
  },
});
