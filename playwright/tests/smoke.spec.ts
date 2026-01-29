import { test, expect } from '@playwright/test';

test('basic smoke test', async ({ page }) => {
	await page.goto('/');

	await expect(page).toHaveTitle(/Open WebUI|Welcome/);

	const heading = page.getByRole('heading', { name: /Welcome|Open WebUI/i });
	await expect(heading).toBeVisible();
});
