import { BasePage, type Language } from './base.page';
import { type Page, type Locator, expect } from '@playwright/test';

export class AuthPage extends BasePage {
	emailInput!: Locator;
	passwordInput!: Locator;
	signInButton!: Locator;
	createAccountButton!: Locator;
	nameInput!: Locator;
	onboardingButton!: Locator;
	signOutButtonPendingUser!: Locator;
	readonly isFirstRunButton: Locator;

	constructor(page: Page, lang: Language = 'en-GB') {
		super(page, lang);

		this.isFirstRunButton = page.getByRole('button').filter({ hasText: /^$/ });
		this.updateLanguage(lang);
	}

	/**
	 * Override to update Chat-specific locators
	 * @param lang The new language to switch to ('en-GB' or 'fr-CA')
	 */
	override updateLanguage(lang: Language) {
		super.updateLanguage(lang);

		this.emailInput = this.page.getByRole('textbox', {
			name: this.t['Enter Your Email'] || 'Enter Your Email'
		});
		this.passwordInput = this.page.getByRole('textbox', {
			name: this.t['Enter Your Password'] || 'Enter Your Password'
		});
		this.signInButton = this.page.getByRole('button', { name: this.t['Sign in'] || 'Sign in' });
		this.createAccountButton = this.page.getByRole('button', {
			name: this.t['Create Admin Account'] || 'Create Admin Account'
		});
		this.nameInput = this.page.getByRole('textbox', {
			name: this.t['Enter Your Full Name'] || 'Enter Your Full Name'
		});
		this.onboardingButton = this.page.getByRole('button', {
			name: this.t["Okay, Let's Go!"] || "Okay, Let's Go!"
		});
		this.signOutButtonPendingUser = this.page.getByRole('button', {
			name: this.t['Sign Out'] || 'Sign Out'
		});
	}

	/**
	 * Perform the user login
	 * @param email The email address of the user.
	 * @param pass The password for the account.
	 */
	async login(email: string, pass: string) {
		await this.goto('/auth');
		await this.emailInput.fill(email);
		await this.passwordInput.fill(pass);
		await this.signInButton.click();

		await this.page.waitForURL('/');
		await expect(this.page.locator('body')).toBeVisible();

		// Handle "Ok, Let's Go!" onboarding popup
		if (await this.onboardingButton.isVisible({ timeout: 2000 })) {
			await this.onboardingButton.click();
		}
	}

	/**
	 * Registers a new Admin account (first run only)
	 * @param name The name of the admin.
	 * @param email The email address of the admin.
	 * @param pass The password for the account.
	 */
	async registerAdmin(name: string, email: string, pass: string) {
		await this.nameInput.fill(name);
		await this.emailInput.fill(email);
		await this.passwordInput.fill(pass);
		await this.createAccountButton.click();

		// Handle "Ok, Let's Go!" onboarding popup
		await this.onboardingButton.waitFor({ state: 'visible', timeout: 5000 });
		await this.onboardingButton.click();
	}

	/**
	 * Signs the user out and verifies redirection to the auth page.
	 */
	async signOutPendingUser() {
		await this.signOutButtonPendingUser.click();
		await expect(this.page).toHaveURL(/\/auth/);
	}
}
