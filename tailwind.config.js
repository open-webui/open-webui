import typography from '@tailwindcss/typography';
import containerQueries from '@tailwindcss/container-queries';

/** @type {import('tailwindcss').Config} */
export default {
	darkMode: 'class',
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			fontFamily: {
				base: ['Pretendard', 'system-ui', 'sans-serif']
			},
			colors: {
				gray: {
					50: 'var(--color-gray-50, #F7F8FB)',
					100: 'var(--color-gray-100, #e8eaf3)',
					200: 'var(--color-gray-200, #ced4e5)',
					300: 'var(--color-gray-300, #B4BCD0)',
					400: 'var(--color-gray-400, #a0a9bd)',
					500: 'var(--color-gray-500, #8d96ad)',
					600: 'var(--color-gray-600, #717a8f)',
					700: 'var(--color-gray-700, #596172)',
					800: 'var(--color-gray-800, #363B45)',
					850: 'var(--color-gray-850, #262626)',
					900: 'var(--color-gray-900, #27282c)',
					950: 'var(--color-gray-950, #1a1b1c)'
				},
				'engine-blue': {
					50: 'var(--color-engine-blue-50, #e2f2ff)',
					100: 'var(--color-engine-blue-100, #b9d0ff)',
					200: 'var(--color-engine-blue-200, #8bc8ff)',
					300: 'var(--color-engine-blue-300, #51b2ff)',
					400: 'var(--color-engine-blue-400, #15a1ff)',
					500: 'var(--color-engine-blue-500, #0081ff)',
					600: 'var(--color-engine-blue-600, #0081ff)',
					700: 'var(--color-engine-blue-700, #1076ef4)',
					800: 'var(--color-engine-blue-800, #175be1)',
					900: 'var(--color-engine-blue-900, #233bc2)'
				},
				// Semantic Colors - Primary
				'primary': {
					50: 'var(--color-primary-50, #e2f2ff)',
					100: 'var(--color-primary-100, #b9d0ff)',
					200: 'var(--color-primary-200, #8bc8ff)',
					300: 'var(--color-primary-300, #51b2ff)',
					400: 'var(--color-primary-400, #15a1ff)',
					500: 'var(--color-primary-500, #0081ff)',
					600: 'var(--color-primary-600, #0081ff)',
					700: 'var(--color-primary-700, #0081ff)',
					800: 'var(--color-primary-800, #175be1)',
					900: 'var(--color-primary-900, #233bc2)'
				},
				// Semantic Colors - Neutral (Layout)
				'neutral': {
					50: 'var(--color-neutral-50, #f2f4f8)',
					100: 'var(--color-neutral-100, #e8eaf3)',
					200: 'var(--color-neutral-200, #cde4e5)',
					300: 'var(--color-neutral-300, #b48d00)',
					400: 'var(--color-neutral-400, #a0a98d)',
					500: 'var(--color-neutral-500, #8d9640)',
					600: 'var(--color-neutral-600, #717abf)',
					700: 'var(--color-neutral-700, #596172)',
					800: 'var(--color-neutral-800, #363845)',
					900: 'var(--color-neutral-900, #27282c)',
					950: 'var(--color-neutral-950, #1a1b1c)'
				},
				// Semantic Colors - Success
				'success': {
					50: 'var(--color-success-50, #e8f5e9)',
					100: 'var(--color-success-100, #c8e6c9)',
					200: 'var(--color-success-200, #a5d6a7)',
					300: 'var(--color-success-300, #81c784)',
					400: 'var(--color-success-400, #66bb6a)',
					500: 'var(--color-success-500, #4caf50)',
					600: 'var(--color-success-600, #43a047)',
					700: 'var(--color-success-700, #388e3c)',
					800: 'var(--color-success-800, #2e7d32)',
					900: 'var(--color-success-900, #1b5e20)'
				},
				// Semantic Colors - Warning
				'warning': {
					50: 'var(--color-warning-50, #fff3e0)',
					100: 'var(--color-warning-100, #ffe0b2)',
					200: 'var(--color-warning-200, #ffcc80)',
					300: 'var(--color-warning-300, #ffb74d)',
					400: 'var(--color-warning-400, #ffa726)',
					500: 'var(--color-warning-500, #ff9800)',
					600: 'var(--color-warning-600, #fb8c00)',
					700: 'var(--color-warning-700, #f57c00)',
					800: 'var(--color-warning-800, #e65100)',
					900: 'var(--color-warning-900, #bf360c)'
				},
				// Semantic Colors - Error
				'error': {
					50: 'var(--color-error-50, #ffebee)',
					100: 'var(--color-error-100, #ffcdd2)',
					200: 'var(--color-error-200, #ef9a9a)',
					300: 'var(--color-error-300, #e57373)',
					400: 'var(--color-error-400, #ef5350)',
					500: 'var(--color-error-500, #f44336)',
					600: 'var(--color-error-600, #e53935)',
					700: 'var(--color-error-700, #d32f2f)',
					800: 'var(--color-error-800, #c62828)',
					900: 'var(--color-error-900, #b71c1c)'
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
			fontSize: {
				'title-1': ['1.75rem', { fontWeight: '600', lineHeight: '150%' }],
				'title-2': ['1.5rem', { fontWeight: '600', lineHeight: '150%' }],
				'title-3': ['1.25rem', { fontWeight: '600', lineHeight: '150%' }],
				'title-4': ['1.125rem', { fontWeight: '600', lineHeight: '150%' }],
				'body-1': ['1.25rem', { fontWeight: '400', lineHeight: '150%' }],
				'body-1-medium': ['1.25rem', { fontWeight: '500', lineHeight: '150%' }],
				'body-2': ['1.125rem', { fontWeight: '400', lineHeight: '150%' }],
				'body-2-medium': ['1.125rem', { fontWeight: '500', lineHeight: '150%' }],
				'body-3': ['1rem', { fontWeight: '400', lineHeight: '150%' }],
				'body-3-medium': ['1rem', { fontWeight: '500', lineHeight: '150%' }],
				'body-4': ['0.875rem', { fontWeight: '400', lineHeight: '150%' }],
				'body-4-medium': ['0.875rem', { fontWeight: '500', lineHeight: '150%' }],
				'caption': ['0.75rem', { fontWeight: '400', lineHeight: '150%' }],
				'caption-medium': ['0.75rem', { fontWeight: '500', lineHeight: '150%' }]
			},
			padding: {
				'safe-bottom': 'env(safe-area-inset-bottom)'
			},
			transitionProperty: {
				width: 'width'
			},
			backgroundImage: {
				// Semantic Borderline Gradient - Angular (Figma 정의)
				'gradient-borderline-angular': 'conic-gradient(from 135deg at 50% 50%, rgba(206, 212, 229, 0.5) 0deg, rgba(113, 122, 191, 0.3) 90deg, rgba(206, 212, 229, 0.5) 180deg, rgba(113, 122, 191, 0.3) 270deg, rgba(206, 212, 229, 0.5) 360deg)',
				// Semantic Pattern Gradient - Radial (Primary)
				'gradient-pattern-radial': 'radial-gradient(circle, #0081ff 0%, #0081ff 100%)',
				// Semantic Background Gradient - Dark
				'gradient-background-dark-1': 'linear-gradient(to right, #1a1b1c, #1a1b1c)',
				'gradient-background-dark-2': 'linear-gradient(to right, #1a1b1c, #1a1b1c)'
			}
		}
	},
	plugins: [typography, containerQueries]
};
