<script lang="ts">
	import {
		showControls,
		showSidebar,
		temporaryChatEnabled,
		user,
		mobile,
		showArchivedChats,
		chatId,
		chats
	} from '$lib/stores';
	import { getContext } from 'svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import AdjustmentsHorizontal from '../icons/AdjustmentsHorizontal.svelte';
	import UserMenu from './Sidebar/UserMenu.svelte';
	import { goto } from '$app/navigation';

	interface I18n {
		t: (key: string) => string;
	}

	const i18n = getContext<I18n>('i18n');
	const t = (key: string) => i18n?.t?.(key) ?? key;

	const handleHomeClick = async () => {
		chatId.set('');
		await goto('/');
	};
</script>

<div
	class="h-[5vh] fixed w-full top-0 bg-white dark:bg-gray-900 border-b border-gray-100 dark:border-gray-800 z-100"
>
	<div class=" h-full mx-auto flex items-center px-4 w-full">
		<div class="flex items-center flex-1">
			<button
				on:click={handleHomeClick}
				class="flex items-center gap-3 p-1.5 rounded-xl"
			>
				<img src="/static/favicon.png" alt="Logo" class="h-8 w-8 rounded-full" />
				<div class="text-2xl font-bold fr-text-title--blue-france">Albert</div>
				<div
					class="px-2 py-0.5 text-xs rounded-full fr-background-action-low--blue-france fr-text-label--blue-cumulus font-bold flex items-center"
				>
					ALPHA
				</div>
			</button>
		</div>

		<div class="flex items-center gap-2">
			<!-- {#if !$mobile}
				<Tooltip content={t('Controls')}>
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
</div>
