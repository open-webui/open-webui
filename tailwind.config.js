import typography from '@tailwindcss/typography';
import containerQuries from '@tailwindcss/container-queries';

/** @type {import('tailwindcss').Config} */
export default {
	darkMode: 'class',
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			fontFamily: {
				sans: ['Inter', 'ui-sans-serif', 'system-ui'], 
			  },
			fontSize: {
			'2xs': '10px',
			'xs-plus': '13px',
			},
			spacing: {
				'2.5': '0.625rem',
				'6.5': '1.625rem',
				'45': '11.25rem', 
			},
			borderRadius: {
				mdx: '10px'
			},
			colors: {
				gray: {
					50: '#f9f9f9',
					100: '#ececec',
					200: '#e3e3e3',
					300: '#cdcdcd',
					400: '#b4b4b4',
					500: '#9b9b9b',
					600: '#676767',
					700: '#4e4e4e',
					800: 'var(--color-gray-800, #333)',
					850: 'var(--color-gray-850, #262626)',
					900: 'var(--color-gray-900, #171717)',
					950: 'var(--color-gray-950, #0d0d0d)'
				},
				customGray: {
					100: '#D0CECE',
					200: '#ACABAB',
					300: '#939292',
					400: '#929AA1',
					500: '#8E8E8E',
					550: '#858586', 
					590: '#777676',
					600: '#787878',
					700: '#313337',
					800: '#272525',
					900: '#1E1E1E',
					950: '#181818'
				},
				customBlue: {
					500: '#007FFF',
					600: '#305BE4',
					700: '#272D98',
					800: '#272A6A'
				},
				customViolet: {
					300: '#41386E'
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
			}
		}
	},
	plugins: [typography, containerQuries]
};
