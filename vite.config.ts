import path from 'path';
import { fileURLToPath } from 'url';

import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

import { viteStaticCopy } from 'vite-plugin-static-copy';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Get backend port from environment variable, default to 8080
const BACKEND_PORT = process.env.BACKEND_PORT || '8080';
const BACKEND_HOST = process.env.BACKEND_HOST || 'localhost';
const backendUrl = `http://${BACKEND_HOST}:${BACKEND_PORT}`;

export default defineConfig({
	resolve: {
		conditions: ['svelte', 'import', 'module', 'browser', 'default'],
		alias: {
			'svelte-confetti': path.resolve(__dirname, 'node_modules/svelte-confetti/dist/index.js'),
			paneforge: path.resolve(__dirname, 'node_modules/paneforge/dist/index.js'),
			'bits-ui': path.resolve(__dirname, 'node_modules/bits-ui/dist/index.js'),
			'@melt-ui/svelte': path.resolve(__dirname, 'node_modules/@melt-ui/svelte/dist/index.js')
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
	server: {
		proxy: {
			'/api': {
				target: backendUrl,
				changeOrigin: true,
				secure: false
			},
			'/ollama': {
				target: backendUrl,
				changeOrigin: true,
				secure: false
			},
			'/openai': {
				target: backendUrl,
				changeOrigin: true,
				secure: false
			},
			'/ws': {
				target: backendUrl,
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
