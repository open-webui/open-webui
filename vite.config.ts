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

	// Development optimizations
	server: {
		fs: {
			// Allow serving files from one level up to the project root
			allow: ['..']
		}
	},
	optimizeDeps: {
		include: [
			'@codemirror/lang-javascript',
			'@codemirror/lang-python',
			'@codemirror/language-data',
			'@codemirror/theme-one-dark',
			'marked',
			'katex',
			'highlight.js'
		],
		// Force pre-bundling of large dependencies
		force: process.env.NODE_ENV === 'development'
	},
	// Enable esbuild for faster builds in development
	esbuild: {
		pure: process.env.ENV === 'dev' ? [] : ['console.log', 'console.debug']
	}
});
