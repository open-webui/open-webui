import { defineConfig, type Plugin } from 'vite';

import { viteStaticCopy } from 'vite-plugin-static-copy';
import { sveltekit } from '@sveltejs/kit/vite';

import path from 'path';
import fs from 'fs/promises';

const HighlightJSLanguagesPlugin = (): Plugin => {
	const virtualModuleId = 'virtual:highlightjs-languages';
	const resolvedVirtualModuleId = '\0' + virtualModuleId;

	return {
		name: 'highlightjs-languages-plugin',
		resolveId(id) {
			if (id === virtualModuleId) {
				return resolvedVirtualModuleId;
			}
		},
		async load(id) {
			if (id !== resolvedVirtualModuleId) {
				return;
			}
			const languagesPath = path.join(
				import.meta.resolve('highlight.js').replace('file:', ''),
				'../languages'
			);
			const languages = (await fs.readdir(languagesPath))
				.filter((file) => !file.endsWith('.js.js'))
				.map((file) => file.replace(/\.js$/, ''));

			const { default: hljs } = await import('highlight.js');
			const generateLanguageConfig = (language: string) =>
				`() => import(${JSON.stringify(path.join(languagesPath, language))})`;
			const kvPairs = languages.map((language) => [language, generateLanguageConfig(language)]);
			languages.forEach((language) => {
				const config = hljs.getLanguage(language);
				if (config?.aliases?.length) {
					config.aliases.forEach((alias) =>
						kvPairs.push([alias, generateLanguageConfig(language)])
					);
				}
			});

			return `export default { ${kvPairs.map(([key, value]) => `'${key}': ${value}`).join(', ')} }`;
		}
	};
};

export default defineConfig({
	plugins: [
		sveltekit(),
		HighlightJSLanguagesPlugin(),
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
	esbuild: {
		pure: process.env.ENV === 'dev' ? [] : ['console.log', 'console.debug', 'console.error']
	}
});
