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
	plugins: ['@typescript-eslint'],
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
	ignorePatterns: ['static/pyodide/**s'],
	rules: {
        // Base ESLint rules
        //'no-async-promise-executor': 'off', // 1
        //'no-constant-condition': 'off',
		//'no-console': 'error', // 738
        'no-control-regex': 'off', // 2
		'no-debugger': 'error',
        //'no-empty': 'off', // 4
        //'no-ex-assign': 'off', // 2
        'no-irregular-whitespace': 'off', // 1
        'no-prototype-builtins': 'off', // 1
        'no-undef': 'off', //10
        'no-unsafe-optional-chaining': 'off', //1
        'no-useless-escape': 'off',
        'prefer-const': 'off',

        // TypeScript ESLint rules
        '@typescript-eslint/no-empty-object-type': 'off', // 3
        '@typescript-eslint/no-explicit-any': 'off', // 50
        '@typescript-eslint/no-unsafe-function-type': 'off', // 166
        '@typescript-eslint/no-unused-expressions': 'off', // 12
        '@typescript-eslint/no-unused-vars': 'off', // 811

        // Svelte rules
        'svelte/no-at-html-tags': 'off', // 8
        'svelte/no-inner-declarations': 'off', // 2
        'svelte/no-unused-svelte-ignore': 'off', // 18
        'svelte/valid-compile': 'off' // 149
    }
};
