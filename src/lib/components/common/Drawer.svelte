<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { flyAndScale } from '$lib/utils/transitions';
	import { fade, fly, slide } from 'svelte/transition';
	import * as FocusTrap from 'focus-trap';
	import { settings } from '$lib/stores';
	import { matchKeybinding, Shortcut } from '$lib/shortcuts';

	export let show = false;
	export let className = '';
	export let zIndexClass = 'z-999';
	export let panelStyle = '';
	export let backdropStyle = '';
	export let swipeSide: 'left' | 'right' | undefined = undefined;
	export let onClose = () => {};
	export let onRequestClose: (() => void) | null = null;
	export let ariaLabel: string | undefined = undefined;
	const requestClose = () => (onRequestClose ? onRequestClose() : (show = false));

	let modalElement = null;
	let mounted = false;
	let focusTrap: FocusTrap.FocusTrap | null = null;

	const handleKeyDown = (event: KeyboardEvent) => {
		if (
			(event.key === 'Escape' ||
				($settings?.keyboardShortcuts !== false &&
					matchKeybinding(event) === Shortcut.CLOSE_MODAL)) &&
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
		focusTrap?.deactivate();
		focusTrap = null;
		if (handleOutsideInteraction) {
			document.removeEventListener('pointerdown', handleOutsideInteraction, true);
			window.removeEventListener('focusin', handleOutsideInteraction, true);
		}
		if (handleModalFocusIn) modalElement?.removeEventListener('focusin', handleModalFocusIn);
	};

	onMount(() => {
		mounted = true;
	});

	$: if (show && modalElement) {
		if (modalElement.parentElement !== document.body) document.body.appendChild(modalElement);
		if (!focusTrap) {
			focusTrap = FocusTrap.createFocusTrap(modalElement, {
				escapeDeactivates: false,
				allowOutsideClick: true,
				fallbackFocus: modalElement
			});
			focusTrap.activate();

			handleOutsideInteraction = (e) => {
				if (
					focusTrap &&
					modalElement &&
					e.target instanceof Node &&
					!modalElement.contains(e.target) &&
					(e.type === 'pointerdown' ||
						(e.target instanceof Element &&
							e.target.closest('[role="menu"], [role="listbox"], [role="combobox"]')))
				) {
					focusTrap.pause();
				} else if (
					focusTrap &&
					modalElement &&
					e.target instanceof Element &&
					modalElement.compareDocumentPosition(e.target) & Node.DOCUMENT_POSITION_PRECEDING &&
					!e.target.closest('[data-sonner-toast]')
				) {
					focusTrap.unpause();
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
		}
		window.addEventListener('keydown', handleKeyDown);
		document.body.style.overflow = 'hidden';
	} else if (modalElement) {
		onClose();
		release();
		window.removeEventListener('keydown', handleKeyDown);

		if (document.body.contains(modalElement)) {
			document.body.removeChild(modalElement);
			document.body.style.overflow = 'unset';
		}
	}

	onDestroy(() => {
		release();
		window.removeEventListener('keydown', handleKeyDown);
		show = false;
		if (modalElement) {
			if (document.body.contains(modalElement)) {
				document.body.removeChild(modalElement);
				document.body.style.overflow = 'unset';
			}
		}
	});
</script>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-static-element-interactions -->
{#if show}
	<div
		bind:this={modalElement}
		aria-modal="true"
		aria-label={ariaLabel}
		role="dialog"
		tabindex="-1"
		data-swipe-panel={swipeSide}
		class="modal fixed right-0 bottom-0 left-0 {zIndexClass} flex h-screen max-h-[100dvh] w-full justify-center overflow-hidden overscroll-contain {swipeSide
			? ''
			: 'bg-black/60'}"
		in:fly={{ y: swipeSide ? 0 : 100, duration: swipeSide ? 0 : 100 }}
		on:mousedown={requestClose}
	>
		{#if swipeSide}
			<div class="absolute inset-0 bg-black" style={backdropStyle}></div>
		{/if}
		<div
			class="{swipeSide
				? 'relative'
				: ''} mt-auto w-full bg-gray-50 dark:bg-gray-900 dark:text-gray-100 {className} scrollbar-hidden max-h-[100dvh] overflow-y-auto"
			style={panelStyle}
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
