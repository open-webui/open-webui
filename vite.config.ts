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
	esbuild: {
		pure: process.env.ENV === 'dev' ? [] : ['console.log', 'console.debug']
	},
	server: {
		host: process.env.VITE_HOST || 'localhost',
		port: 5173,
		strictPort: true,
		hmr: {
			port: 5173,
			host: 'localhost'
		},
		// API proxy for Docker development
		proxy: process.env.DOCKER_DEV === 'true' ? {
			'/api': {
				target: 'http://backend-dev:8080',
				changeOrigin: true,
				secure: false
			},
			'/static': {
				target: 'http://backend-dev:8080',
				changeOrigin: true,
				secure: false
			},
			'/socket.io': {
				target: 'http://backend-dev:8080',
				changeOrigin: true,
				secure: false,
				ws: true
			}
		} : {}
	}
});
