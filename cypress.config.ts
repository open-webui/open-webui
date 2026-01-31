import { defineConfig } from 'cypress';

export default defineConfig({
	e2e: {
		// Allow baseUrl to be overridden by CYPRESS_baseUrl environment variable
		baseUrl: process.env.CYPRESS_baseUrl || 'http://localhost:8080'
	},
	video: true,
	env: {
		// So RUN_CHILD_PROFILE_TESTS=1 or CYPRESS_RUN_CHILD_PROFILE_TESTS=1 skips registerAdmin in e2e.ts
		RUN_CHILD_PROFILE_TESTS:
			process.env.CYPRESS_RUN_CHILD_PROFILE_TESTS ?? process.env.RUN_CHILD_PROFILE_TESTS ?? false
	}
});
