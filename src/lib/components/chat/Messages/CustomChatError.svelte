<script lang="ts">
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	import WarningIcon from '$lib/components/icons/WarningIcon.svelte';
	import { user, subscription } from '$lib/stores';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import { fade } from 'svelte/transition';
	import { flyAndScale } from '$lib/utils/transitions';

	let modalElement = null;
	export let content = '';
	let show = true;
	let mounted = false;

	onMount(() => {
		mounted = true;
	});

	$: if (mounted) {
		if (show && modalElement) {
			document.body.appendChild(modalElement);
			document.body.style.overflow = 'hidden';
		} else if (modalElement) {
			document.body.removeChild(modalElement);
			document.body.style.overflow = 'unset';
		}
	}
</script>

{#if show}
	<div
		bind:this={modalElement}
		class=" fixed top-0 right-0 left-0 bottom-0 bg-[#1D1A1A]/50 backdrop-blur-[7.44px] w-full h-screen max-h-[100dvh] flex justify-center z-[99999999] overflow-hidden overscroll-contain"
		in:fade={{ duration: 10 }}
		on:mousedown={() => {
			// show = false;
		}}
	>
		<div
			class=" m-auto mt-[8rem] relative rounded-2xl max-w-full w-[42rem] mx-2 bg-gray-50 dark:bg-customGray-800 max-h-[100dvh] shadow-3xl"
			in:flyAndScale
			on:mousedown={(e) => {
				e.stopPropagation();
			}}
		>
			<div class="px-5 py-5 flex justify-between items-center">
				<div>
					<div class="flex items-center mb-1">
						<WarningIcon />
						<div class="ml-3 text-base dark:text-white">
							{#if $subscription?.plan !== 'free'}
								{$i18n.t('You’ve run out of credits')}
							{:else}
								{$i18n.t('Your trial period is over')}
							{/if}
						</div>
					</div>
					<div class="text-base dark:text-customGray-100 max-w-[26rem]">
						{#if $user?.role === 'admin'}
							{#if $subscription?.plan !== 'free'}
								{$i18n.t(
									'You’ve used all available credits. To continue using the platform, action is required.'
								)}
							{:else}
								{$i18n.t('To continue using the platform, please select a plan')}
							{/if}
						{:else if $subscription?.plan !== 'free'}
							{$i18n.t('Please contact your administrator to request a credit recharge')}
						{:else}
							{$i18n.t('To continue using the platform, please contact your administrator.')}
						{/if}
					</div>
				</div>
				{#if $user?.role === 'admin'}
					{#if $subscription?.plan !== 'free'}
						<a
							on:click={() => {
								show = false;
							}}
							href="/?modal=company-settings&tab=billing&recharge=open"
							class="flex items-center justify-center h-10 rounded-mdx dark:bg-customGray-900 hover:dark:bg-customGray-950 border dark:border-customGray-700 px-8 py-3 text-xs dark:text-customGray-200"
						>
							{$i18n.t('Recharge Credits')}
						</a>
					{:else}
						<a
							on:click={() => {
								show = false;
							}}
							href="/?modal=company-settings&tab=billing&plans=open"
							class="flex items-center justify-center h-10 rounded-mdx dark:bg-customGray-900 hover:dark:bg-customGray-950 border dark:border-customGray-700 px-8 py-3 text-xs dark:text-customGray-200"
						>
							{$i18n.t('Select a plan')}
						</a>
					{/if}
				{/if}
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
