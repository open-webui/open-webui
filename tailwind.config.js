/** @type {import('tailwindcss').Config} */
export default {
	darkMode: 'class',
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			colors: {
				gray: {
					50: '#f7f7f8',
					100: '#ececf1',
					200: '#d9d9e3',
					300: '#c5c5d2',
					400: '#acacbe',
					500: '#8e8ea0',
					600: '#565869',
					700: '#40414f',
					800: '#343541',
					900: '#202123',
					950: '#050509'
				},
				'fits-blue': '#304b6a',
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

			animation: {
				blob: "blob 7s infinite",
			  },
			  keyframes: {
				blob: {
				  "0%": {
					transform: "translate(0px, 0px) scale(1)",
				  },
				  "33%": {
					transform: "translate(30px, -50px) scale(1.1)",
				  },
				  "66%": {
					transform: "translate(-20px, 20px) scale(0.9)",
				  },
				  "100%": {
					transform: "translate(0px, 0px) scale(1)",
				  },
				},
			},
		},
	},
	variants: {
		extend: {},
	  },
	plugins: [require('@tailwindcss/typography')]
};
