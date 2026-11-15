import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  workers: 1,
  fullyParallel: false,
  reporter: 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://127.0.0.1:58002',
    // Tokens and source text must not enter traces, videos or automatic screenshots.
    trace: 'off',
    screenshot: 'off',
    video: 'off',
    browserName: 'chromium',
  },
});
