import { defineConfig, devices } from '@playwright/test';

const BASE_URL = process.env.BASE_URL ?? 'http://localhost:8080';

export default defineConfig({
	testDir: './tests/e2e',
	fullyParallel: true,
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 2 : 0,
	workers: process.env.CI ? 1 : undefined,
	reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
	use: {
		baseURL: BASE_URL,
		extraHTTPHeaders: { Accept: 'application/json' },
		trace: 'on-first-retry'
	},
	projects: [
		{ name: 'api', testMatch: '**/api/*.spec.ts' },
		{ name: 'ui', testMatch: '**/ui/*.spec.ts', use: { ...devices['Desktop Chrome'] } }
	]
});
