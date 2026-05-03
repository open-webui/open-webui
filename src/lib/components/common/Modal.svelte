<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { fade } from 'svelte/transition';

	import { flyAndScale } from '$lib/utils/transitions';
	import * as FocusTrap from 'focus-trap';
	export let show = true;
	export let size = 'md';
	export let containerClassName = 'p-3';
	export let className = 'bg-white dark:bg-gray-850 rounded-2xl';

	let modalElement = null;
	let mounted = false;
	let savedScrollY = 0;
	// Create focus trap to trap user tabs inside modal
	// https://www.w3.org/WAI/WCAG21/Understanding/focus-order.html
	// https://www.w3.org/WAI/WCAG21/Understanding/keyboard.html
	let focusTrap: FocusTrap.FocusTrap | null = null;

	const sizeToWidth = (size) => {
		// max-sm:w-full forces full width below Tailwind's sm breakpoint (640px)
		// so modals don't get clipped on mobile while preserving desktop sizing.
		if (size === 'full') {
			return 'w-full';
		}
		if (size === 'xs') {
			return 'max-sm:w-full w-[16rem]';
		} else if (size === 'sm') {
			return 'max-sm:w-full w-[30rem]';
		} else if (size === 'md') {
			return 'max-sm:w-full w-[42rem]';
		} else if (size === 'lg') {
			return 'max-sm:w-full w-[56rem]';
		} else if (size === 'xl') {
			return 'max-sm:w-full w-[70rem]';
		} else if (size === '2xl') {
			return 'max-sm:w-full w-[84rem]';
		} else if (size === '3xl') {
			return 'max-sm:w-full w-[100rem]';
		} else {
			return 'max-sm:w-full w-[56rem]';
		}
	};

	const handleKeyDown = (event: KeyboardEvent) => {
		if (event.key === 'Escape' && isTopModal()) {
			console.log('Escape');
			show = false;
		}
	};

	const isTopModal = () => {
		const modals = document.getElementsByClassName('modal');
		return modals.length && modals[modals.length - 1] === modalElement;
	};

	const lockBodyScroll = () => {
		// iOS Safari ignores `overflow:hidden` on body — pin position instead.
		savedScrollY = window.scrollY;
		document.body.style.position = 'fixed';
		document.body.style.top = `-${savedScrollY}px`;
		document.body.style.left = '0';
		document.body.style.right = '0';
		document.body.style.overflow = 'hidden';
	};

	const unlockBodyScroll = () => {
		document.body.style.position = '';
		document.body.style.top = '';
		document.body.style.left = '';
		document.body.style.right = '';
		document.body.style.overflow = '';
		if (savedScrollY) {
			window.scrollTo(0, savedScrollY);
			savedScrollY = 0;
		}
	};

	onMount(() => {
		mounted = true;
	});

	$: if (show && modalElement) {
		document.body.appendChild(modalElement);
		focusTrap = FocusTrap.createFocusTrap(modalElement, {
			allowOutsideClick: (e) => {
				return e.target.closest('[data-sonner-toast]') !== null;
			}
		});
		focusTrap.activate();
		window.addEventListener('keydown', handleKeyDown);
		lockBodyScroll();
	} else if (modalElement) {
		focusTrap.deactivate();
		window.removeEventListener('keydown', handleKeyDown);
		document.body.removeChild(modalElement);
		unlockBodyScroll();
	}

	onDestroy(() => {
		show = false;
		if (focusTrap) {
			focusTrap.deactivate();
		}
		if (modalElement) {
			document.body.removeChild(modalElement);
		}
		unlockBodyScroll();
	});
</script>

{#if show}
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div
		bind:this={modalElement}
		aria-modal="true"
		role="dialog"
		class="modal fixed top-0 right-0 left-0 bottom-0 bg-[#191919]/30 dark:bg-[#0F0F0F]/60 w-full h-screen max-h-[100dvh] {containerClassName}  flex justify-center z-9999 overflow-y-auto overscroll-contain"
		in:fade={{ duration: 10 }}
		on:mousedown={() => {
			show = false;
		}}
	>
		<div
			class="m-auto max-w-full {sizeToWidth(size)} {size !== 'full'
				? 'mx-2'
				: ''} shadow-md min-h-fit scrollbar-hidden {className} border-hairline border-gray-200 dark:border-gray-700"
			in:flyAndScale
			on:mousedown={(e) => {
				e.stopPropagation();
			}}
		>
			<slot />
		</div>
	</div>
{/if}

<style>
	.modal-content {
		animation: scaleUp 0.1s ease-out forwards;
	}

	@keyframes scaleUp {
		from {
			transform: scale(0.985);
			opacity: 0;
		}
		to {
			transform: scale(1);
			opacity: 1;
		}
	}
</style>
