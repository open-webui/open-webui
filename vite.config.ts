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
	plugins: [sveltekit(), terser({
		parse: {
			// options for parsing input code
			ecma: 2020,
		},
		compress: {
			// options for compressing code
			ecma: 5,
			comparisons: false,
			inline: 2,
			drop_console: true, // 移除 console 语句
			drop_debugger: true, // 移除 debugger 语句
			dead_code: true, // 移除未使用的代码
			conditionals: true, // 优化 if/else 语句
			booleans: true, // 优化布尔表达式
			loops: true, // 优化循环
			unused: true, // 移除未引用的函数和变量
			toplevel: true, // 顶级变量和函数优化
		},
		mangle: {
			// options for mangling variable and function names
			toplevel: true, // 顶级变量和函数名混淆
			properties: {
				regex: /^_/, // 混淆以下划线开头的属性
			},
		},
		output: {
			// options for output
			ecma: 5,
			comments: false, // 移除注释
			beautify: false, // 不美化输出代码
		},
		module: true,
		sourceMap: false, // 是否生成 source map
	})],
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
