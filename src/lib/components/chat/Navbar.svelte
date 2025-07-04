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
	 let isOn = false
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

	<div
				class="flex-1 overflow-hidden max-w-full py-0.5
			{$showSidebar ? 'ml-1' : ''}
			"
			>
				{#if showModelSelector}
					<ModelSelector bind:selectedModels showSetDefault={!shareEnabled} />
				{/if}
			</div>



    <!-- No add/new chat icon on desktop -->
  {/if}
</nav>
