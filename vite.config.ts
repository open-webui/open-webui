import { defineConfig } from 'vite';
import { sveltekit } from '@sveltejs/kit/vite';
import terser from '@rollup/plugin-terser';

export default defineConfig(({ mode }) => {
	// const isProduction = mode === 'production';
	const isProduction = true;

	return {
		plugins: [
			sveltekit(),
			// 仅在生产环境使用 terser
			isProduction && terser({
				format: {
					comments: false,
				},
				compress: {
					drop_console: true,
					drop_debugger: true,
				},
			}),
		],
		define: {
			APP_VERSION: JSON.stringify(process.env.npm_package_version),
			APP_BUILD_HASH: JSON.stringify(process.env.APP_BUILD_HASH || 'dev-build'),
			'process.env.NODE_ENV': JSON.stringify(mode),
		},
		build: {
			sourcemap: !isProduction,  // 仅在开发环境生成sourcemap
			target: 'esnext',
			minify: isProduction ? 'terser' : false,  // 仅在生产环境最小化代码
		},
		worker: {
			format: 'es',
		},
	};
});
