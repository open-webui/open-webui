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
		sourcemap: true,
		rollupOptions: {
			external: (id) => {
				// Don't externalize raw imports (they need to be inlined)
				if (id.includes('?raw')) {
					return false;
				}

				// Externalize specific browser-only packages for SSR
				const externalPackages = [
					'vega',
					'vega-lite',
					'@joplin/turndown-plugin-gfm',
					'turndown',
					'turndown-plugin-gfm',
					'alpinejs'
				];

				// Check if id matches any external package or starts with @tiptap/
				return externalPackages.includes(id) || id.startsWith('@tiptap/') || id.startsWith('alpinejs/');
			}
		}
	},
	worker: {
		format: 'es'
	},
	esbuild: {
		pure: process.env.ENV === 'dev' ? [] : ['console.log', 'console.debug', 'console.error']
	},
	ssr: {
		noExternal: [],
		external: ['vega', 'vega-lite']
	},
	optimizeDeps: {
		exclude: ['vega', 'vega-lite']
	}
});
