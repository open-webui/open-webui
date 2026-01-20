import { test, expect } from '../../../src/fixtures/base-fixture';
import { Language } from '../../../src/pages/base.page';

test.describe('Feature: Wiki Grounding', () => {
	test('Service Availability', async ({ adminPage, userPage, locale }, testInfo) => {
		console.log('Testing: Feature: Wiki Grounding');
		const timeout = parseInt(process.env.LONG_TIMEOUT as string) || 120_000;
		test.setTimeout(timeout);
		await adminPage.navigateToAdminSettings(
			adminPage.getTranslation('Settings'),
			adminPage.getTranslation('Grounding')
		);

		await userPage.goto('/');
		await userPage.toggleChatTool(userPage.getTranslation('Wiki Grounding'), true);
		await expect(userPage.page.locator('#chat-container')).toContainText(
			userPage.getTranslation('Wiki Grounding'),
			{
				timeout: 15000
			}
		);

		if (locale === 'fr-CA') {
			await userPage.sendMessage("Qui est l'actuel Premier ministre canadien?");
		} else {
			await userPage.sendMessage('Who is the current Canadian Prime Minister?');
		}
		await userPage.getChatStatusDescription('sources');
		const responseText = await userPage.getLastMessageText();

		await testInfo.attach('Results', {
			body: `Chat response: ${responseText}`,
			contentType: 'text/plain'
		});
	});
});
