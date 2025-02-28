// @ts-check
import js from '@eslint/js';
import svelte from 'eslint-plugin-svelte';
import ts from 'typescript-eslint';
import * as svelteParser from 'svelte-eslint-parser';
import * as typescriptParser from '@typescript-eslint/parser';
import * as espree from 'espree';
import eslintPluginPrettierRecommended from 'eslint-plugin-prettier/recommended';
import globals from 'globals';

export default [
	{
		ignores: [
			'static',
			'node_modules',
			'test',
			'.svelte-kit',
			'__pycache__',
			'.venv',
			'build',
			'dist'
		]
	},
	{
		languageOptions: {
			globals: {
				...globals.browser
			}
		}
	},
	js.configs.recommended,
	...ts.configs.recommended,
	...svelte.configs['flat/all'],
	eslintPluginPrettierRecommended,
	...svelte.configs['flat/prettier'],
	{
		files: ['**/*.svelte'],
		rules: {
			'svelte/no-unused-class-name': 0,
			'svelte/block-lang': 0,
			'svelte/experimental-require-strict-events': 0
		},
		languageOptions: {
			parser: svelteParser,
			// svelteConfig: svelteConfig,
			parserOptions: {
				parser: {
					// Specify a parser for each lang.
					ts: typescriptParser,
					js: espree,
					typescript: typescriptParser
				},
				extraFileExtensions: ['.svelte']
			}
		}
	}
];
