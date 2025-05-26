<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

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
		company
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
	import ChevronDown from '../icons/ChevronDown.svelte';


	import PencilSquare from '../icons/PencilSquare.svelte';
	import ShowSidebarIcon from '../icons/ShowSidebarIcon.svelte';
	import MenuIcon from '../icons/MenuIcon.svelte';
	import Plus from '../icons/Plus.svelte';

	const i18n = getContext('i18n');

	export let initNewChat: Function;
	export let title: string = $WEBUI_NAME;
	export let shareEnabled: boolean = false;

	export let chat;
	export let selectedModels;
	export let showModelSelector = true;

	let showShareChatModal = false;
	let showDownloadChatModal = false;

	let showDropdown = false;
</script>

<ShareChatModal bind:show={showShareChatModal} chatId={$chatId} />

<nav class="sticky top-0 z-30 {$mobile ? 'bg-lightGray-300 dark:bg-customGray-900' : 'bg-transparent'} w-full px-1.5 py-1.5 -mb-12 flex items-center drag-region h-12">
	<!-- <div
		class="{$mobile ? 'bg-lightGray-300 dark:bg-customGray-900' : 'bg-transparent'} pointer-events-none absolute inset-0 -bottom-7 z-[-1]"
	></div> -->

	<div class=" max-w-full w-full mx-auto px-1 pt-0.5 bg-transparent">
		<div class="flex items-center w-full max-w-full">
			<div
				class="{$showSidebar
					? 'md:hidden'
					: ''} mr-1 self-center flex flex-none items-center text-gray-600 dark:text-gray-400"
			>
				<button
					id="sidebar-toggle-button"
					class="cursor-pointer flex justify-center items-center w-[25px] h-[25px] rounded-lg hover:bg-gray-100 dark:hover:bg-customGray-900 border border-transparent dark:hover:border-customGray-700 transition"
					on:click={() => {
						showSidebar.set(!$showSidebar);
					}}
					aria-label="Toggle Sidebar"
				>
					<div class="flex items-center">
						{#if ($mobile)}
							<MenuIcon/>
						{:else}
							<ShowSidebarIcon/>
						{/if}	
					</div>
				</button>
			</div>

			<div
				class="flex-1 overflow-hidden max-w-full py-0.5
			{$showSidebar ? 'ml-1' : ''}
			"
			>
			{#if ($mobile)}
			<div class="flex flex-col font-primary">
				{#if $user !== undefined}
					<UserMenu
						role={$user.role}
						on:show={(e) => {
							if (e.detail === 'archived-chat') {
								showArchivedChats.set(true);
							}
						}}
					>
						<button
							class=" flex items-center rounded-xl px-2.5 w-full transition"
							on:click={() => {
								showDropdown = !showDropdown;
							}}
						>
							<div class=" self-center mr-3">
								<img
									src={$company?.profile_image_url}
									class=" max-w-[28px] object-cover rounded-md"
									alt="User profile"
								/>
							</div>
							<div class=" self-center font-medium text-sm mr-1 text-lightGray-1300 dark:text-customGray-100">{$company?.name}</div>
							<ChevronDown className=" size-3" strokeWidth="2.5" />
						</button>
					</UserMenu>
				{/if}
			</div>
			{/if}
			
			<!-- {#if showModelSelector}
				<ModelSelector bind:selectedModels showSetDefault={!shareEnabled} />
			{/if} -->
			</div> 

			<div class="self-start flex flex-none items-center text-gray-600 dark:text-gray-400">
				
				<!-- {#if shareEnabled && chat && (chat.id || $temporaryChatEnabled)}
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
				{:else if $mobile && ($user.role === 'admin' || $user?.permissions.chat?.controls)}
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
				{/if} -->
<!-- 
				{#if !$mobile && ($user.role === 'admin' || $user?.permissions.chat?.controls)}
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
				{/if} -->

				<!-- {#if ($mobile)} -->
					<button
						id="new-chat-button"
						class="md:hidden cursor-pointer font-medium flex justify-center items-center flex-1 rounded-lg text-xs px-3 py-1 border border-lightGray-400 dark:border-customGray-700 h-[35px] text-right text-lightGray-100 dark:text-customGray-200 dark:hover:text-white bg-lightGray-300 dark:bg-customGray-900 hover:bg-gray-100 dark:hover:bg-customGray-950 transition"
						on:click={() => {
							initNewChat();
						}}
						aria-label="New Chat"
					>
					<div class="relative bottom-[0.5px] mr-[6px]">
						<Plus className="w-[12px] h-[12px]" />
					</div>
						{$i18n.t('New Chat')}	
					</button>
				<!-- {/if} -->

				<!-- {#if $user !== undefined}
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
							<div class=" self-center">
								<img
									src={$user.profile_image_url}
									class="size-6 object-cover rounded-full"
									alt="User profile"
									draggable="false"
								/>
							</div>
						</button>
					</UserMenu>
				{/if} -->
			</div>
		</div>
	</div>
</nav>
