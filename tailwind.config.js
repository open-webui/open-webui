/** @type {import('tailwindcss').Config} */
export default {
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			colors: {
				gray: {
					50: '#000000',
					100: '#111111',
					200: '#2d2d2d',
					300: '#3d3d3d',
					400: '#b4b4b4',
					500: '#373738',
					600: '#9b9b9b',
					700: '#676767',
					800: 'var(--color-gray-800, #4a4a4a)',
					850: 'var(--color-gray-850, #4e4e4e)',
					900: 'var(--color-gray-900, #ececec)',
					950: 'var(--color-gray-950, #ffffff)'
				},
				red: {999: '#7c1d18'}
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
	plugins: [require('@tailwindcss/typography')]
};
