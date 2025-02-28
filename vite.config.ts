import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig, type UserConfig } from 'vite';

import { viteStaticCopy } from 'vite-plugin-static-copy';

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export default defineConfig(async (_): Promise<UserConfig> => ({
	server: {
		proxy: {
			'/api': {
				target: process.env.API_URL ?? 'localhost:8000',
				changeOrigin: true,
			}
		}
	},
	plugins: [
		sveltekit(),
		viteStaticCopy({
			targets: [
				{
					src: 'node_modules/onnxruntime-web/dist/*.jsep.*',
					dest: 'wasm'
				}
			]
		})
	],
	define: {
		APP_VERSION: JSON.stringify(process.env.npm_package_version),
		APP_BUILD_HASH: JSON.stringify(process.env.APP_BUILD_HASH || 'dev-build')
	},
	build: {
		sourcemap: true
	},
	worker: {
		format: 'es'
	}
}));
