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
					50: 'var(--color-gray-50, #FAFAF7)',
					100: 'var(--color-gray-100, #F0F0EB)',
					200: 'var(--color-gray-200, #E5E4DF)',
					300: 'var(--color-gray-300, #BFBFBA)',
					400: 'var(--color-gray-400, #91918D)',
					500: 'var(--color-gray-500, #666663)',
					600: 'var(--color-gray-600, #52524F)',
					700: 'var(--color-gray-700, #40403E)',
					800: 'var(--color-gray-800, #33332E)',
					850: 'var(--color-gray-850, #262625)',
					900: 'var(--color-gray-900, #1F1F1E)',
					950: 'var(--color-gray-950, #191919)'
				},
				'book-cloth': '#CC785C',
				kraft: '#D4A27F',
				manilla: '#EBDBBC',
				'manilla-dark': '#33332E',
				'error-brick': '#BF4D43'
			},
			borderWidth: {
				hairline: '0.5px'
			},
			transitionTimingFunction: {
				paper: 'cubic-bezier(0.16, 1, 0.3, 1)'
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
