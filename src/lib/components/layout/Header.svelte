<script lang="ts">
	import { user, showArchivedChats, chatId, showFeedbackBanner } from '$lib/stores';
	import { getContext as _g } from 'svelte';
	import UserMenu from './Sidebar/UserMenu.svelte';
	import { goto } from '$app/navigation';
	import type { i18n as i18nType } from 'i18next';

	const i18n = _g<any>('i18n');

	const _x = _g<any>('show');

	const handleHomeClick = async () => {
		chatId.set('');
		await goto('/');
	};
</script>

<div
	class="h-[5vh] fixed w-full top-0 bg-white dark:bg-gray-900 border-b border-gray-100 dark:border-gray-800 z-100 mb-50"
>
	<div class=" h-full mx-auto flex items-center px-4 w-full">
		<div class="flex items-center flex-1">
			<button on:click={handleHomeClick} class="flex items-center gap-3 p-1.5 rounded-xl">
				<img src="/static/favicon.png" alt="Logo" class="h-8 w-8 rounded-full" />
				{#if $_x}
					<img src="/cam.svg" alt="@cam" class="h-14 mt-[3.7vh]" />
				{:else}
					<div class="text-2xl font-bold fr-text-title--blue-france">Albert</div>
				{/if}
				<div
					class="px-2 py-0.5 text-xs rounded-full fr-background-action-low--blue-france fr-text-label--blue-cumulus font-bold flex items-center"
				>
					BETA
				</div>
			</button>
		</div>

		<div class="flex items-center gap-2">
			<!-- {#if !$mobile}
				<Tooltip content={$i18n.t('Controls')}>
					<button
						class="flex cursor-pointer px-2 py-2 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-850 transition text-gray-600 dark:text-gray-400"
						on:click={async () => {
							await showControls.set(!$showControls);
						}}
						aria-label="Controls"
					>
						<div class="m-auto self-center">
							<AdjustmentsHorizontal className="size-5" strokeWidth="0.5" />
						</div>
					</button>
				</Tooltip>
			{/if} -->

			{#if $user !== undefined}
				<UserMenu
					className="max-w-[200px]"
					role={$user.role}
					on:show={(e) => {
						if (e.detail === 'archived-chat') {
							showArchivedChats.set(true);
						}
					}}
				>
					<button
						class="select-none flex rounded-xl p-1.5 w-full hover:bg-gray-50 dark:hover:bg-gray-850 transition"
						aria-label="User Menu"
					>
						<div class="self-center">
							<img
								src={$user.profile_image_url}
								class="size-6 object-cover rounded-full"
								alt="User profile"
								draggable="false"
							/>
						</div>
					</button>
				</UserMenu>
			{/if}
		</div>
	</div>
	{#if $showFeedbackBanner && $user !== undefined && $user !== null}
		<div
			class="w-full bg-blue-50 dark:bg-blue-900/80 flex items-center relative py-4 sm:py-0 sm:h-[3.5vh] border-b border-blue-100 dark:border-blue-800/30"
		>
			<div class="mx-auto flex flex-col sm:flex-row sm:gap-3 px-4 sm:px-0">
				<span class="text-sm text-gray-700 dark:text-gray-200 align-middle">
					💬 {$i18n.t('We would love to hear what you think about Albert')}
				</span>
				<a
					href="https://grist.numerique.gouv.fr/o/albert/forms/3YqFNWKSkYjLTK9quzcSLq/75"
					class="text-sm font-medium text-blue-600 dark:text-blue-400 hover:underline underline-offset-2"
					target="_blank"
					rel="noopener noreferrer"
				>
					{$i18n.t('Share your feedback (french)')}
				</a>
			</div>

			<button
				on:click={() => {
					showFeedbackBanner.set(false);
					localStorage.setItem('dismissedFeedbackBanner', 'true');
				}}
				class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 absolute right-2"
				aria-label={$i18n.t('Dismiss banner')}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					class="h-4 w-4"
					viewBox="0 0 20 20"
					fill="currentColor"
				>
					<path
						fill-rule="evenodd"
						d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
						clip-rule="evenodd"
					/>
				</svg>
			</button>
		</div>
	{/if}
</div>
