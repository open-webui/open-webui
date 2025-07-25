import { defineConfig } from '@hey-api/openapi-ts';

export default defineConfig({
	// Input: NENNA.ai OpenAPI specification
	input: 'https://api.nenna.ai/latest/openapi.json',

	// Output: Generated client in PII APIs directory
	output: 'src/lib/apis/pii/generated',

	// Plugins to enable
	plugins: [
		// Generate TypeScript types
		'@hey-api/typescript',

		// Generate SDK methods
		'@hey-api/sdk',

		// Generate fetch client
		'@hey-api/client-fetch'
	]
});
