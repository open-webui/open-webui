import { BasePage, type Language } from './base.page';
import { type Page, type Locator, expect } from '@playwright/test';

export class ChatPage extends BasePage {
	readonly messageInput: Locator;
	sendButton!: Locator;
	stopGenerationButton!: Locator;
	readonly regenerateButton: Locator;
	readonly responseMessages: Locator;
	readonly responseSelector = '#response-content-container';
	chatStatusDescription!: Locator;

	constructor(page: Page, lang: Language = 'en-GB') {
		super(page, lang);

		this.messageInput = page.locator('#chat-input');
		this.regenerateButton = page.locator('div:nth-child(8) > .visible');
		this.responseMessages = page.locator('#response-content-container');
		this.responseSelector = '#response-content-container';
		this.chatStatusDescription = page.locator('.status-description');

		this.updateLanguage(lang);
	}

	/**
	 * Override to update Chat-specific locators
	 * @param lang The new language to switch to ('en-GB' or 'fr-CA')
	 */
	override updateLanguage(lang: Language) {
		super.updateLanguage(lang);

		this.sendButton = this.page.getByRole('button', {
			name: this.t['Send message'] || 'Send message'
		});
		this.stopGenerationButton = this.page.getByRole('button', { name: this.t['Stop'] || 'Stop' });
	}

	/**
	 * Starts a new chat session
	 */
	async newChat() {
		await this.toggleSidebar(true);
		await this.sidebarNewChatButton.click();
		await expect(this.messageInput).toBeVisible();
	}

	/**
	 * Sends a message and waits for the response generation
	 */
	async sendMessage(text: string, waitForReply: boolean = true, idleMessage: string = '') {
		await expect(this.messageInput).toBeVisible();

		await this.messageInput.fill(text);
		await expect(this.sendButton).toBeEnabled();
		await this.sendButton.click();

		if (waitForReply) {
			await this.waitForGeneration(idleMessage);
		}
	}

	/**
	 * Waits for the response to complete
	 */
	async waitForGeneration(idleMessage: string = '') {
		const selector = this.responseSelector;
		await this.page.waitForSelector(selector, { state: 'visible' });

		await this.page.waitForFunction(
			({ selector, idleMessage }) => {
				const el = document.querySelector(selector);
				if (!el) return false;
				const text = el.textContent?.trim() || '';
				return text.length > 0 && (idleMessage.length === 0 || !text.includes(idleMessage));
			},
			{ selector, idleMessage },
			{ timeout: 180000 }
		);

		await this.waitToSettle(1500);
	}

	/**
	 * Retrieves the chat status description displayed above the answer
	 * Example is wiki grounding "Enhanced with 5 ressources"
	 */
	async getChatStatusDescription(status: string) {
		await expect(this.chatStatusDescription).toContainText(status, { timeout: 60000 });
	}

	/**
	 * Retrieves the text content of the most recent chat bubble
	 */
	async getLastMessageText(): Promise<string> {
		await expect(this.responseMessages.last()).toBeVisible();
		return await this.responseMessages.last().innerText();
	}

	/**
	 * Triggers regeneration of the last AI response
	 */
	async regenerateLastResponse() {
		await this.regenerateButton.click();
		await this.waitForGeneration();
	}

	/**
	 * Checks if the "Network Problem" error is visible
	 */
	async isNetworkErrorPresent(): Promise<boolean> {
		// Scoped to the messages container to avoid false positives elsewhere
		return await this.responseMessages.getByText('Network Problem').isVisible();
	}

	/**
	 * Opens the 'More' menu and toggles a specific tool/capability
	 * @param toolName The name of the button in the menu
	 * @param enable Desired state (true/false)
	 */
	async toggleChatTool(toolName: string, enable: boolean) {
		await this.page.getByLabel('More').click();
		const toolButton = this.page.getByRole('menuitem', { name: toolName });
		const toolSwitch = toolButton.getByRole('switch');

		await expect(toolButton).toBeVisible();

		const isChecked = await toolSwitch.isChecked();
		if (isChecked !== enable) {
			await toolSwitch.click();
			await expect(toolSwitch).toBeChecked({ checked: enable });
		}

		await this.page.keyboard.press('Escape');
	}

	/**
	 * Uploads a file via the 'More' menu
	 * @param filePath Path to the file
	 */
	async uploadFile(filePath: string) {
		const fileChooserPromise = this.page.waitForEvent('filechooser');

		await this.page.getByLabel('More').click();
		await this.page.getByText(this.getTranslation('Upload Files')).click();

		const fileChooser = await fileChooserPromise;
		await fileChooser.setFiles(filePath);

		await this.page
			.locator('li')
			.filter({ hasText: this.getTranslation('File uploaded successfully') })
			.waitFor({ state: 'visible', timeout: 180000 });
		await this.page
			.locator('li', { hasText: this.getTranslation('File uploaded successfully') })
			.waitFor({
				state: 'detached',
				timeout: 30000
			});
	}

	/**
	 * Returns the locator for the last generated image in the chat
	 */
	getLastImage() {
		return this.page.getByRole('button', { name: 'Generated Image' }).last();
	}
}
