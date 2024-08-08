import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import obfuscator from 'vite-plugin-obfuscator';

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
	plugins: [
		// 集成 SvelteKit
		sveltekit(),
		// 集成 obfuscator 插件并配置混淆选项
		obfuscator({
			globals: ['window'], // 全局对象
			compact: true, // 紧凑代码
			controlFlowFlattening: true, // 启用控制流平坦化
			controlFlowFlatteningThreshold: 0.75, // 控制流平坦化的应用比例
			deadCodeInjection: true, // 启用死代码注入
			deadCodeInjectionThreshold: 0.4, // 死代码注入的应用比例
			debugProtection: true, // 启用调试保护
			debugProtectionInterval: true, // 启用调试保护间隔
			disableConsoleOutput: true, // 禁用控制台输出
			stringArray: true, // 启用字符串数组
			stringArrayThreshold: 0.75 // 字符串数组的应用比例
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
	}
});
