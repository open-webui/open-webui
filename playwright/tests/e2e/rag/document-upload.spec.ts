import { test, expect } from '../../../src/fixtures/base-fixture';
import { Language } from '../../../src/pages/base.page';
import * as path from 'path';
import * as fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test.describe('Feature: Document Upload and Retrieval', () => {
	test('Uploading a TXT Document', async ({ userPage, locale }, testInfo) => {
		console.log('Testing: Feature: Document Upload and Retrieval');
		const timeout = parseInt(process.env.LONG_TIMEOUT as string) || 120000;
		test.setTimeout(timeout);

		await userPage.goto('/');

		const relativePath = '../../../src/test-data/uploads/pg11.txt';
		const filePath = path.resolve(__dirname, relativePath);

		if (!fs.existsSync(filePath)) {
			throw new Error(`Test File not found at: ${filePath}`);
		}

		await userPage.uploadFile(filePath);

		await userPage.sendMessage('Summarize the uploaded document.');
		await expect(userPage.responseMessages.last()).toContainText('Gutenberg', { timeout: 60000 });

		const responseText = await userPage.getLastMessageText();
		await testInfo.attach('Results', {
			body: `Chat response: ${responseText}`,
			contentType: 'text/plain'
		});
	});
});
