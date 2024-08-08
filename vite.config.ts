import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import terser from '@rollup/plugin-terser';

// /** @type {import('vite').Plugin} */
// const viteServerConfig = {
// 	name: 'log-request-middleware',
// 	configureServer(server) {
// 		server.middlewares.use((req, res, next) => {
// 			res.setHeader('Access-Control-Allow-Origin', '*');
// 			res.setHeader('Access-Control-Allow-Methods', 'GET');
// 			res.setHeader('Cross-Origin-Opener-Policy', 'same-origin');
// 			res.setHeader('Cross-Origin-Embedder-Policy', 'require-corp');
// 			next();
// 		});
// 	}
// };


export default defineConfig({
	plugins: [sveltekit()],
	define: {
		APP_VERSION: JSON.stringify(process.env.npm_package_version),
		APP_BUILD_HASH: JSON.stringify(process.env.APP_BUILD_HASH || 'dev-build')
	},
	build: {
		sourcemap: true,  // 如果不需要sourcemap，可以改为 false
		minify: 'terser',
		rollupOptions: {
			plugins: [terser({
				compress: {
					drop_console: true, // 移除 console 语句
					drop_debugger: true // 移除 debugger 语句
				},
				mangle: {
					properties: {
						regex: /^_/, // 混淆以 _ 开头的私有属性
					},
				}
			})]
		}
	},
	worker: {
		format: 'es'
	}
});
