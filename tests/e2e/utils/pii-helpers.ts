import { Page, expect } from '@playwright/test';

/**
 * Utility functions for PII testing in Playwright
 */

export class PiiTestHelpers {
	constructor(private page: Page) {}

	/**
	 * Enter a message in the chat input field
	 */
	async enterMessage(text: string): Promise<void> {
		// Use the TipTap/ProseMirror editor with id="chat-input"
		const messageInput = this.page.locator('#chat-input');

		await expect(messageInput).toBeVisible();

		// Use JavaScript to set content and trigger events properly for TipTap editor
		await this.page.evaluate((text) => {
			const chatInput = document.getElementById('chat-input');
			if (chatInput) {
				chatInput.focus();
				chatInput.textContent = text;

				// Trigger input events to make sure PII detection runs
				chatInput.dispatchEvent(new Event('input', { bubbles: true }));
				chatInput.dispatchEvent(new Event('change', { bubbles: true }));
			}
		}, text);

		await this.page.waitForTimeout(1500); // Wait for PII detection
	}

	/**
	 * Send the current message via Enter key
	 */
	async sendMessage(): Promise<void> {
		await this.page.keyboard.press('Enter');
		await this.page.waitForTimeout(2000); // Wait for message processing
	}

	/**
	 * Enter and send a message in one action
	 */
	async sendChatMessage(text: string): Promise<void> {
		await this.enterMessage(text);
		await this.sendMessage();
	}

	/**
	 * Toggle the PII masking button
	 */
	async toggleMasking(): Promise<void> {
		// The button contains both an icon and text, so we need flexible selectors
		const selectors = [
			'button:has-text("Maskieren")', // Standard text match
			'button >> text="Maskieren"', // Child text match
			'button:has(img) >> text="Maskieren"', // Button with icon and text
			'button:has([role="img"]) >> text="Maskieren"', // Alternative icon selector
			'button[title*="Maskieren"]', // Title attribute
			'button[aria-label*="Maskieren"]' // Aria label
		];

		let maskButton = null;

		// Try each selector
		for (const selector of selectors) {
			try {
				const button = this.page.locator(selector).first();
				if ((await button.count()) > 0) {
					await expect(button).toBeVisible({ timeout: 3000 });
					maskButton = button;
					break;
				}
			} catch (e) {
				// Continue to next selector
			}
		}

		// Final fallback: iterate through all buttons and check text content
		if (!maskButton) {
			const allButtons = this.page.locator('button');
			const count = await allButtons.count();

			for (let i = 0; i < count; i++) {
				const button = allButtons.nth(i);
				try {
					const textContent = await button.textContent();
					if (textContent && textContent.trim().includes('Maskieren')) {
						await expect(button).toBeVisible({ timeout: 1000 });
						maskButton = button;
						break;
					}
				} catch (e) {
					// Continue to next button
				}
			}
		}

		if (maskButton) {
			await maskButton.click();
			await this.page.waitForTimeout(500);
		} else {
			throw new Error('Maskieren button not found with any selector');
		}
	}

	/**
	 * Check if masking is currently enabled
	 */
	async isMaskingEnabled(): Promise<boolean> {
		const maskButton = this.page.getByRole('button', { name: 'Maskieren' });
		const isPressed = await maskButton.getAttribute('aria-pressed');
		return isPressed !== 'true'; // Inverted because when pressed, masking is OFF
	}

	/**
	 * Wait for an AI response containing specific text
	 */
	async waitForAiResponse(expectedText: string, timeout = 15000): Promise<void> {
		await expect(this.page.locator(`text=${expectedText}`)).toBeVisible({ timeout });
	}

	/**
	 * Check if PII highlighting elements are present
	 */
	async checkPiiHighlighting(): Promise<number> {
		const highlightedElements = this.page.locator(
			'.pii-highlight, [data-pii-label], [data-pii-type]'
		);
		return await highlightedElements.count();
	}

	/**
	 * Hover over a PII element and check for overlay
	 */
	async hoverOverPiiElement(): Promise<boolean> {
		const piiElements = this.page.locator('.pii-highlight, [data-pii-label], [data-pii-type]');
		const elementCount = await piiElements.count();

		if (elementCount > 0) {
			await piiElements.first().hover();
			await this.page.waitForTimeout(500);

			// Check if overlay appears
			const overlay = this.page.locator('.pii-overlay, .pii-hover-overlay');
			return (await overlay.count()) > 0;
		}

		return false;
	}

