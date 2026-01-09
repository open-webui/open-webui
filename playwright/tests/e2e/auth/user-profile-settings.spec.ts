import { test, expect } from '../../../src/fixtures/base-fixture';
import { Language } from '../../../src/pages/base.page';

test.describe('Feature: User Settings', () => {
	test.setTimeout(180000);

	test('user can delete all chats', async ({ userPage, locale }, testInfo) => {
		console.log('Testing: user can delete all chats');
		await userPage.verifyPageLanguage(locale as Language);
		await userPage.navigateToUserSettings(userPage.t['Chats'] || 'Chats');

		await userPage.page
			.getByRole('button', { name: userPage.t['Delete All Chats'] || 'Delete All Chats' })
			.click();
		await userPage.page.getByRole('button', { name: userPage.t['Confirm'] || 'Confirm' }).click();
	});
});
