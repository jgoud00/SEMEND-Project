import { defineConfig } from '@playwright/test'
import path from 'node:path'

export default defineConfig({
  testDir: './tests',
  timeout: 60000,
  expect: { timeout: 15000 },
  workers: 1,
  reporter: [['list'], ['json', { outputFile: './playwright-report/browser-tests.json' }]],
  use: { baseURL: 'http://127.0.0.1:15173', viewport: { width: 1440, height: 1100 }, headless: true, trace: 'retain-on-failure' },
  webServer: [
    { command: '..\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --app-dir ../backend --host 127.0.0.1 --port 18000', url: 'http://127.0.0.1:18000/api/health', env: { FOREARMSENSE_OUTPUT_ROOT: path.resolve('test-results/backend-artifacts') }, reuseExistingServer: false, timeout: 60000 },
    { command: 'npm run dev -- --port 15173', url: 'http://127.0.0.1:15173', env: { FOREARMSENSE_API_TARGET: 'http://127.0.0.1:18000' }, reuseExistingServer: false, timeout: 30000 },
  ],
})
