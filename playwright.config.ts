import { defineConfig } from '@playwright/test';

export default defineConfig({
	testDir: './test/frontend',
	testMatch: '**/*.pw.ts',
	workers: 1,
	forbidOnly: !!process.env.CI,
	timeout: 60000,
	expect: { timeout: 15000 },
	use: {
		baseURL: process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:5177',
		browserName: 'chromium',
		viewport: { width: 1280, height: 900 },
		serviceWorkers: 'block',
		trace: 'retain-on-failure'
	},
	webServer: {
		command: 'npm exec -- vite --host 127.0.0.1 --port 5177 --strictPort',
		url: 'http://127.0.0.1:5177',
		reuseExistingServer: !process.env.CI,
		timeout: 120000,
		env: { WEBUI_BACKEND_URL: 'http://127.0.0.1:9' }
	}
});
