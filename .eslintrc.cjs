module.exports = {
	root: true,
	extends: [
		'eslint:recommended',
		'plugin:@typescript-eslint/recommended',
		'plugin:svelte/recommended',
		'plugin:cypress/recommended',
		'prettier'
	],
	parser: '@typescript-eslint/parser',
	plugins: ['@typescript-eslint', 'unused-imports'],
	parserOptions: {
		sourceType: 'module',
		ecmaVersion: 2020,
		extraFileExtensions: ['.svelte']
	},
	env: {
		browser: true,
		es2017: true,
		node: true
	},
	overrides: [
		{
			files: ['*.svelte'],
			parser: 'svelte-eslint-parser',
			parserOptions: {
				parser: '@typescript-eslint/parser'
			}
		}
	],
	rules: {
		'sort-imports': [
			'error',
			{
				ignoreDeclarationSort: true
			}
		],
		'unused-imports/no-unused-imports': 'error',
		'no-constant-condition': [
			'error',
			{
				checkLoops: false // Change to 'allExceptWhileTrue' when eslint is upgraded >= 9.1.0
			}
		]
	}
};
