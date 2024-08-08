import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import { obfuscate } from 'javascript-obfuscator'; // 导入 obfuscator 方法

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
			plugins: [{
				name: 'vite-plugin-javascript-obfuscator',
				enforce: 'post',
				// Vite 构建钩子，混淆生成的代码
				generateBundle(options, bundle) {
					for (const file of Object.values(bundle)) {
						if (file.type === 'chunk') {
							const obfuscatedCode = obfuscate(file.code, {
								compact: true,
								controlFlowFlattening: true,
								controlFlowFlatteningThreshold: 0.75,
								deadCodeInjection: true,
								deadCodeInjectionThreshold: 0.4,
								debugProtection: true,
								debugProtectionInterval: true,
								disableConsoleOutput: true,
								stringArray: true,
								stringArrayThreshold: 0.75
							}).getObfuscatedCode();

							file.code = obfuscatedCode;
						}
					}
				}
			}]
		}
	},
	onwarn: (warning, handler) => {
		const { code, _ } = warning;
		if (code === 'css-unused-selector') return;
		
		handler(warning);
	}
};

export default config;