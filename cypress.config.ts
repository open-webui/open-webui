import { defineConfig } from 'cypress';

export default defineConfig({
	e2e: {
		baseUrl: 'http://18.237.49.156:8080'
	},
	video: true
});