	/**
	 * Get console messages related to PII
	 */
	async getPiiConsoleMessages(): Promise<string[]> {
		return await this.page.evaluate(() => {
			// Extract PII-related console messages
			const messages: string[] = [];
			const originalLog = console.log;
			const originalError = console.error;

			// This is a simplified approach - in a real implementation,
			// you might want to capture console messages during test execution
			return messages;
		});
	}

	/**
	 * Verify message appears in chat
	 */
	async verifyMessageInChat(text: string): Promise<void> {
		await expect(this.page.locator(`text=${text}`)).toBeVisible();
	}

	/**
	 * Create a new chat/conversation
	 */
	async startNewChat(): Promise<void> {
		// Click on the new chat button if available
		const newChatButton = this.page.locator(
			'button[aria-label="New Chat"], button:has-text("New Chat")'
		);
		if ((await newChatButton.count()) > 0) {
			await newChatButton.click();
			await this.page.waitForTimeout(1000);
		}
	}

	/**
	 * Login as a specific user (if needed)
	 */
	async loginAs(email: string, password: string): Promise<void> {
		// Check if we're on the login page
		const signInText = this.page.locator('text=Sign in to Open WebUI');
		const isLoginPage = await signInText.isVisible();

		if (isLoginPage) {
			// Look for email and password fields
			const emailField = this.page.locator(
				'input[type="email"], input[name="email"], input[placeholder*="email" i]'
			);
			const passwordField = this.page.locator(
				'input[type="password"], input[name="password"], input[placeholder*="password" i]'
			);

			if ((await emailField.isVisible()) && (await passwordField.isVisible())) {
				await emailField.fill(email);
				await passwordField.fill(password);

				// Find and click the sign in button
				const signInButton = this.page.locator(
					'button[type="submit"], button:has-text("Sign in"), button:has-text("Login")'
				);
				await signInButton.click();

				// Wait for redirect to main app
				await this.page.waitForLoadState('networkidle');
			}
		}
	}

	/**
	 * Check if user is logged in
	 */
	async isLoggedIn(): Promise<boolean> {
		// Check for elements that indicate the user is logged in
		const userMenu = this.page.getByRole('button', { name: 'Open User Profile Menu' });
		return (await userMenu.count()) > 0;
	}

	/**
	 * Clear chat history or reset state
	 */
	async clearChatHistory(): Promise<void> {
		// Implementation would depend on the application's UI for clearing chat
		// This might involve going to settings or using a clear button
	}
}

/**
 * Common PII test data for consistent testing
 */
export const PII_TEST_DATA = {
	GERMAN_PERSON_LOCATION: 'Max F aus Berlin.',
	FULL_NAME_LOCATION: 'Mein Name ist Sarah Schmidt und ich wohne in München.',
	DOCTOR_HOSPITAL: 'Ich bin Dr. Maria Rodriguez aus Barcelona.',
	PROFESSIONAL_INFO: 'Anna Müller arbeitet bei der Deutschen Bank in Frankfurt.',
	EMAIL_PHONE: 'Kontaktieren Sie mich unter max.mustermann@email.de oder 0123-456789.',

	// Expected masked patterns (these would need to be updated based on actual API behavior)
	EXPECTED_MASKS: {
		PERSON: '[{PERSON_1}]',
		LOCATION: '[{LOCATION_1}]',
		EMAIL: '[{EMAIL_1}]',
		PHONE: '[{PHONE_1}]'
	}
};

/**
 * Test scenarios for comprehensive PII testing
 */
export const PII_TEST_SCENARIOS = [
	{
		name: 'Basic German PII',
		input: PII_TEST_DATA.GERMAN_PERSON_LOCATION,
		expectedEntities: ['PERSON', 'LOCATION'],
		description: 'Tests detection of German name and location'
	},
	{
		name: 'Full identity with location',
		input: PII_TEST_DATA.FULL_NAME_LOCATION,
		expectedEntities: ['PERSON', 'LOCATION'],
		description: 'Tests full name and city detection'
	},
	{
		name: 'Professional title and location',
		input: PII_TEST_DATA.DOCTOR_HOSPITAL,
		expectedEntities: ['PERSON', 'LOCATION'],
		description: 'Tests professional titles and international locations'
	},
	{
		name: 'Contact information',
		input: PII_TEST_DATA.EMAIL_PHONE,
		expectedEntities: ['EMAIL', 'PHONE'],
		description: 'Tests email and phone number detection'
	}
];
