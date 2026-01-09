import { test as base } from '@playwright/test';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export type AuthWorkerFixtures = {
	authFiles: {
		admin: string;
		user: string;
		analyst: string;
		globalAnalyst: string;
	};
};

export const authFixture = base.extend<{}, AuthWorkerFixtures>({
	authFiles: [
		async ({}, use) => {
			const authDir = path.join(__dirname, '../../.auth');

			await use({
				admin: path.join(authDir, 'admin.json'),
				user: path.join(authDir, 'user.json'),
				analyst: path.join(authDir, 'analyst.json'),
				globalAnalyst: path.join(authDir, 'globalanalyst.json')
			});
		},
		{ scope: 'worker' }
	]
});
