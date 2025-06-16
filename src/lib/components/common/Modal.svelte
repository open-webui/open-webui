<script lang="ts">
	import { onDestroy, onMount, getContext } from 'svelte';
	import { fade } from 'svelte/transition';
	import { flyAndScale } from '$lib/utils/transitions';
	import * as focusTrap from 'focus-trap';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	export let show = true;
	export let size = 'md';
	export let containerClassName = 'p-3';
	export let className = 'bg-gray-50 dark:bg-gray-900 rounded-2xl';
	export let disableClose = false;
	export let title = '';

	// New props for custom focus behavior:
	export let initialFocusSelector = ''; // e.g. '#first-input'
	export let returnFocusSelector = ''; // e.g. '#open-button'

	let modalElement: HTMLElement;
	let contentEl: HTMLElement;
	let mounted = false;
	let trap: any = null;

	const sizeToWidth = (size: string) => {
		if (size === 'full') return 'w-full';
		if (size === 'xs') return 'w-[16rem]';
		if (size === 'sm') return 'w-[30rem]';
		if (size === 'md') return 'w-[42rem]';
		return 'w-[56rem]';
	};

	const handleKeyDown = (event: KeyboardEvent) => {
		if (event.key === 'Escape' && isTopModal() && !disableClose) {
			show = false;
		}
	};

	const isTopModal = () => {
		const modals = document.getElementsByClassName('modal');
		return modals.length && modals[modals.length - 1] === modalElement;
	};

	onMount(() => {
		mounted = true;
	});

	$: if (show && modalElement) {
		document.body.appendChild(modalElement);
		window.addEventListener('keydown', handleKeyDown);
		document.body.style.overflow = 'hidden';
		toast.announce($i18n.t('modalOpened', { title: title }));
	} else if (modalElement) {
		window.removeEventListener('keydown', handleKeyDown);
		document.body.removeChild(modalElement);
		document.body.style.overflow = 'unset';
		toast.announce($i18n.t('modalClosed', { title: title }));
	}

	// Set up the focus trap using custom selectors if provided.
	$: if (show && contentEl && !trap) {
		const config: any = {
			clickOutsideDeactivates: true,
			// This makes the trap record the active element automatically
			returnFocusOnDeactivate: true,
			// Use the provided initial focus selector if available
			initialFocus: initialFocusSelector
				? () => contentEl.querySelector(initialFocusSelector)
				: undefined,
			// Override onDeactivate if a custom return focus selector is provided:
			onDeactivate: () => {
				if (returnFocusSelector) {
					const returnEl = document.querySelector(returnFocusSelector);
					if (returnEl) {
						returnEl.focus();
						return;
					}
				}
			}
		};
		trap = focusTrap.createFocusTrap(contentEl, config);
		trap.activate();
	} else if (!show && trap) {
		trap.deactivate();
		trap = null;
	}

	onDestroy(() => {
		show = false;
		if (trap) {
			trap.deactivate();
			trap = null;
		}
		if (modalElement && document.body.contains(modalElement)) {
			document.body.removeChild(modalElement);
		}
	});
</script>

{#if show}
	<div
		bind:this={modalElement}
		class="modal fixed top-0 right-0 left-0 bottom-0 bg-black/60 w-full h-screen max-h-[100dvh] {containerClassName} flex justify-center z-[9999] overflow-y-auto overscroll-contain"
		in:fade={{ duration: 10 }}
		on:mousedown={() => {
			if (!disableClose) show = false;
		}}
	>
		<div
			bind:this={contentEl}
			class=" m-auto max-w-full {sizeToWidth(size)} {size !== 'full'
				? 'mx-2'
				: ''} shadow-3xl min-h-fit scrollbar-hidden {className}"
			in:flyAndScale
			on:mousedown={(e) => {
				e.stopPropagation();
			}}
		>
			<slot />
		</div>
	</div>
{/if}
