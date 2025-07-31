<script lang="ts">
	import { getAdminDetails } from '$lib/apis/auths';
	import { onMount, tick, getContext } from 'svelte';
	import { config } from '$lib/stores';
	import SplashContainer from '$lib/components/common/Splash/index.svelte';

	const i18n = getContext('i18n');

	let adminDetails = null;

	onMount(async () => {
		adminDetails = await getAdminDetails(localStorage.token).catch((err) => {
			console.error(err);
			return null;
		});
	});
</script>

<div class=" dark login min-h-screen w-full flex justify-center relative">
	<div class="relative w-full h-full flex flex-col">
		<!-- Login using Credentials button in top right corner -->

		<SplashContainer>
			<div class="tagline-container">
				<p class="waiting text-typography-titles text-[28px] leading-[36px]">
					{$i18n.t('waitList.title')}
				</p>
				<p class="text-[#979EAD] mt-5 description">
					{$i18n.t('waitList.description')}
				</p>
			</div>

			<div class=" mt-6 mx-auto relative group w-fit">
				<button
					type="button"
					class="flex h-[48px] w-[200px] sm:w-[250px] md:w-[300px] px-[16px] py-[6px] pl-[8px] justify-center items-center gap-[4px] self-stretch rounded-[12px] bg-gradient-to-r from-[#A5C7E6] via-[#CEE7FF] to-[#A5C7E6] shadow-[inset_6px_3px_8px_0_#BFDBF6]"
					on:click={async () => {
						localStorage.removeItem('token');
						location.href = '/auth';
					}}>{$i18n.t('Logout')}</button
				>
			</div>
		</SplashContainer>
	</div>
</div>

<!-- <div class="fixed w-full h-full flex z-999">
	<div
		class="absolute w-full h-full backdrop-blur-lg bg-white/10 dark:bg-gray-900/50 flex justify-center"
	>
		<div class="m-auto pb-10 flex flex-col justify-center">
			<div class="max-w-md">
				<div
					class="text-center dark:text-white text-2xl font-medium z-50"
					style="white-space: pre-wrap;"
				>
					{#if ($config?.ui?.pending_user_overlay_title ?? '').trim() !== ''}
						{$config.ui.pending_user_overlay_title}
					{:else}
						{$i18n.t('Account Activation Pending')}<br />
						{$i18n.t('Contact Admin for WebUI Access')}
					{/if}
				</div>

				<div
					class=" mt-4 text-center text-sm dark:text-gray-200 w-full"
					style="white-space: pre-wrap;"
				>
					{#if ($config?.ui?.pending_user_overlay_content ?? '').trim() !== ''}
						{$config.ui.pending_user_overlay_content}
					{:else}
						{$i18n.t('Your account status is currently pending activation.')}{'\n'}{$i18n.t(
							'To access the WebUI, please reach out to the administrator. Admins can manage user statuses from the Admin Panel.'
						)}
					{/if}
				</div>

				{#if adminDetails}
					<div class="mt-4 text-sm font-medium text-center">
						<div>{$i18n.t('Admin')}: {adminDetails.name} ({adminDetails.email})</div>
					</div>
				{/if}

				<div class=" mt-6 mx-auto relative group w-fit">
					<button
						class="relative z-20 flex px-5 py-2 rounded-full bg-white border border-gray-100 dark:border-none hover:bg-gray-100 text-gray-700 transition font-medium text-sm"
						on:click={async () => {
							location.href = '/';
						}}
					>
						{$i18n.t('Check Again')}
					</button>

					<button
						class="text-xs text-center w-full mt-2 text-gray-400 underline"
						on:click={async () => {
							localStorage.removeItem('token');
							location.href = '/auth';
						}}>{$i18n.t('Sign Out')}</button
					>
				</div>
			</div>
		</div>
	</div>
</div> -->
<style>
	@media (max-width: 768px) {
		.waiting {
			font-size: 24px;
		}

		.description {
			font-size: 12px;
		}
	}

	@media (max-width: 480px) {
		.waiting {
			font-size: 20px;
		}

		.description {
			font-size: 10px;
		}
	}
</style>
