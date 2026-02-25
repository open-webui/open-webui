import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import { viteStaticCopy } from 'vite-plugin-static-copy';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
	plugins: [
		tailwindcss(),
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
		// Performance optimizations
		target: 'esnext', // Skip transpilation for modern browsers
		sourcemap: false, // Disable sourcemaps in production (saves 5-10s)
		reportCompressedSize: false // Skip gzip analysis (saves 2-5s)
	},
	worker: {
		format: 'es'
	},
	// Optimize dependency pre-bundling for dev server
	optimizeDeps: {
		include: ['svelte', 'svelte/animate', 'svelte/transition', 'svelte/store']
	},
	// Narrow resolve extensions for faster resolution
	resolve: {
		extensions: ['.mjs', '.js', '.ts', '.svelte', '.json']
	}
});
