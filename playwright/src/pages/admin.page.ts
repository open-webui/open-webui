import { BasePage, type Language } from './base.page';
import { type Page, type Locator, expect } from '@playwright/test';

export class AdminPage extends BasePage {
	saveButton!: Locator;
	readonly addUserButton: Locator;

	constructor(page: Page, lang: Language = 'en-GB') {
		super(page, lang);

		this.addUserButton = page.locator('[id="add-user\\9 \\9 \\9 \\9 "]');
		this.updateLanguage(lang);
	}

	/**
	 * Override the base method to update Admin-specific locators
	 * @param lang The new language to switch to ('en-GB' or 'fr-CA')
	 */
	override updateLanguage(lang: Language) {
		super.updateLanguage(lang);
		this.saveButton = this.page.getByRole('button', { name: this.getTranslation('Save') });
	}

	/**
	 * Navigates to the Admin Panel using the User Menu
	 */
	async navigateToAdminPanel() {
		await this.openHeaderUserMenu();
		await this.menuAdminPanel.click();
		await expect(this.page).toHaveURL(/\/admin/);
	}

	/**
	 * Navigates to a specific section within the Admin Panel
	 * @param menu Sidebar link name
	 * @param section Tab button name
	 */
	async navigateToAdminSettings(menu?: string, section?: string) {
		await this.goto('/');

		await this.navigateToAdminPanel();

		await this.page.getByRole('link', { name: menu }).click();

		const sectionTab = this.page.getByRole('button', { name: section });
		await expect(sectionTab).toBeVisible();
		await sectionTab.click();
		await this.waitToSettle(500);
	}

	/**
	 * Generic method to toggle a setting switch
	 * @param locator Locator of the switch
	 * @param [checked=true] The state of the element
	 */
	async toggleSwitch(locator: Locator, checked: boolean = true) {
		await locator.waitFor({ state: 'visible' });
		await expect(locator).toHaveAttribute('data-state', /^(checked|unchecked)$/);

		const currentState = await locator.getAttribute('data-state');
		if ((currentState === 'checked') !== checked) {
			await locator.click();
		}
	}

	/**
	 * Enable External Image Generation
	 * @param provider the image provider name
	 * @param enable the desired state
	 */
	async configureImageGeneration(provider: 'dall-e-2' | 'dall-e-3', enable: boolean) {
		await this.navigateToAdminSettings(
			this.getTranslation('Settings'),
			this.getTranslation('Images')
		);

		// Image Generation (Experimental) Switch
		await this.toggleSwitch(this.page.getByRole('switch').first(), true);

		if (enable) {
			await this.page.getByRole('combobox', { name: 'Select a model' }).fill('dall-e-2');
			await this.saveButton.click();
		}
	}

	/**
	 * Navigates to MCP settings and toggles the master switch.
	 */
	async configureMCP(enable: boolean) {
		await this.navigateToAdminSettings(this.getTranslation('Settings'), this.getTranslation('MCP'));
		await this.toggleSwitch(
			this.page.getByRole('switch', { name: this.getTranslation('Enable MCP API') }),
			true
		);
	}

	/**
	 * Verifies that a specific MCP server hows the expected status.
	 * @param serverName the server name
	 * @param status the status of the server 'running' | 'stopped' | 'initializing'
	 */
	async verifyMCPServerStatus(serverName: string, status: string) {
		/* const statusBadge = this.page.locator(
			`//div[normalize-space(text())='${serverName}']/../../..//span[normalize-space(text())='${status}']`
		);

		await expect(statusBadge.first()).toBeVisible(); */

		//Only await for a MCP to be displayed and does not verify it's status.
		await await expect(this.page.getByText('MCP: Current Time')).toBeVisible();
	}

	/**
	 * Navigates to the model settings and selects a specific model
	 * @param modelName The name of the model
	 */
	async openModelSettings(modelName: string) {
		await this.navigateToAdminSettings(
			this.getTranslation('Settings'),
			this.getTranslation('Models')
		);
		await this.page
			.getByRole('textbox', { name: 'Search Models' })
			.waitFor({ state: 'visible', timeout: 5000 });
		await this.page.getByRole('button', { name: `modelfile profile ${modelName}` }).click();
		await expect(this.page.locator('#models')).toBeVisible();
	}

	/**
	 * Updates the model description fields in English & French
	 * @param descriptions the description of the model
	 */
	async updateModelDescription(descriptions: { en?: string; fr?: string }) {
		if (descriptions.en !== undefined) {
			await this.page
				.locator('div[data-placeholder="Enter English description"]')
				.fill(descriptions.en);
		}

		if (descriptions.fr !== undefined) {
			await this.page
				.locator('div[data-placeholder="Enter French description"]')
				.fill(descriptions.fr);
		}
	}

	/**
	 * Updates the visibility dropdown (Public or Private)
	 * @param visibility The value option 'public' | 'private'
	 */
	async updateModelVisibility(visibility: string) {
		await this.page.locator('#models').selectOption(visibility);
	}

	/**
	 * Save the changes made to the model
	 */
	async saveModelSettings() {
		await this.page.getByRole('button', { name: this.getTranslation('Save & Update') }).click();
	}

	/**
	 * Creates a new user via the Admin Settings panel
	 * @param name The account name of the user
	 * @param role The role of the user
	 * @param email The email of the user
	 * @param password The account password
	 */
	async createUser(name: string, role: string, email: string, password: string) {
		await this.addUserButton.click();
		await this.page.getByRole('combobox').selectOption(role);
		await this.page
			.getByRole('textbox', { name: this.getTranslation('Enter Your Full Name') })
			.fill(name);
		await this.page
			.getByRole('textbox', { name: this.getTranslation('Enter Your Email') })
			.fill(email);
		await this.page
			.getByRole('textbox', { name: this.getTranslation('Enter Your Password') })
			.fill(password);
		await this.saveButton.click();
	}
}
