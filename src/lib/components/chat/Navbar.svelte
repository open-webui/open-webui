<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		WEBUI_NAME,
		banners,
		chatId,
		config,
		mobile,
		settings,
		showArchivedChats,
		showControls,
		showSidebar,
		temporaryChatEnabled,
		user
	} from '$lib/stores';

	import { slide } from 'svelte/transition';
	import { page } from '$app/stores';

	import ShareChatModal from '../chat/ShareChatModal.svelte';
	import ModelSelector from '../chat/ModelSelector.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Menu from '$lib/components/layout/Navbar/Menu.svelte';
	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import MenuLines from '../icons/MenuLines.svelte';
	import AdjustmentsHorizontal from '../icons/AdjustmentsHorizontal.svelte';

	import PencilSquare from '../icons/PencilSquare.svelte';
	import Banner from '../common/Banner.svelte';

	const i18n = getContext('i18n');

	export let initNewChat: Function;
	export let title: string = $WEBUI_NAME;
	export let shareEnabled: boolean = false;

	export let chat;
	export let history;
	export let selectedModels;
	export let showModelSelector = true;

	let showShareChatModal = false;
	let showDownloadChatModal = false;
</script>

<ShareChatModal bind:show={showShareChatModal} chatId={$chatId} />

<button
	id="new-chat-button"
	class="hidden"
	on:click={() => {
		initNewChat();
	}}
	aria-label="New Chat"
/>

<nav class="sticky top-0 z-30 w-full py-1 -mb-8 flex flex-col items-center drag-region">
	<div class="flex items-center w-full pl-1.5 pr-1">
		<div
			class=" bg-linear-to-b via-50% from-white via-white to-transparent dark:from-gray-900 dark:via-gray-900 dark:to-transparent pointer-events-none absolute inset-0 -bottom-7 z-[-1]"
		></div>

		<div class=" flex max-w-full w-full mx-auto px-1 pt-0.5 bg-transparent">
			<div class="flex items-center w-full max-w-full">
				<div
					class="{$showSidebar
						? 'md:hidden'
						: ''} mr-1 self-start flex flex-none items-center text-gray-600 dark:text-gray-400"
				>
					<button
						id="sidebar-toggle-button"
						class="cursor-pointer px-2 py-2 flex rounded-xl hover:bg-gray-50 dark:hover:bg-gray-850 transition"
						on:click={() => {
							showSidebar.set(!$showSidebar);
						}}
						aria-label="Toggle Sidebar"
					>
						<div class=" m-auto self-center">
							<MenuLines />
						</div>
					</button>

					{#if !$mobile}
						<Tooltip content={$i18n.t('New Chat')}>
							<button
								class=" flex {$showSidebar
									? 'md:hidden'
									: ''} cursor-pointer px-2 py-2 rounded-xl text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
								on:click={() => {
									initNewChat();
								}}
								aria-label="New Chat"
							>
								<div class=" m-auto self-center">
									<PencilSquare className=" size-5" strokeWidth="2" />
								</div>
							</button>
						</Tooltip>
					{/if}
				</div>

				<div
					class="flex-1 overflow-hidden max-w-full py-0.5
			{$showSidebar ? 'ml-1' : ''}
			"
				>
					{#if showModelSelector}
						<ModelSelector bind:selectedModels showSetDefault={!shareEnabled} />
					{/if}
				</div>

				<div class="self-start flex flex-none items-center text-gray-600 dark:text-gray-400">
					<!-- <div class="md:hidden flex self-center w-[1px] h-5 mx-2 bg-gray-300 dark:bg-stone-700" /> -->
					{#if shareEnabled && chat && (chat.id || $temporaryChatEnabled)}
						<Menu
							{chat}
							{shareEnabled}
							shareHandler={() => {
								showShareChatModal = !showShareChatModal;
							}}
							downloadHandler={() => {
								showDownloadChatModal = !showDownloadChatModal;
							}}
						>
							<button
								class="flex cursor-pointer px-2 py-2 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-850 transition"
								id="chat-context-menu-button"
							>
								<div class=" m-auto self-center">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="1.5"
										stroke="currentColor"
										class="size-5"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M6.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0ZM12.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0ZM18.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Z"
										/>
									</svg>
								</div>
							</button>
						</Menu>
					{/if}

					<Tooltip content={$i18n.t('Controls')}>
						<button
							class=" flex cursor-pointer px-2 py-2 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-850 transition"
							on:click={async () => {
								await showControls.set(!$showControls);
							}}
							aria-label="Controls"
						>
							<div class=" m-auto self-center">
								<AdjustmentsHorizontal className=" size-5" strokeWidth="0.5" />
							</div>
						</button>
					</Tooltip>

					{#if $user !== undefined && $user !== null}
						<UserMenu
							className="max-w-[240px]"
							role={$user?.role}
							help={true}
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
								<div class=" self-center">
									<img
										src={$user?.profile_image_url}
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
	</div>

	{#if $temporaryChatEnabled && $chatId === 'local'}
		<div class=" w-full z-30 text-center">
			<div class="text-xs text-gray-500">{$i18n.t('Temporary Chat')}</div>
		</div>
	{/if}

	{#if !history.currentId && !$chatId && ($banners.length > 0 || ($config?.license_metadata?.type ?? null) === 'trial' || (($config?.license_metadata?.seats ?? null) !== null && $config?.user_count > $config?.license_metadata?.seats))}
		<div class=" w-full z-30 mt-5">
			<div class=" flex flex-col gap-1 w-full">
				{#if ($config?.license_metadata?.type ?? null) === 'trial'}
					<Banner
						banner={{
							type: 'info',
							title: 'Trial License',
							content: $i18n.t(
								'You are currently using a trial license. Please contact support to upgrade your license.'
							)
						}}
					/>
				{/if}

				{#if ($config?.license_metadata?.seats ?? null) !== null && $config?.user_count > $config?.license_metadata?.seats}
					<Banner
						banner={{
							type: 'error',
							title: 'License Error',
							content: $i18n.t(
								'Exceeded the number of seats in your license. Please contact support to increase the number of seats.'
							)
						}}
					/>
				{/if}

				{#each $banners.filter( (b) => (b.dismissible ? !JSON.parse(localStorage.getItem('dismissedBannerIds') ?? '[]').includes(b.id) : true) ) as banner}
					<Banner
						{banner}
						on:dismiss={(e) => {
							const bannerId = e.detail;

							localStorage.setItem(
								'dismissedBannerIds',
								JSON.stringify(
									[
										bannerId,
										...JSON.parse(localStorage.getItem('dismissedBannerIds') ?? '[]')
									].filter((id) => $banners.find((b) => b.id === id))
								)
							);
						}}
					/>
				{/each}
			</div>
		</div>
	{/if}
</nav>
