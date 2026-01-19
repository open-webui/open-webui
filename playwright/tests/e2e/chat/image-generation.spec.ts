import { test, expect } from '../../../src/fixtures/base-fixture';
import { describeLocalImage } from '../../../src/utils/openai';
import { Language } from '../../../src/pages/base.page';

test.describe('Feature: Image Generation', () => {
	test('user can generate images using dall-e-2', async ({
		adminPage,
		userPage,
		locale
	}, testInfo) => {
		test.setTimeout(240000);
		console.log('Testing: user can generate images using dall-e-2');

		// Enable image generation globally
		await adminPage.configureImageGeneration('dall-e-2', true);

		await userPage.goto('/');
		await userPage.toggleChatTool(userPage.getTranslation('Image'), true);

		await userPage.sendMessage(
			'Make a picture of the Easter Bunny.',
			true,
			userPage.getTranslation('Generating an image')
		);

		const imageElement = userPage.getLastImage();
		await expect(imageElement).toBeVisible({ timeout: 120000 });

		// Verify the screenshot with openAI
		const screenshotPath = './playwright-report/screenshots/image_gen.png';
		await userPage.page.screenshot({ path: screenshotPath });
		const description = await describeLocalImage(screenshotPath);

		await testInfo.attach('AI Description', {
			body: `Image description: ${description}`,
			contentType: 'text/plain'
		});

		await testInfo.attach('Screenshot', {
			path: screenshotPath,
			contentType: 'image/png'
		});

		// Ensure OpenAI didn't return an error string
		expect(description).not.toContain('error');
	});
});
