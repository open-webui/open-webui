<script lang="ts">
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import { fade } from 'svelte/transition';
	import { flyAndScale } from '$lib/utils/transitions';
	import CloseIcon from '$lib/components/icons/CloseIcon.svelte';

	export let title = '';
	export let message = '';

	export let noMessage = false;

	export let inputType = 'textarea';

	export let cancelLabel = $i18n.t('Cancel');
	export let confirmLabel = $i18n.t('Confirm');

	export let onConfirm = () => {};

	export let input = false;
	export let inputPlaceholder = '';
	export let inputValue = '';

	export let show = false;

	let modalElement = null;
	let mounted = false;

	const handleKeyDown = (event: KeyboardEvent) => {
		if (event.key === 'Escape') {
			console.log('Escape');
			show = false;
		}

		if (event.key === 'Enter') {
			console.log('Enter');
			confirmHandler();
		}
	};

	const confirmHandler = async () => {
		show = false;
		await onConfirm();
		dispatch('confirm', inputValue);
	};

	onMount(() => {
		mounted = true;
	});

	$: if (mounted) {
		if (show && modalElement) {
			document.body.appendChild(modalElement);

			window.addEventListener('keydown', handleKeyDown);
			document.body.style.overflow = 'hidden';
		} else if (modalElement) {
			window.removeEventListener('keydown', handleKeyDown);
			document.body.removeChild(modalElement);

			document.body.style.overflow = 'unset';
		}
	}
</script>

{#if show}
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		bind:this={modalElement}
		class=" fixed top-0 right-0 left-0 bottom-0 bg-[#1D1A1A]/50 backdrop-blur-[7.44px] w-full h-screen max-h-[100dvh] flex justify-center z-[99999999] overflow-hidden overscroll-contain"
		in:fade={{ duration: 10 }}
		on:mousedown={() => {
			show = false;
			const url = new URL(window.location.href);
			url.searchParams.delete('plans'); 
			window.history.replaceState({}, '', `${url.pathname}${url.search}`);
		}}
	>
		<div
			class=" m-auto relative rounded-2xl max-w-full w-[36rem] mx-2 bg-lightGray-550 dark:bg-customGray-800 max-h-[100dvh] shadow-3xl"
			in:flyAndScale
			on:mousedown={(e) => {
				e.stopPropagation();
			}}
		>
			<div class="px-5 py-5 flex flex-col text-left">
				<div class="mb-5 border-b border-lightGray-400 dark:border-customGray-700 flex justify-between items-center pb-2.5">
					<div
						class=" text-base text-lightGray-100 dark:text-customGray-100 text-left"
					>
						{$i18n.t('Explore Plans')}
					</div>
					<button
						class="text-customGray-300"
						on:click={() => {
							show = false;
							const url = new URL(window.location.href);
							url.searchParams.delete('plans'); 
							window.history.replaceState({}, '', `${url.pathname}${url.search}`);
						}}
					>
						<CloseIcon />
					</button>
				</div>
				<div class="min-h-[10rem]">
					<slot/>
				</div>
			</div>
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
