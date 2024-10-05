import { defineConfig } from 'cypress';

export default defineConfig({
	e2e: {
		baseUrl: 'http://[::1]:8080'
	},
	video: true
});
