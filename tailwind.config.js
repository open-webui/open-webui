import typography from '@tailwindcss/typography';
import containerQuries from '@tailwindcss/container-queries';

/** @type {import('tailwindcss').Config} */
export default {
	darkMode: 'class',
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			colors: {
				surface: '#F9F9FF',
				'gradient-bg-2': 'rgba(204, 221, 252, 0.3)',
				typography:{
                    titles:'#23282E',
					subtext:'#666D7A',
					'secondary-body-text':'#979EAD',
					disabled: '#ABB4C5',
				},
				neutrals:{
                       50: 'var(--color-neutrals-50, #ECEEF1)',
					   100: 'var(--color-neutrals-100, #DEE0E3)',
					   400: 'var(--color-neutrals-400, #A5A6A9)',
					   700: 'var(--color-neutrals-700, #4F5154)',
					   800: 'var(--color-neutrals-800, #36383B)',
					   hover: 'var(--color-neutrals-hover, rgba(236, 238, 241, 0.72))',
					   black: 'var(--color-neutrals-black, #1D1F22)',
					   white: 'var(--color-neutrals-white, #ffffff)', 
					   error:'var(--color-neutrals-error, #D91938)',
					   errorTone:'var(--color-neutrals-errorTone, #C2451E)',
					   green:'var(--color-neutrals-errorTone, #04C759)',
				},
				primary:{
					400: 'var(--color-primary-400, #0054F2)',  
					DEFAULT: 'var(--color-primary-400, #0054F2)',
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
					950: 'var(--color-gray-950, #0d0d0d)',
					1000: 'var(--color-gray-1000, #1C1B1B)',
					1050: 'var(--color-gray-1050, #FBFBFB)',
					1100: 'var(--color-gray-1100, #DFE2EE)',
					1150:'var(--color-gray-1150, #F5F5F5)',
					1200: 'var(--color-gray-1200, #424750)',
					1300:'var(--color-gray-1350, #EAEAEA)',
				},
			},
			  boxShadow: {
				'custom': '0px 24px 48px 0px rgba(0, 0, 0, 0.08)',
				'custom2': '0px 48px 100px 0px rgba(0, 84, 242, 0.08)',
				'custom3': ' 0px 10px 20px 0px rgba(0, 0, 0, 0.10)',
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
			backgroundImage: {
				'login': "url('/login-bg.jpg')",
			  }
		}
	},
	plugins: [typography, containerQuries]
};
