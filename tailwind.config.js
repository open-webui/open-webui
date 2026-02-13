import typography from '@tailwindcss/typography';
import containerQueries from '@tailwindcss/container-queries';

/** @type {import('tailwindcss').Config} */
export default {
	darkMode: 'class',
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			colors: {
				accent: {
					DEFAULT: 'var(--accent-500, #e3530f)',
					50: 'var(--accent-50, #fef3ed)',
					100: 'var(--accent-100, #fde4d4)',
					200: 'var(--accent-200, #fac5a8)',
					300: 'var(--accent-300, #f6a071)',
					400: 'var(--accent-400, #f17038)',
					500: 'var(--accent-500, #e3530f)',
					600: 'var(--accent-600, #d44409)',
					700: 'var(--accent-700, #b0330a)',
					800: 'var(--accent-800, #8c2a10)',
					900: 'var(--accent-900, #722610)',
					950: 'var(--accent-950, #3e1006)'
				},
				gray: {
					50: 'var(--color-gray-50, #f9f9f9)',
					100: 'var(--color-gray-100, #ececec)',
					200: 'var(--color-gray-200, #e3e3e3)',
					300: 'var(--color-gray-300, #cdcdcd)',
					400: 'var(--color-gray-400, #b4b4b4)',
					500: 'var(--color-gray-500, #9b9b9b)',
					600: 'var(--color-gray-600, #676767)',
					700: 'var(--color-gray-700, #4e4e4e)',
					800: 'var(--color-gray-800, #333)',
					850: 'var(--color-gray-850, #262626)',
					900: 'var(--color-gray-900, #171717)',
					950: 'var(--color-gray-950, #0d0d0d)'
				}
			},
			typography: {
				DEFAULT: {
					css: {
						pre: false,
						code: false,
						'pre code': false,
						'code::before': false,
						'code::after': false
					}
				}
			},
			padding: {
				'safe-bottom': 'env(safe-area-inset-bottom)'
			},
			transitionProperty: {
				width: 'width'
			}
		}
	},
	plugins: [typography, containerQueries]
};
