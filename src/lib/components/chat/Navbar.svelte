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
	import Logo from '../icons/Logo.svelte';
	import LightMode from '../icons/LightMode.svelte';
	import DarkMode from '../icons/DarkMode.svelte';

	import PencilSquare from '../icons/PencilSquare.svelte';
	import Banner from '../common/Banner.svelte';

	import MaterialIcon from '$lib/components/common/MaterialIcon.svelte';


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
	let isOn = false;
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

<nav class="w-full flex items-center justify-between px-4 py-0 h-[56px] relative z-30 { $mobile ? 'bg-white dark:bg-gray-900 border-b border-[#dee0e3] dark:border-gray-800' : 'bg-transparent' }">
  {#if $mobile}
    <button
      class="flex items-center justify-center rounded-lg size-10 hover:bg-[#e5e7eb] transition"
      aria-label="Toggle Sidebar"
      on:click={() => showSidebar.set(!$showSidebar)}
    >
      <MaterialIcon name="menu" className="w-6 h-6" />
    </button>
    <button
      class="flex items-center justify-center rounded-lg size-10 hover:bg-[#e5e7eb] transition"
      aria-label="New Chat"
      on:click={() => initNewChat()}
    >
      <MaterialIcon name="add" className="w-[18px] h-[18px]" />
    </button>
  {:else}

  <img
	src="/logo-dark.png"
	alt="GovGPT Logo"
	class="w-[132px] h-[40px] filter dark:invert dark:brightness-0 dark:contrast-200"
	/>

	<!--<div
				class="flex-1 overflow-hidden max-w-full py-0.5
			{$showSidebar ? 'ml-1' : ''}
			"
				>
					{#if showModelSelector}
						<ModelSelector bind:selectedModels showSetDefault={!shareEnabled} />
					{/if}
				</div>-->
				<div class="self-start flex flex-none items-center text-gray-600 dark:text-gray-400">
					<!-- <div class="md:hidden flex self-center w-[1px] h-5 mx-2 bg-gray-300 dark:bg-stone-700" /> -->
					<!--{#if shareEnabled && chat && (chat.id || $temporaryChatEnabled)}
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
					{/if}-->
					<div class="flex items-center mr-[12px]">
						<label class="relative inline-flex items-center cursor-pointer">
							<input type="checkbox" bind:checked={isOn} class="sr-only peer" />
							<div class="w-[56px] h-[28px] bg-gray-1100 rounded-full peer duration-300">
								<div
									class=" flex items-center justify-center absolute {isOn
										? 'left-[3px]'
										: 'right-[3px]'}  top-[3px] w-[20px] h-[20px] bg-white rounded-full transition-transform duration-300 peer-checked:translate-x-5"
								>
									<LightMode strokeWidth="2" className="size-[1.1rem]" />
								</div>
							</div>
						</label>
					</div>
					<!--<Tooltip content={$i18n.t('Controls')}>
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
					</Tooltip>-->

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
								class="select-none flex rounded-xl w-full hover:bg-gray-50 dark:hover:bg-gray-850 transition"
								aria-label="User Menu"
							>
								<div class=" self-center">
									<img
										src={$user?.profile_image_url}
										class="size-8 object-cover rounded-full"
										alt="User profile"
										draggable="false"
									/>
								</div>
							</button>
						</UserMenu>
					{/if}
				</div>
			</div>



    <!-- No add/new chat icon on desktop -->
  {/if}
</nav>
