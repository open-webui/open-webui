<script lang="ts">
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	import WarningIcon from '$lib/components/icons/WarningIcon.svelte';
	import { user, subscription, isBlocked, blockedMessage } from '$lib/stores';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import { fade } from 'svelte/transition';
	import { flyAndScale } from '$lib/utils/transitions';

	let modalElement = null;
	export let content = '';
	let mounted = false;

	let errorType = null;
	$: {
		if ($blockedMessage?.includes('Insufficient credits')) {
			errorType = 'credits';
		} else if ($blockedMessage?.includes('No active subscription found')) {
			errorType = 'subscription';
		} else if ($blockedMessage?.includes('You have reached the maximum number of seats')) {
			errorType = 'seats';
		}
	}

	onMount(() => {
		mounted = true;
	});

	$: if (mounted) {
		if (modalElement) {
			document.body.appendChild(modalElement);
			document.body.style.overflow = 'hidden';
		} else if (modalElement) {
			document.body.removeChild(modalElement);
			document.body.style.overflow = 'unset';
		}
	}
</script>

<div
	bind:this={modalElement}
	class=" fixed top-0 right-0 left-0 bottom-0 bg-[#1D1A1A]/50 backdrop-blur-[7.44px] w-full h-screen max-h-[100dvh] flex justify-center z-[99999999] overflow-hidden overscroll-contain"
	in:fade={{ duration: 10 }}
	on:mousedown={() => {
		// show = false;
	}}
>
	<div
		class=" m-auto relative rounded-2xl max-w-full w-[27rem] mx-2 bg-gray-50 dark:bg-customGray-800 max-h-[100dvh] shadow-3xl"
		in:flyAndScale
		on:mousedown={(e) => {
			e.stopPropagation();
		}}
	>
		{#if errorType === 'credits'}
			<div class="px-5 py-5 flex flex-col items-center">
				<WarningIcon />
				<div class="mt-5">
					<div class="flex items-center mb-1">
						
						<div class="text-base dark:text-white text-center w-full font-medium">
							{$i18n.t('You’ve run out of credits')}
						</div>
					</div>
					<div class="text-base dark:text-customGray-100 max-w-[26rem]">
						{#if $user?.role === 'admin'}
							{$i18n.t(
								'You’ve used all available credits. To continue using the platform, action is required.'
							)}
						{:else}
							{$i18n.t('Please contact your administrator to request a credit recharge')}
						{/if}
					</div>
				</div>
				{#if $user?.role === 'admin'}
					<div class="mt-5">
						<a
							on:click={() => {
								// show = false;
								{
									isBlocked.set(false);
								}
							}}
							href="/?modal=company-settings&tab=billing&recharge=open"
							class="flex items-center justify-center h-10 rounded-mdx dark:bg-customGray-900 hover:dark:bg-customGray-950 border dark:border-customGray-700 px-8 py-3 text-xs dark:text-customGray-200"
						>
							{$i18n.t('Recharge Credits')}
						</a>
					</div>
				{/if}
			</div>
		{:else if errorType === 'subscription'}
			<div class="px-5 py-5 flex flex-col items-center">
				<WarningIcon />
				<div class="mt-5">
					<div class="flex items-center mb-1">
						
						<div class="text-base dark:text-white text-center w-full font-medium">
							{$i18n.t('No active subscription found')}
						</div>
					</div>
					<div class="text-base dark:text-customGray-100 max-w-[26rem]">
						{#if $user?.role === 'admin'}
							{$i18n.t('To continue using the platform, please select a plan')}
						{:else}
							{$i18n.t('To continue using the platform, please contact your administrator.')}
						{/if}
					</div>
				</div>
				{#if $user?.role === 'admin'}
					<div class="mt-5">
						<a
							on:click={() => {
								// show = false;
								{
									isBlocked.set(false);
								}
							}}
							href="/?modal=company-settings&tab=billing&plans=open"
							class="flex items-center justify-center h-10 rounded-mdx dark:bg-customGray-900 hover:dark:bg-customGray-950 border dark:border-customGray-700 px-8 py-3 text-xs dark:text-customGray-200"
						>
							{$i18n.t('Select a plan')}
						</a>
					</div>
				{/if}
			</div>
		{:else if (errorType === 'seats')}
		<div class="px-5 py-5 flex flex-col items-center">
			<WarningIcon />
			<div class="mt-5">
				<div class="flex items-center mb-1">
					
					<div class="text-base dark:text-white text-center w-full font-medium">
						{$i18n.t('You have reached the maximum number of seats in your subscription.')}
					</div>
				</div>
				<div class="text-base dark:text-customGray-100 max-w-[26rem]">
					{#if $user?.role === 'admin'}
						{$i18n.t('Please upgrade your plan or remove some users.')}
					{:else}
						{$i18n.t('To continue using the platform, please contact your administrator.')}
					{/if}
				</div>
			</div>
			{#if $user?.role === 'admin'}
				<div class="mt-5">
					<a
						on:click={() => {
							// show = false;
							{
								isBlocked.set(false);
							}
						}}
						href="/?modal=company-settings&tab=billing"
						class="flex items-center justify-center h-10 rounded-mdx dark:bg-customGray-900 hover:dark:bg-customGray-950 border dark:border-customGray-700 px-8 py-3 text-xs dark:text-customGray-200"
					>
						{$i18n.t('Manage Billing')}
					</a>
				</div>
			{/if}
		</div>
		{/if}
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
