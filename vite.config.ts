import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

import { viteStaticCopy } from 'vite-plugin-static-copy';

export default defineConfig({
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
	},

	server: {
		proxy: {
			// forward API requests to the given backend
			'/api': {
				target: 'http://175.45.204.157:8080',
				changeOrigin: true,
				rewrite: (path: string) => path.replace(/^\/api/, '/api')
			},
			// forward websocket or socket requests if any
			'/socket': {
				target: 'ws://175.45.204.157:8080',
				ws: true,
				changeOrigin: true
			}
		}
	},
	esbuild: {
		pure: process.env.ENV === 'dev' ? [] : ['console.log', 'console.debug', 'console.error']
	}
});
