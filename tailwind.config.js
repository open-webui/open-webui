import typography from '@tailwindcss/typography';

/** @type {import('tailwindcss').Config} */
export default {
	darkMode: 'class',
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			colors: {
				gray: {
					50: '#f9f9f9',
					100: '#F4F7FA',
					200: '#DBE2E8',
					300: '#bcc8d4',
					400: '#97A3B4',
					450: '#8896AA',
					500: '#718095',
					600: '#465A75',
					700: '#2E4360',
					800: '#1D2D42',
					850: 'var(--color-gray-850, #262626)',
					900: '#0A121C',
					950: 'var(--color-gray-950, #0d0d0d)'
				},
				blue: {
					100: '#dbedf8',
					200: '#95caeb',
					300: '#3196D6',
					400: '#1474C4',
					500: '#095BB1',
					600: '#003D8F',
					700: '#0B2A63',
					800: '#001B41',
					900: '#02102B',
				},
				red: {
					100: '#FFE4E2',
					200: '#FFA8A3',
					300: '#FF6159',
					400: '#F50C00',
					500: '#C80A00',
					600: '#9C0800',
					700: '#6E0500',
				},
				green: {
					100: '#C7FAE2',
					200: '#46EFA0',
					300: '#12CF76',
					400: '#0FA954',
					500: '#0C8A44',
					600: '#096B35',
					700: '#074D26',
				},
				purple: {
					100: '#FAE7FE',
					200: '#F0B7FB',
					300: '#E480F8',
					400: '#D746F5',
					500: '#B410E7',
					600: '#8212C2',
					700: '#560E8A'
				},
				amber: {
					100: '#FFEDCA',
					200: '#FFD176',
					300: '#FFAA00',
					400: '#EF8300',
					500: '#C36B00',
					600: '#8E4E00',
					700: '#603500'
				},
				sky: {
					100: '#D2F6FC',
					200: '#7FE4F6',
					300: '#11C7E6',
					400: '#08A5C5',
					500: '#007E9C',
					600: '#005B72',
					700: '#003D4B'
				},
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
			screens: {
				xs: "560px",
			}
		}
	},
	plugins: [typography]
};
