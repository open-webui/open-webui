import { test, expect } from '../../../src/fixtures/base-fixture';
import { Language } from '../../../src/pages/base.page';

test.describe('Feature: Model Context Protocol (MCP)', () => {
	test.setTimeout(240000);

	test('MCP - Time Server', async ({ adminPage, userPage, locale }) => {
		// Admin Setup
		await test.step('Admin enables MCP API and verifies services', async () => {
			console.log('Testing: MCP - Time Server');
			await adminPage.configureMCP(true);
			await adminPage.verifyMCPServerStatus(
				adminPage.getTranslation('Time Server'),
				adminPage.getTranslation('running')
			);
			await adminPage.signOut();
		});

		/* // User - Time Tool Test
		await test.step('User can use MCP Time tool', async () => {
			await userPage.goto('/');
			await userPage.verifyPageLanguage(locale as Language);
			await userPage.toggleChatTool(userPage.getTranslation('MCP: Current Time'), true);
			await expect(userPage.page.locator('#chat-container')).toContainText(
				userPage.getTranslation('MCP: Current Time')
			);
			await userPage.sendMessage(
				'What is the time?',
				true,
				userPage.getTranslation('Consulting CrewAI agents...')
			);

			if (await userPage.isNetworkErrorPresent()) {
				console.log('Network error detected. Retrying...');
				await userPage.regenerateLastResponse();
			}

			// Verify that contains time
			await expect(userPage.responseMessages.last()).toContainText('time', {
				ignoreCase: true,
				timeout: 120000
			});
		}); */
	});

	test('MCP - News Headlines', async ({ adminPage, userPage, locale }) => {
		// Admin Setup
		await test.step('Admin enables MCP API and verifies services', async () => {
			console.log('Testing: MCP - News Headlines');
			await adminPage.configureMCP(true);
			await adminPage.verifyMCPServerStatus(
				adminPage.getTranslation('Time Server'),
				adminPage.getTranslation('running')
			);
			await adminPage.signOut();
		});

		/* // User - News Tool Test
		await test.step('User can use MCP News tool', async () => {
			await userPage.verifyPageLanguage(locale as Language);
			await userPage.toggleChatTool(userPage.getTranslation('MCP: News Headlines'), true);
			await expect(userPage.page.locator('#chat-container')).toContainText(
				userPage.getTranslation('MCP: News Headlines')
			);

			await userPage.sendMessage(
				'What are the current headlines?',
				true,
				userPage.getTranslation('Consulting CrewAI agents...')
			);

			await expect(userPage.responseMessages.last()).not.toContainText(
				'No recent articles found matching your criteria',
				{
					ignoreCase: true,
					timeout: 120000
				}
			);
		}); */
	});
});
