import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
	testDir: 'playwright/tests',
	fullyParallel: true,
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 2 : 0,
	reporter: [['list']],
	use: {
		baseURL: process.env.BASE_URL || 'http://localhost:3000',
		trace: 'on-first-retry',
		screenshot: 'only-on-failure',
		video: 'retain-on-failure',
		headless: true
	},
	projects: [
		{
			name: 'chromium',
			use: { ...devices['Desktop Chrome'] }
		}
	],
	timeout: 60 * 1000
});
