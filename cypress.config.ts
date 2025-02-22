import { defineConfig } from 'cypress';

export default defineConfig({
	e2e: {
		// 건우 로컬 백앤드 서버 연결
		// baseUrl: 'http://10.89.101.205:8080'
		baseUrl: 'http://localhost:8080'
	},
	video: true
});
