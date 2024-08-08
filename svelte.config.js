import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import obfuscator from 'vite-plugin-obfuscator';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	// Consult https://kit.svelte.dev/docs/integrations#preprocessors
	// for more information about preprocessors
	preprocess: vitePreprocess(),
	kit: {
		// adapter-auto only supports some environments, see https://kit.svelte.dev/docs/adapter-auto for a list.
		// If your environment is not supported or you settled on a specific environment, switch out the adapter.
		// See https://kit.svelte.dev/docs/adapters for more information about adapters.
		adapter: adapter({
			pages: 'build',
			assets: 'build',
			fallback: 'index.html'
		}),
		vite: {
			plugins: [
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
			]
		}
	},
	onwarn: (warning, handler) => {
		const { code, _ } = warning;
		if (code === 'css-unused-selector') return;
		
		handler(warning);
	}
};

export default config;
