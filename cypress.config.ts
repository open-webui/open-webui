import { defineConfig } from 'cypress';

export default defineConfig({
	e2e: {
		baseUrl: 'http://localhost:8080'
	},
	video: true,
	env: {
		SKIP_OLLAMA_TESTS: 'false'
	}
});
