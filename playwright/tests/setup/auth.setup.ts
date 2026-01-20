import { test as setup, type Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { AuthPage } from '../../src/pages/auth.page';
import { AdminPage } from '../../src/pages/admin.page';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// --- Paths & Data ---
const authDir = path.join(__dirname, '../../.auth');
const usersFile = path.join(__dirname, '../../src/test-data/users.json');
const usersData = JSON.parse(fs.readFileSync(usersFile, 'utf-8'));

const adminUser = usersData.users.find((u: any) => u.username === 'admin');
const standardUsers = usersData.users.filter((u: any) => u.username !== 'admin');

setup('global setup: seed data & authenticate', async ({ page }) => {
	const authPage = new AuthPage(page);
	const adminPage = new AdminPage(page);

	await authPage.goto('/auth');
	const isFirstRun = await authPage.isFirstRunButton.isVisible();

	if (!isFirstRun) {
		console.log('CanChat already initialized. Skipping Global Setup');
		return;
	}

	console.log('First run detected. Starting initialization...');
	await performAdminRegistration(page, authPage);
	await seedUserAccounts(page, adminPage);
	await saveAuthState(page, 'admin.json');

	// Make one model visible
	await adminPage.navigateToAdminSettings('Settings', 'Connections'); //temporary
	await adminPage.openModelSettings('chatgpt-4o-');
	await adminPage.updateModelDescription({
		en: 'English Description',
		fr: 'French Description'
	});
	await adminPage.updateModelVisibility(adminPage.getTranslation('public'));
	await adminPage.saveModelSettings();
	await adminPage.updateChatModel('chatgpt-4o-latest');
	await adminPage.setDefaultChatModel();
	await adminPage.signOut();

	await generateUserAuthFiles(page, authPage, adminPage);

	console.log('Global Setup Complete!');
});

async function performAdminRegistration(page: Page, authPage: AuthPage) {
	console.log('Registering Admin...');
	// Click the empty button to start setup
	await authPage.isFirstRunButton.click();
	await authPage.registerAdmin(adminUser.name, adminUser.email, adminUser.password);
}

async function seedUserAccounts(page: Page, adminPage: AdminPage) {
	console.log('Checking User Accounts...');
	await adminPage.navigateToAdminSettings(
		adminPage.getTranslation('Users & Access'),
		adminPage.getTranslation('Overview')
	);

	for (const user of standardUsers) {
		const userExists = await page.getByText(user.email).isVisible();

		if (!userExists) {
			console.log(`Creating user: ${user.username}`);
			await adminPage.createUser(user.name, user.role, user.email, user.password);
		}
	}
}

async function generateUserAuthFiles(page: Page, authPage: AuthPage, basePage: any) {
	const browser = page.context().browser();

	for (const user of standardUsers) {
		console.log(`Authenticating ${user.username}...`);

		// Use a fresh context for each user to prevent state leakage
		const context = await browser!.newContext();
		const userPage = await context.newPage();
		const userAuthPage = new AuthPage(userPage);

		await userAuthPage.goto('/auth');
		await userAuthPage.login(user.email, user.password);

		await saveAuthState(userPage, `${user.username}.json`);

		await context.close();
	}
}

async function saveAuthState(page: Page, fileName: string) {
	await page.context().storageState({ path: path.join(authDir, fileName) });
	console.log('Authentication state saved.');
}
