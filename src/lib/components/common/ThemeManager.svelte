<script lang="ts">
	/**
	 * @component ThemeManager
	 * This is a logic-only Svelte component responsible for managing and applying
	 * container-specific theme customizations, such as gradients and animations.
	 * It listens to the live theme store and applies changes to the container element
	 * passed to it as a prop.
	 *
	 * @prop {HTMLElement} container - The HTML element to which the theme customizations will be applied.
	 */
	import type { Theme } from '$lib/types';
	import { onMount } from 'svelte';
	import { liveThemeStore } from '$lib/stores/theme';

	export let container: HTMLElement;

	let lastTheme: Theme | undefined = undefined;
	let currentAnimation: Theme['animation'] | undefined;
	let currentResizeObserver: ResizeObserver | undefined;

	const cleanupCustomizations = (theme: Theme, mainContainer: HTMLElement) => {
		if (!mainContainer) return;
		if (currentAnimation && typeof currentAnimation.stop === 'function') {
			currentAnimation.stop();
		}
		currentAnimation = undefined;

		const canvas = mainContainer.querySelector(`[id$='-canvas']`);
		if (canvas) {
			canvas.remove();
		}

		if (currentResizeObserver) {
			currentResizeObserver.disconnect();
			currentResizeObserver = undefined;
		}

		mainContainer.classList.remove(`${theme.id}-bg`);
		mainContainer.style.backgroundImage = 'none';

		const gradientLayer = mainContainer.querySelector('#theme-gradient-layer');
		if (gradientLayer) {
			gradientLayer.remove();
		}
	};

	const applyCustomizations = (theme: Theme, mainContainer: HTMLElement) => {
		if (!mainContainer) return;
		// Handle Gradient
		if (
			theme.gradient &&
			(!theme.toggles || typeof theme.toggles.gradient === 'undefined' || theme.toggles.gradient) &&
			theme.gradient.enabled &&
			theme.gradient.colors.length > 0
		) {
			const { colors, direction, intensity } = theme.gradient;
			const alpha = (intensity ?? 100) / 100;
			const rgbaColors = colors.map((hex) => {
				if (/^#([A-Fa-f0-9]{3}){1,2}$/.test(hex)) {
					let c = hex.substring(1).split('');
					if (c.length === 3) {
						c = [c[0], c[0], c[1], c[1], c[2], c[2]];
					}
					c = '0x' + c.join('');
					const r = (c >> 16) & 255;
					const g = (c >> 8) & 255;
					const b = c & 255;
					return `rgba(${r}, ${g}, ${b}, ${alpha})`;
				}
				return `rgba(0, 0, 0, ${alpha})`;
			});
			const gradientCss = `linear-gradient(${direction}deg, ${rgbaColors.join(', ')})`;

			const gradientLayer = document.createElement('div');
			gradientLayer.id = 'theme-gradient-layer';
			gradientLayer.style.position = 'absolute';
			gradientLayer.style.top = '0';
			gradientLayer.style.left = '0';
			gradientLayer.style.width = '100%';
			gradientLayer.style.height = '100%';
			gradientLayer.style.zIndex = '3';
			gradientLayer.style.backgroundImage = gradientCss;
			mainContainer.prepend(gradientLayer);
		} else {
			mainContainer.style.backgroundImage = 'none';
		}

		mainContainer.classList.add(`${theme.id}-bg`);
		if (theme.animationScript && (!theme.toggles || theme.toggles.animationScript)) {
			const canvas = document.createElement('canvas');
			canvas.id = `${theme.id}-canvas`;
			canvas.style.position = 'absolute';
			canvas.style.top = '0';
			canvas.style.left = '0';
			canvas.style.width = '100%';
			canvas.style.height = '100%';
			canvas.style.zIndex = '0';
			canvas.style.pointerEvents = 'none';
			canvas.style.opacity = '0';
			canvas.style.transition = 'opacity 0.5s ease-in-out';
			mainContainer.prepend(canvas);

			try {
				const blob = new Blob([theme.animationScript], { type: 'application/javascript' });
				const workerUrl = URL.createObjectURL(blob);
				const worker = new Worker(workerUrl);

				const offscreen = canvas.transferControlToOffscreen();

				const rect = mainContainer.getBoundingClientRect();
				worker.postMessage(
					{ type: 'init', canvas: offscreen, width: rect.width, height: rect.height },
					[offscreen]
				);

				currentResizeObserver = new ResizeObserver((entries) => {
					if (entries.length > 0) {
						const entry = entries[0];
						worker.postMessage({
							type: 'resize',
							width: entry.contentRect.width,
							height: entry.contentRect.height
						});
					}
				});
				currentResizeObserver.observe(mainContainer);

				mainContainer.addEventListener('mousemove', (e) => {
					const rect = mainContainer.getBoundingClientRect();
					worker.postMessage({
						type: 'mousemove',
						x: e.clientX - rect.left,
						y: e.clientY - rect.top
					});
				});

				currentAnimation = {
					start: () => {},
					stop: () => {
						worker.terminate();
						URL.revokeObjectURL(workerUrl);
						if (currentResizeObserver) {
							currentResizeObserver.disconnect();
						}
					}
				};
			} catch (e) {
				console.error('Failed to start animation worker:', e);
			}

			setTimeout(() => {
				window.dispatchEvent(new Event('resize'));
				canvas.style.opacity = '1';
			}, 100);
		} else if (theme.animation && typeof theme.animation.start === 'function') {
			const canvas = document.createElement('canvas');
			canvas.id = `${theme.id}-canvas`;
			canvas.style.position = 'absolute';
			canvas.style.top = '0';
			canvas.style.left = '0';
			canvas.style.width = '100%';
			canvas.style.height = '100%';
			canvas.style.zIndex = '0';
			canvas.style.pointerEvents = 'none';
			canvas.style.opacity = '0';
			canvas.style.transition = 'opacity 0.5s ease-in-out';
			mainContainer.prepend(canvas);

			currentAnimation = theme.animation;
			currentAnimation.start(canvas);

			setTimeout(() => {
				window.dispatchEvent(new Event('resize'));
				canvas.style.opacity = '1';
			}, 100);
		}
	};

	onMount(() => {
		const unsubscribe = liveThemeStore.subscribe((theme) => {
			if (!container) {
				return;
			}

			if (lastTheme) {
				cleanupCustomizations(lastTheme, container);
			}
			if (theme) {
				applyCustomizations(theme, container);
				lastTheme = theme;
			}
		});

		return () => {
			unsubscribe();
			if (lastTheme && container) {
				cleanupCustomizations(lastTheme, container);
			}
		};
	});
</script>
