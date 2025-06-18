<script lang="ts">
	import { getContext } from 'svelte';
	import {
		WEBUI_NAME,
		chatId,
		mobile,
		settings,
		showArchivedChats,
		showControls,
		showSidebar,
		temporaryChatEnabled,
		user,
		suggestionCycle,
		ariaMessage

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

	const i18n = getContext('i18n');

	export let initNewChat: Function;
	export let title: string = $WEBUI_NAME;
	export let shareEnabled: boolean = false;

	export let chat;
	export let selectedModels;
	export let showModelSelector = true;

	let showShareChatModal = false;
	let showDownloadChatModal = false;
	const changeFocus = async (elementId) => {
		setTimeout(() => {
			document.getElementById(elementId)?.focus();
		}, 110);
	};

	const handleNewChat = () => {
		suggestionCycle.update((n) => n + 1);
		initNewChat();
	};
</script>

<ShareChatModal bind:show={showShareChatModal} chatId={$chatId} />

<nav class="sticky top-0 z-30 w-full px-1.5 py-1.5 -mb-8 flex items-center drag-region">
	<div
		class=" bg-gradient-to-b via-50% from-white via-white to-transparent dark:from-gray-900 dark:via-gray-900 dark:to-transparent pointer-events-none absolute inset-0 -bottom-7 z-[-1] blur"
	></div>

	<div class=" flex max-w-full w-full mx-auto px-1 pt-0.5 bg-transparent">
		<div class="flex items-center w-full max-w-full">
			<div
				class="{$showSidebar
					? 'md:hidden'
					: ''} mr-1 self-start flex flex-none items-center text-gray-600 dark:text-gray-400"
			>
				<Tooltip content={$i18n.t('Show Sidebar')}>
					<button
						id="sidebar-toggle-button"
						class="m-auto self-center cursor-pointer px-2 py-2 flex rounded-xl hover:bg-gray-50 dark:hover:bg-gray-850 transition"
						on:click={async () => {
							showSidebar.set(!$showSidebar);
							ariaMessage.set($i18n.t('Sidebar expanded.'));
							await changeFocus('hide-sidebar-button');
						}}
						aria-label="Show Sidebar"
					>
						<MenuLines />
					</button>
				</Tooltip>
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
					<Tooltip content={$i18n.t('Chat Context Menu')}>
						<Menu
							{chat}
							{shareEnabled}
							buttonID={'chat-context-menu-button' + chat.id}
							buttonClass="flex cursor-pointer px-2 py-2 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-850 transition"
							ariaLabel={$i18n.t('Chat Context Menu')}
							shareHandler={() => {
								showShareChatModal = !showShareChatModal;
							}}
							downloadHandler={() => {
								showDownloadChatModal = !showDownloadChatModal;
							}}
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
						</Menu>
					</Tooltip>
				{:else if $mobile && ($user.role === 'admin' || $user?.permissions.chat?.controls)}
					<Tooltip content={$i18n.t('Controls')}>
						<button
							class="m-auto self-center flex cursor-pointer px-2 py-2 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-850 transition"
							on:click={async () => {
								await showControls.set(!$showControls);
							}}
							aria-label={$i18n.t('Controls')}
						>
							<AdjustmentsHorizontal className=" size-5" strokeWidth="0.5" />
						</button>
					</Tooltip>
				{/if}
				<Tooltip content={$i18n.t('New Chat')}>
					<button
						id="new-chat-button"
						class=" flex m-auto self-center cursor-pointer px-2 py-2 rounded-xl text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
						on:click={handleNewChat}
						aria-label={$i18n.t('New Chat')}
					>
						<PencilSquare className=" size-5" strokeWidth="2" />
					</button>
				</Tooltip>
			</div>
		</div>
	</div>
</nav>
