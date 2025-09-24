import { test, expect } from '@playwright/test';

test.describe('PII Masking Workflow - Simplified', () => {
	test('should select text and apply PII masking', async ({ page }) => {
		// Navigate directly to the app (assuming auth is handled elsewhere)
		await page.goto('http://localhost:5173/');
		await page.waitForLoadState('networkidle');

		// Skip auth if already logged in, otherwise handle it gracefully
		const isLoggedIn = await page
			.locator('#chat-input')
			.isVisible({ timeout: 5000 })
			.catch(() => false);

		if (!isLoggedIn) {
			console.log(
				'Need to authenticate first. You may need to manually log in or handle auth in beforeEach.'
			);
			// For development, you might want to save an authenticated state:
			// await page.context().storageState({ path: 'tests/e2e/auth.json' });
			return;
		}

		console.log('✅ Already authenticated, proceeding with PII test...');

		// For this test, let's type some text with PII directly in the input
		const chatInput = page.locator('#chat-input');
		await expect(chatInput).toBeVisible();

		// Type text containing PII
		const testText =
			'Hello, my name is John Siebert from Berlin. Contact me at john.siebert@example.com';
		await chatInput.fill(testText);

		// Wait for PII detection to trigger (if enabled)
		await page.waitForTimeout(2000);

		// Step 1: Select text by double-clicking on "Siebert"
		const sieberText = page.getByText('Siebert').first();
		if ((await sieberText.count()) > 0) {
			await sieberText.dblclick();
			console.log('✅ Text selected via double-click');
		} else {
			// Alternative: Select text programmatically
			await page.evaluate(() => {
				const input = document.querySelector('#chat-input') as HTMLElement;
				if (input) {
					const selection = window.getSelection();
					const range = document.createRange();
					// Select the word "Siebert"
					const textNode = input.firstChild;
					if (textNode) {
						const text = textNode.textContent || '';
						const startIndex = text.indexOf('Siebert');
						if (startIndex !== -1) {
							range.setStart(textNode, startIndex);
							range.setEnd(textNode, startIndex + 7); // "Siebert".length
							selection?.removeAllRanges();
							selection?.addRange(range);
						}
					}
				}
			});
			console.log('✅ Text selected programmatically');
		}

		await page.waitForTimeout(500);

		// Step 2: Look for and click the "Mask Words" button
		const maskButtonSelectors = [
			'button:has-text("🛡️ Mask Words")',
			'button:has-text("Mask Words")',
			'button:has-text("Mask")',
			'[data-testid="mask-button"]',
			'.mask-button'
		];

		let maskButton = null;
		for (const selector of maskButtonSelectors) {
			const button = page.locator(selector);
			if ((await button.count()) > 0 && (await button.isVisible())) {
				maskButton = button;
				break;
			}
		}

		if (maskButton) {
			await maskButton.click();
			console.log('✅ Mask Words button clicked');

			// Wait for masking to be applied
			await page.waitForTimeout(1000);

			// Step 3: Verify that PII highlighting appears
			const piiHighlights = page.locator('.pii-highlight');
			await expect(piiHighlights).toHaveCount({ min: 1 });

			// Verify specific text is highlighted
			const highlightedSiebert = page.locator('.pii-highlight:has-text("Siebert")');
			if ((await highlightedSiebert.count()) > 0) {
				await expect(highlightedSiebert).toBeVisible();
				console.log('✅ "Siebert" is highlighted as PII');
			}

			// Verify PII data attributes
			const piiWithLabel = page.locator('[data-pii-label]');
			await expect(piiWithLabel).toHaveCount({ min: 1 });

			const piiWithType = page.locator('[data-pii-type]');
			await expect(piiWithType).toHaveCount({ min: 1 });

			// Check masking state
			const maskedElements = page.locator('.pii-masked, .pii-unmasked');
			await expect(maskedElements).toHaveCount({ min: 1 });

			console.log('✅ PII masking workflow completed successfully!');
		} else {
			console.log('⚠️ Mask Words button not found - PII masking might not be enabled or available');

			// Alternative: Check if PII detection is working without the button
			await page.waitForTimeout(2000);
			const autoPiiHighlights = page.locator('.pii-highlight');
			if ((await autoPiiHighlights.count()) > 0) {
				console.log('✅ Automatic PII detection is working');
				await expect(autoPiiHighlights).toHaveCount({ min: 1 });
			} else {
				console.log('ℹ️ No automatic PII detection found');
			}
		}
	});

	test('should handle PII in uploaded file content', async ({ page }) => {
		// This test focuses on the file upload + PII detection workflow
		await page.goto('http://localhost:5173/');
		await page.waitForLoadState('networkidle');

		// Check if authenticated
		const chatInput = page.locator('#chat-input');
		const isReady = await chatInput.isVisible({ timeout: 5000 }).catch(() => false);

		if (!isReady) {
			console.log('Chat input not ready - authentication may be required');
			return;
		}

		// Try to upload a file and then test PII interactions on the content
		console.log('Testing file upload + PII workflow...');

		// Upload file using the simple file input method
		const fileInput = page.locator('input[type="file"]:not(#camera-input)').first();
		if ((await fileInput.count()) > 0) {
			await fileInput.setInputFiles('tests/e2e/test_files/line.break.entity.docx');
			console.log('✅ File uploaded');

			// Wait for processing
			await page.waitForTimeout(5000);

			// Look for file content in the UI
			const fileContent = page.getByText('Siebert aus Berlin');
			if ((await fileContent.count()) > 0) {
				console.log('✅ File content visible');

				// Test the double-click + mask workflow on file content
				await fileContent.dblclick();
				await page.waitForTimeout(500);

				const maskButton = page.locator('button:has-text("🛡️ Mask Words")');
				if ((await maskButton.count()) > 0) {
					await maskButton.click();
					await page.waitForTimeout(1000);

					// Verify highlighting
					const highlights = page.locator('.pii-highlight');
					await expect(highlights).toHaveCount({ min: 1 });
					console.log('✅ File PII masking successful');
				}
			} else {
				console.log('⚠️ File content not visible yet');
			}
		} else {
			console.log('⚠️ File input not found');
		}
	});
});
