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
		config,
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

			{#if $config?.features?.pbmm_env === true}
				<div class="self-start flex flex-none items-center text-gray-600 dark:text-gray-400 mr-2">
					<Tooltip content={$i18n.t('PROTECTED B')}>
						<div
							class="absolute left-1/2 -translate-x-1/2 top-1/2 -translate-y-1/2 pointer-events-none z-10 hidden sm:block"
						>
							<div
								class="text-xs leading-tight font-bold text-gray-600 dark:text-gray-400 uppercase tracking-widest"
							>
								{$i18n.t('PROTECTED B')}
							</div>
						</div>
					</Tooltip>
				</div>
			{/if}

			<div class="self-start flex flex-none items-center text-gray-600 dark:text-gray-400">
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
