<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { fade } from 'svelte/transition';

	import { flyAndScale } from '$lib/utils/transitions';

	export let show = true;
	export let size = 'md';
	export let containerClassName = 'p-3';
	export let className = 'bg-gray-50 dark:bg-gray-900 rounded-2xl';

	let modalElement = null;
	let mounted = false;

	const sizeToWidth = (size) => {
        if (size === 'full') {
            return 'w-full';
        } else if (size === 'xs') {
            return 'w-[16rem]';
        } else if (size === 'sm') {
            return 'w-[30rem]';
        } else if (size === 'md') {
            return 'w-[42rem]';
        } else if (size === 'lg') {
            return 'w-[56rem]';
        } else if (size === 'xl') {
            return 'w-[64rem]';
        } else if (size === '2xl') {
            return 'w-[72rem]';
        } else if (size === '3xl') {
            return 'w-[80rem]';
        } else if (size === '4xl') {
            return 'w-[84rem]';
        } else if (size === '5xl') {
            return 'w-[88rem]';
        } else if (size === '6xl') {
            return 'w-[92rem]';
        } else if (size === '7xl') {
            return 'w-[96rem]';
        } else if (size === '8xl') {
            return 'w-[100rem]';
        } else if (size === '9xl') {
            return 'w-[90vw]';  // 90% of viewport width
        } else if (size === '10xl') {
            return 'w-[95vw]';  // 95% of viewport width
        } else if (size === '11xl') {
            return 'w-[98vw]';  // 98% of viewport width
        } else if (size === '12xl') {
            return 'w-[99vw]';  // 99% of viewport width
        } else {
            return 'w-[56rem]';  // Default fallback
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

{#if show}
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		bind:this={modalElement}
		class="modal fixed top-0 right-0 left-0 bottom-0 bg-black/60 w-full h-screen max-h-[100dvh] {containerClassName} flex justify-center z-9999 overflow-y-auto overscroll-contain"
		in:fade={{ duration: 10 }}
		on:mousedown={() => {
			show = false;
		}}
	>
		<div
			class="m-auto max-w-full {sizeToWidth(size)} {size !== 'full'
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
