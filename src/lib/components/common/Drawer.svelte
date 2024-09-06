<script lang="ts">
	import { onDestroy, onMount, createEventDispatcher } from 'svelte';
	import { flyAndScale } from '$lib/utils/transitions';
	import { fade, fly, slide } from 'svelte/transition';

	export let show = false;
	export let size = 'md';

	let modalElement = null;
	let mounted = false;

	const sizeToWidth = (size) => {
		if (size === 'xs') {
			return 'w-[16rem]';
		} else if (size === 'sm') {
			return 'w-[30rem]';
		} else if (size === 'md') {
			return 'w-[48rem]';
		} else {
			return 'w-[56rem]';
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

	onMount(() => {
		mounted = true;
	});

	$: if (show && modalElement) {
		document.body.appendChild(modalElement);
		window.addEventListener('keydown', handleKeyDown);
		document.body.style.overflow = 'hidden';
	} else if (modalElement) {
		window.removeEventListener('keydown', handleKeyDown);
		document.body.removeChild(modalElement);
		document.body.style.overflow = 'unset';
	}

	onDestroy(() => {
		show = false;
		if (modalElement) {
			document.body.removeChild(modalElement);
		}
	});
</script>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-static-element-interactions -->

<div
	bind:this={modalElement}
	class="modal fixed right-0 left-0 bottom-0 bg-black/60 w-full h-screen max-h-[100dvh] flex justify-center z-[9999] overflow-hidden overscroll-contain"
	in:fly={{ y: 100, duration: 100 }}
	on:mousedown={() => {
		show = false;
	}}
>
	<div
		class=" mt-auto max-w-full w-full bg-gray-50 dark:bg-gray-900 max-h-[100dvh] overflow-y-auto scrollbar-hidden"
		on:mousedown={(e) => {
			e.stopPropagation();
		}}
	>
		<slot />
	</div>
</div>

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
