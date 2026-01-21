import typography from '@tailwindcss/typography';
import containerQueries from '@tailwindcss/container-queries';

/** @type {import('tailwindcss').Config} */
export default {
	darkMode: 'class',
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			colors: {
				gray: {
					50: 'var(--color-gray-50, #fafafa)',
					100: 'var(--color-gray-100, #f4f4f5)',
					200: 'var(--color-gray-200, #e4e4e7)',
					300: 'var(--color-gray-300, #d4d4d8)',
					400: 'var(--color-gray-400, #a1a1aa)',
					500: 'var(--color-gray-500, #71717a)',
					600: 'var(--color-gray-600, #52525b)',
					700: 'var(--color-gray-700, #3f3f46)',
					800: 'var(--color-gray-800, #27272a)',
					850: 'var(--color-gray-850, #1f1f23)',
					900: 'var(--color-gray-900, #18181b)',
					950: 'var(--color-gray-950, #09090b)'
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
