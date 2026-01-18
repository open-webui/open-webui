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
				target: 'https://hy-aitutor.hanyang.ac.kr',
				changeOrigin: true,
				rewrite: (path: string) => path.replace(/^\/api/, '/api')
			},
			// forward websocket (socket.io) requests - must use http target for ws upgrade
			'/ws/socket.io': {
				target: 'https://hy-aitutor.hanyang.ac.kr',
				ws: true,
				changeOrigin: true,
				secure: false
			},
			// forward other socket requests if any
			'/socket': {
				target: 'https://hy-aitutor.hanyang.ac.kr',
				ws: true,
				changeOrigin: true,
				secure: false
			}
		}
	},
	esbuild: {
		pure: process.env.ENV === 'dev' ? [] : ['console.log', 'console.debug', 'console.error']
	}
});
