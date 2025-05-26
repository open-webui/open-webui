<script lang="ts">
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import { fade } from 'svelte/transition';
	import { flyAndScale } from '$lib/utils/transitions';
	import CloseIcon from '../icons/CloseIcon.svelte';

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
		class=" fixed top-0 right-0 left-0 bottom-0 bg-lightGray-250/50 dark:bg-[#1D1A1A]/50 backdrop-blur-[7.44px] w-full h-screen max-h-[100dvh] flex justify-center z-[99999999] overflow-hidden overscroll-contain"
		in:fade={{ duration: 10 }}
		on:mousedown={() => {
			show = false;
		}}
	>
		<div
			class=" m-auto relative rounded-2xl max-w-full w-[32rem] mx-2 bg-lightGray-550 dark:bg-customGray-800 max-h-[100dvh] shadow-3xl"
			in:flyAndScale
			on:mousedown={(e) => {
				e.stopPropagation();
			}}
		>
			<button
				class="absolute top-4 right-4 text-customGray-300"
				on:click={() => {
					show = false;
				}}
			>
				<CloseIcon />
			</button>

			<div class="px-10 pt-14 pb-6 py-6 flex flex-col text-center">
				<div class=" text-base text-lightGray-100 dark:text-white mb-2.5 text-center">
					{#if title !== ''}
						{title}
					{:else}
						{$i18n.t('Confirm your action')}
					{/if}
				</div>

				<slot>
					<div class=" text-sm text-gray-500 flex-1 text-center">
						{#if !noMessage}
							{#if message !== ''}
								{message}
							{:else}
								{$i18n.t('This action cannot be undone. Do you wish to continue?')}
							{/if}
						{/if}

						{#if input}
							{#if inputType === 'textarea'}
								<textarea
									bind:value={inputValue}
									placeholder={inputPlaceholder ? inputPlaceholder : $i18n.t('Enter your message')}
									class="w-full mt-2 placeholder:text-lightGray-100 dark:placeholder:text-customGray-100 rounded-md px-4 py-2 text-sm bg-lightGray-300 text-lightGray-100 dark:text-gray-300 dark:bg-customGray-900 outline-none resize-none"
									rows="3"
									required
								/>
							{:else}
								<input
									bind:value={inputValue}
									placeholder={inputPlaceholder ? inputPlaceholder : $i18n.t('Enter your message')}
									class="w-full mt-2 placeholder:text-lightGray-100 dark:placeholder:text-customGray-100 rounded-md px-4 py-3 text-sm bg-lightGray-300 text-lightGray-100 dark:text-gray-300 dark:bg-customGray-900 outline-none resize-none"
									required
								/>
							{/if}
						{/if}
					</div>
				</slot>

				<div class="mt-6 flex justify-end gap-7 font-medium">
					<button
						class="text-gray-800 w-fit text-xs dark:text-customGray-200 py-2.5 rounded-lg transition"
						on:click={() => {
							show = false;
							dispatch('cancel');
						}}
						type="button"
					>
						{cancelLabel}
					</button>
					<button
						class="bg-lightGray-300 border-lighGray-400 hover:bg-lightGray-700 text-lightGray-100 text-xs dark:bg-customGray-900 border dark:border-customGray-700 dark:hover:bg-customGray-950 dark:text-customGray-200 w-1/2 py-2.5 rounded-lg transition"
						on:click={() => {
							confirmHandler();
						}}
						type="button"
					>
						{confirmLabel}
					</button>
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
