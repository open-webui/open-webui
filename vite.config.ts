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
	server: {
		proxy: {
			'/api': {
				target: 'http://localhost:8080',
				changeOrigin: true,
				secure: false
			},
			'/ollama': {
				target: 'http://localhost:8080',
				changeOrigin: true,
				secure: false
			},
			'/openai': {
				target: 'http://localhost:8080',
				changeOrigin: true,
				secure: false
			},
			'/ws': {
				target: 'http://localhost:8080',
				changeOrigin: true,
				secure: false,
				ws: true
			}
		}
	},
	define: {
		APP_VERSION: JSON.stringify(process.env.npm_package_version),
		APP_BUILD_HASH: JSON.stringify(process.env.APP_BUILD_HASH || 'dev-build')
	},
	build: {
		sourcemap: false, // Disable sourcemaps to reduce memory usage
		chunkSizeWarningLimit: 1000
	},
	worker: {
		format: 'es'
	},
	esbuild: {
		pure: ['console.log', 'console.debug']
	},
	optimizeDeps: {
		// Exclude large dependencies from pre-bundling
		exclude: ['@mediapipe/tasks-vision', 'pyodide']
	}
});
