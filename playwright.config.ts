import { defineConfig, devices } from '@playwright/test';

// Env variables
process.env.BASE_PATH = process.cwd();

// Long test timeout
process.env.LONG_TIMEOUT = '180000';

export default defineConfig({
	/* Global test timeout */
	timeout: 60000,
	/* Directory for test files */
	testDir: './playwright/tests',
	/* Run tests in files in parallel */
	fullyParallel: true,
	/* Fail the build on CI if you accidentally left test.only in the source code. */
	forbidOnly: !!process.env.CI,

	/* Retry on CI only */
	retries: process.env.CI ? 2 : 0,

	/* Opt out of parallel tests on CI. */
	//workers: process.env.CI ? 1 : undefined,
	workers: 6,
	/* Reporter to use. See https://playwright.dev/docs/test-reporters */
	reporter: [
		['html', { open: 'never' }],
		['json', { outputFile: './playwright-report/results.json' }]
	],
	/* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
	use: {
		/* Base URL to use in actions like `await page.goto('/')`. */
		baseURL: 'http://localhost:8080',

		/* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
		trace: 'on',

		// Capture screenshot after each test failure.
		screenshot: 'only-on-failure',

		// Record video only when retrying a test for the first time.
		video: 'on-first-retry'
	},
	expect: {
		timeout: 5000
	},
	/* webServer: {
		command: 'npm run start',
		url: 'http://localhost:8080',
		timeout: 120 * 1000,
		reuseExistingServer: true
	}, */
	/* Configure projects for major browsers */
	projects: [
		// --- Global Setup (Runs Once) ---
		{
			name: 'setup',
			testMatch: /.*\.setup\.ts/
		},

		// --- Tests Environment ---
		{
			name: 'chromium-en',
			use: {
				...devices['Desktop Chrome'],
				locale: 'en-GB'
			},
			testDir: './playwright/tests/e2e',
			dependencies: ['setup']
		},

		{
			name: 'chromium-fr',
			use: {
				...devices['Desktop Chrome'],
				locale: 'fr-CA'
			},
			testDir: './playwright/tests/e2e',
			dependencies: ['setup']
		},

		{
			name: 'firefox-en',
			use: {
				...devices['Desktop Firefox'],
				locale: 'en-GB'
			},
			testDir: './playwright/tests/e2e',
			dependencies: ['setup']
		},

		{
			name: 'firefox-fr',
			use: {
				...devices['Desktop Firefox'],
				locale: 'fr-CA'
			},
			testDir: './playwright/tests/e2e',
			dependencies: ['setup']
		}
	]
});
