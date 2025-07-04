import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

import { viteStaticCopy } from 'vite-plugin-static-copy';
import svelte from '@sveltejs/vite-plugin-svelte';

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
		watch: {
		  ignored: ['**/venv/**', '**/site-packages/**']
		},
		host: '0.0.0.0',
		port: 5173,
		allowedHosts: ['codeassist.axlrator.com', 'axlrator.com', 'www.axlrator.com'],
		hmr: {
			protocol: 'wss',
			host: 'axlrator.com'
		}
	},	
	preview: {
		host: '0.0.0.0',
		port: 4173,
		allowedHosts: ['axlrator.com', 'www.axlrator.com']
	},
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
		pure: ['console.log', 'console.debug']
	}
});
