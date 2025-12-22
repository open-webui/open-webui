import { defineConfig } from 'cypress';

export default defineConfig({
	e2e: {
		baseUrl: 'http://175.45.204.157:8080'
	},
	video: true
});
