import typography from '@tailwindcss/typography';
import containerQueries from '@tailwindcss/container-queries';

/** @type {import('tailwindcss').Config} */
export default {
	darkMode: 'class',
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			colors: {
				claw: {
					50: '#fef3ee',
					100: '#fde4d6',
					200: '#fac5ac',
					300: '#f69d78',
					400: '#f17042',
					500: '#ed4d1e',
					600: '#de3514',
					700: '#b82512',
					800: '#932017',
					900: '#771d16',
					950: '#400c09'
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
