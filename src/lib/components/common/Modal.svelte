<script lang="ts">
	import { onDestroy } from 'svelte';
	import { fade } from 'svelte/transition';

	import { flyAndScale } from '$lib/utils/transitions';
	import * as FocusTrap from 'focus-trap';
	import { settings } from '$lib/stores';
	import { matchKeybinding, Shortcut } from '$lib/shortcuts';
	export let show = true;
	export let size = 'md';
	export let containerClassName = 'p-3';
	export let className = 'bg-white dark:bg-gray-900 rounded-4xl';
	export let onRequestClose: (() => void) | null = null;
	export let ariaLabel: string | undefined = undefined;
	const requestClose = () => (onRequestClose ? onRequestClose() : (show = false));

	let modalElement: HTMLDivElement | null = null;
	let previousOverflow: string | null = null;
	// Create focus trap to trap user tabs inside modal
	// https://www.w3.org/WAI/WCAG21/Understanding/focus-order.html
	// https://www.w3.org/WAI/WCAG21/Understanding/keyboard.html
	let focusTrap: FocusTrap.FocusTrap | null = null;

	const sizeToWidth = (size: string) => {
		if (size === 'full') {
			return 'w-full';
		}
		if (size === 'xs') {
			return 'w-[16rem]';
		} else if (size === 'sm') {
			return 'w-[30rem]';
		} else if (size === 'md') {
			return 'w-[42rem]';
		} else if (size === 'lg') {
			return 'w-[56rem]';
		} else if (size === 'xl') {
			return 'w-[70rem]';
		} else if (size === '2xl') {
			return 'w-[84rem]';
		} else if (size === '3xl') {
			return 'w-[100rem]';
		} else {
			return 'w-[56rem]';
		}
	};

	const handleKeyDown = (event: KeyboardEvent) => {
		if (
			(event.key === 'Escape' ||
				($settings?.keyboardShortcuts !== false &&
					matchKeybinding(event) === Shortcut.CLOSE_MODAL)) &&
			!(
				event.target instanceof Element && event.target.closest('[role="menu"], [role="listbox"]')
			) &&
			isTopModal()
		) {
			requestClose();
		}
	};

	const isTopModal = () => {
		const modals = document.getElementsByClassName('modal');
		return modals.length && modals[modals.length - 1] === modalElement;
	};

	let handleOutsideInteraction: ((event: Event) => void) | undefined;
	let handleModalFocusIn: (() => void) | undefined;
	const release = () => {
		if (typeof document === 'undefined') return;
		focusTrap?.deactivate();
		focusTrap = null;
		if (handleOutsideInteraction) {
			document.removeEventListener('pointerdown', handleOutsideInteraction, true);
			window.removeEventListener('focusin', handleOutsideInteraction, true);
		}
		if (handleModalFocusIn) modalElement?.removeEventListener('focusin', handleModalFocusIn);
		window.removeEventListener('keydown', handleKeyDown);
		if (previousOverflow !== null) {
			document.body.style.overflow = previousOverflow;
			previousOverflow = null;
		}
	};

	$: if (show && modalElement) {
		document.body.appendChild(modalElement);
		focusTrap = FocusTrap.createFocusTrap(modalElement, {
			escapeDeactivates: false,
			allowOutsideClick: (e) => {
				return (
					e.target instanceof Element &&
					(e.target.closest('[data-sonner-toast]') !== null ||
						e.target.closest('.modal-content') === null)
				);
			}
		});
		focusTrap.activate();

		// Portaled menus need keyboard focus as well as pointer interaction.
		handleOutsideInteraction = (e) => {
			if (
				focusTrap &&
				modalElement &&
				e.target instanceof Node &&
				!modalElement.contains(e.target) &&
				(e.type === 'pointerdown' ||
					(e.target instanceof Element && e.target.closest('[role="menu"], [role="listbox"]')))
			) {
				focusTrap.pause();
			}
		};
		handleModalFocusIn = () => {
			if (focusTrap) {
				focusTrap.unpause();
			}
		};
		document.addEventListener('pointerdown', handleOutsideInteraction, true);
		window.addEventListener('focusin', handleOutsideInteraction, true);
		modalElement.addEventListener('focusin', handleModalFocusIn);

		window.addEventListener('keydown', handleKeyDown);
		previousOverflow = document.body.style.overflow;
		document.body.style.overflow = 'hidden';
	} else if (modalElement) {
		release();
		modalElement.remove();
	}

	onDestroy(() => {
		show = false;
		release();
		if (modalElement && modalElement.parentNode === document.body) {
			document.body.removeChild(modalElement);
		}
	});
</script>

{#if show}
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div
		bind:this={modalElement}
		aria-modal="true"
		aria-label={ariaLabel}
		role="dialog"
		tabindex="-1"
		class="modal fixed top-0 right-0 left-0 bottom-0 bg-black/45 dark:bg-black/60 w-full h-screen max-h-[100dvh] {containerClassName}  flex justify-center z-9999 overflow-y-auto overscroll-contain"
		style="scrollbar-gutter: stable;"
		in:fade={{ duration: 10 }}
		on:mousedown={requestClose}
	>
		<div
			class="m-auto max-w-full {sizeToWidth(size)} {size !== 'full'
				? 'mx-2'
				: ''} shadow-3xl min-h-fit scrollbar-hidden {className} border border-white dark:border-gray-850"
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
