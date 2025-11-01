import typography from '@tailwindcss/typography';
import containerQueries from '@tailwindcss/container-queries';

/** @type {import('tailwindcss').Config} */
export default {
	darkMode: 'class',
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			colors: {
				// Coffee-themed palette for VITA
				coffee: {
					cream: '#EFEBE9',
					latte: '#D7CCC8',
					cappuccino: '#A1887F',
					mocha: '#8D6E63',
					bean: '#6D4C41',
					espresso: '#5D4037',
					dark: '#4E342E',
					roast: '#3E2723',
					midnight: '#1E1410'
				},
				gray: {
					50: 'var(--color-gray-50, #EFEBE9)',      // Coffee cream
					100: 'var(--color-gray-100, #D7CCC8)',    // Latte
					200: 'var(--color-gray-200, #BCAAA4)',    // Light cappuccino
					300: 'var(--color-gray-300, #A1887F)',    // Cappuccino
					400: 'var(--color-gray-400, #8D6E63)',    // Mocha
					500: 'var(--color-gray-500, #795548)',    // Medium roast
					600: 'var(--color-gray-600, #6D4C41)',    // Coffee bean
					700: 'var(--color-gray-700, #5D4037)',    // Espresso
					800: 'var(--color-gray-800, #4E342E)',    // Dark roast
					850: 'var(--color-gray-850, #3E2723)',    // Deep roast
					900: 'var(--color-gray-900, #2C1810)',    // Very dark
					950: 'var(--color-gray-950, #1E1410)'     // Midnight roast
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
