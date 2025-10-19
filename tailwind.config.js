import typography from '@tailwindcss/typography';
import containerQueries from '@tailwindcss/container-queries';

/** @type {import('tailwindcss').Config} */
export default {
	darkMode: 'class',
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			colors: {
				// Renobo Brand Colors
				primary: {
					50: '#e6f7f2',
					100: '#ccefe5',
					200: '#99dfcb',
					300: '#66cfb1',
					400: '#33bf97',
					500: '#00A676',  // Primary Renobo Green
					600: '#00855e',
					700: '#007D63',  // Primary Dark
					800: '#005340',
					900: '#003a2d',
					950: '#00261f'
				},
				background: {
					DEFAULT: '#F7F9F9',  // Background color
					dark: '#1B263B'      // Dark background (using text color)
				},
				text: {
					DEFAULT: '#1B263B',  // Text color
					light: '#F7F9F9'     // Light text (for dark backgrounds)
				},
				accent: {
					DEFAULT: '#E0FBFC',  // Accent color
					50: '#f7feff',
					100: '#E0FBFC',
					200: '#c4f6f8',
					300: '#a7f2f4',
					400: '#8bedf0',
					500: '#6ee9ec',
					600: '#4dd4d7',
					700: '#3ab0b3',
					800: '#2d888a',
					900: '#1f5e60'
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
			},
			fontFamily: {
				sans: ['Inter', 'system-ui', 'sans-serif']
			}
		}
	},
	plugins: [typography, containerQueries]
};
