<script lang="ts">
	import { getContext, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { models, settings, user, mobile } from '$lib/stores';
	import { updateUserSettings } from '$lib/apis/users';
	import { getModels as _getModels } from '$lib/apis';
	import { goto } from '$app/navigation';

	import Modal from '../common/Modal.svelte';
	import Account from './Settings/Account.svelte';
	import About from './Settings/About.svelte';
	import General from './Settings/General.svelte';
	import Interface from './Settings/Interface.svelte';
	import Audio from './Settings/Audio.svelte';
	import Chats from './Settings/Chats.svelte';
	import User from '../icons/User.svelte';
	import Personalization from './Settings/Personalization.svelte';
	import SearchInput from '../layout/Sidebar/SearchInput.svelte';
	import Search from '../icons/Search.svelte';
	import ProfileIcon from '../icons/ProfileIcon.svelte';
	import PersonalizationIcon from '../icons/PersonalizationIcon.svelte';
	import ChatIcon from '../icons/ChatIcon.svelte';
	import BackIcon from '../icons/BackIcon.svelte';

	const i18n = getContext('i18n');

	export let show = false;

	interface SettingsTab {
		id: string;
		title: string;
		keywords: string[];
	}

	const searchData: SettingsTab[] = [
		{
			id: 'account',
			title: 'Profile',
			keywords: [
				'account',
				'profile',
				'security',
				'privacy',
				'settings',
				'login',
				'useraccount',
				'userdata',
				'api',
				'apikey',
				'userprofile',
				'profiledetails',
				'accountsettings',
				'accountpreferences',
				'securitysettings',
				'privacysettings'
			]
		},
		{
			id: 'personalization',
			title: 'Personalization',
			keywords: [
				'personalization',
				'memory',
				'personalize',
				'preferences',
				'profile',
				'personalsettings',
				'customsettings',
				'userpreferences',
				'accountpreferences'
			]
		},
		{
			id: 'chats',
			title: 'Chats',
			keywords: [
				'chat',
				'messages',
				'conversations',
				'chatsettings',
				'history',
				'chathistory',
				'messagehistory',
				'messagearchive',
				'convo',
				'chats',
				'conversationhistory',
				'exportmessages',
				'chatactivity'
			]
		},
		{
			id: 'admin',
			title: 'Admin',
			keywords: [
				'admin',
				'administrator',
				'adminsettings',
				'adminpanel',
				'systemadmin',
				'administratoraccess',
				'systemcontrol',
				'manage',
				'management',
				'admincontrols',
				'adminfeatures',
				'usercontrol',
				'arenamodel',
				'evaluations',
				'websearch',
				'database',
				'pipelines',
				'images',
				'audio',
				'documents',
				'rag',
				'models',
				'ollama',
				'openai',
				'users'
			]
		},
	];

	let search = '';
	let visibleTabs = searchData.map((tab) => tab.id);
	let searchDebounceTimeout;

	const searchSettings = (query: string): string[] => {
		const lowerCaseQuery = query.toLowerCase().trim();
		return searchData
			.filter(
				(tab) =>
					tab.title.toLowerCase().includes(lowerCaseQuery) ||
					tab.keywords.some((keyword) => keyword.includes(lowerCaseQuery))
			)
			.map((tab) => tab.id);
	};

	const searchDebounceHandler = () => {
		clearTimeout(searchDebounceTimeout);
		searchDebounceTimeout = setTimeout(() => {
			visibleTabs = searchSettings(search);
			if (visibleTabs.length > 0 && !visibleTabs.includes(selectedTab)) {
				selectedTab = visibleTabs[0];
			}
		}, 100);
	};

	const saveSettings = async (updated) => {
		console.log(updated);
		await settings.set({ ...$settings, ...updated });
		await models.set(await getModels());
		await updateUserSettings(localStorage.token, { ui: $settings });
	};

	const getModels = async () => {
		return await _getModels(localStorage.token);
	};

	let selectedTab = 'account';

	// Function to handle sideways scrolling
	const scrollHandler = (event) => {
		const settingsTabsContainer = document.getElementById('settings-tabs-container');
		if (settingsTabsContainer) {
			event.preventDefault(); // Prevent default vertical scrolling
			settingsTabsContainer.scrollLeft += event.deltaY; // Scroll sideways
		}
	};

	const addScrollListener = async () => {
		await tick();
		const settingsTabsContainer = document.getElementById('settings-tabs-container');
		if (settingsTabsContainer) {
			settingsTabsContainer.addEventListener('wheel', scrollHandler);
		}
	};

	const removeScrollListener = async () => {
		await tick();
		const settingsTabsContainer = document.getElementById('settings-tabs-container');
		if (settingsTabsContainer) {
			settingsTabsContainer.removeEventListener('wheel', scrollHandler);
		}
	};

	let previousWidth = window.innerWidth;

	const handleResize = () => {
		const currentWidth = window.innerWidth;
		if (currentWidth !== previousWidth) {
			previousWidth = currentWidth;

			if (show) {
				if (currentWidth < 768 && selectedTab !== null) {
					selectedTab = null;
				} else if (currentWidth >= 768 && selectedTab === null) {
					selectedTab = 'account';
				}
			}
		}
	};

	$: if (show) {
		addScrollListener();
		handleResize(); 
		window.addEventListener('resize', handleResize);
	} else {
		removeScrollListener();
		window.removeEventListener('resize', handleResize);
	}
</script>

<Modal size="md-plus" bind:show className="dark:bg-customGray-800 rounded-2xl" containerClassName="bg-lightGray-250/50 dark:bg-[#1D1A1A]/50 backdrop-blur-[7.44px]">
	<div class="text-lightGray-100 dark:text-gray-100 bg-lightGray-550 dark:bg-customGray-800 rounded-xl md:h-auto">
		<div class="px-7">
			<div class=" flex justify-between items-center dark:text-white pt-5 pb-4 border-b dark:border-customGray-700">
				{#if selectedTab && $mobile}
					<button class="capitalize flex items-center" on:click={() => selectedTab = null}>
						<BackIcon className="mr-1 size-4 shrink-0"/>
						<div class="shrink-0">{$i18n.t(searchData?.find(item => item?.id === selectedTab).title)}</div>
					</button>
				{:else}
					<div class="self-center">{$i18n.t('Personal Settings')}</div>
				{/if}
				
				<button
					class="self-center"
					on:click={() => {
						show = false;
					}}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="w-5 h-5"
					>
						<path
							d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
						/>
					</svg>
				</button>
			</div>
		</div>

		<div class="flex flex-col md:flex-row w-full pl-4 pr-4 md:pl-0 md:pr-7 md:space-x-4">
			{#if selectedTab === null || !$mobile}
				<div
					id="settings-tabs-container"
					class="rounded-bl-lg md:pl-4 md:pt-5 pr-2 tabs flex flex-col  md:dark:bg-customGray-900 md:gap-1 flex-1 md:flex-none md:w-[253px] dark:text-gray-200 text-sm font-medium text-left mb-1 md:mb-0"
				>
					{#if visibleTabs.length > 0}
						{#each visibleTabs as tabId (tabId)}
							
							{#if tabId === 'personalization'}
								<button
								class="px-3 py-5 md:py-2.5 min-w-fit border-b md:border-b-0 border-lightGray-400 dark:border-customGray-700 md:rounded-md text-lightGray-100 flex-1 md:flex-none text-left transition {selectedTab ===
								'personalization'
									? 'bg-lightGray-700 dark:bg-customGray-800 dark:text-white'
									: ' text-lightGray-100 dark:text-customGray-100 hover:text-gray-700 dark:hover:text-white'}"
									on:click={() => {
										selectedTab = 'personalization';
									}}
								>
								<div class="flex items-center mb-1">
									<div class=" self-center mr-2">
										<PersonalizationIcon/>
									</div>
									<div class=" self-center">{$i18n.t('Personalization')}</div>
								</div>
									<!-- {#if (!$mobile)}
										<div class="{selectedTab ===
										'personalization'
											? ''
											: 'invisible'} font-normal text-xs dark:text-white/50">{$i18n.t('Personalise the look and feel')}</div>
									{/if}	 -->
							</button>
							
							{:else if tabId === 'chats'}
								<button
								class="px-3 py-5 md:py-2.5 min-w-fit text-lightGray-100 border-b md:border-b-0 border-lightGray-400 dark:border-customGray-700 md:rounded-md flex-1 md:flex-none text-left transition {selectedTab ===
								'chats'
									? 'bg-lightGray-700 dark:bg-customGray-800 dark:text-white'
									: ' text-lightGray-100 dark:text-customGray-100 hover:text-gray-700 dark:hover:text-white'}"
									on:click={() => {
										selectedTab = 'chats';
									}}
								>
								<div class="flex items-center mb-1">
									<div class=" self-center mr-2">
										<ChatIcon/>
									</div>
									<div class=" self-center">{$i18n.t('Chats')}</div>
								</div>
								<!-- {#if (!$mobile)}
									<div class="{selectedTab ===
									'chats'
										? ''
										: 'invisible'} font-normal text-xs dark:text-white/50">{$i18n.t('Manage your personal details')}</div>
							  	{/if}	 -->
							</button>
							{:else if tabId === 'account'}
								<button
									class="px-3 py-5 md:py-2.5 min-w-fit border-b md:border-b-0 border-lightGray-400 dark:border-customGray-700 md:rounded-md flex-1 text-lightGray-100 md:flex-none text-left transition {selectedTab ===
									'account'
										? 'bg-lightGray-700 dark:bg-customGray-800 dark:text-white'
										: ' text-lightGray-100 dark:text-customGray-100 hover:text-gray-700 dark:hover:text-white'}"
									on:click={() => {
										selectedTab = 'account';
									}}
								>
									<div class="flex items-center mb-1">
										<div class=" self-center mr-2">
											<ProfileIcon/>
										</div>
										<div class=" self-center">{$i18n.t('Profile')}</div>
									</div>
									<!-- {#if (!$mobile)}
										<div class="{selectedTab ===
										'account'
											? ''
											: 'invisible'} font-normal text-xs dark:text-white/50">{$i18n.t('Manage your personal details')}</div>
									{/if}	 -->
							</button>
							{:else if tabId === 'admin'}
								<!-- {#if $user.role === 'admin'}
									<button
										class="px-0.5 py-1 min-w-fit rounded-lg flex-1 md:flex-none flex text-left transition {selectedTab ===
										'admin'
											? ''
											: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
										on:click={async () => {
											await goto('/admin/settings');
											show = false;
										}}
									>
										<div class=" self-center mr-2">
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 24 24"
												fill="currentColor"
												class="size-4"
											>
												<path
													fill-rule="evenodd"
													d="M4.5 3.75a3 3 0 0 0-3 3v10.5a3 3 0 0 0 3 3h15a3 3 0 0 0 3-3V6.75a3 3 0 0 0-3-3h-15Zm4.125 3a2.25 2.25 0 1 0 0 4.5 2.25 2.25 0 0 0 0-4.5Zm-3.873 8.703a4.126 4.126 0 0 1 7.746 0 .75.75 0 0 1-.351.92 7.47 7.47 0 0 1-3.522.877 7.47 7.47 0 0 1-3.522-.877.75.75 0 0 1-.351-.92ZM15 8.25a.75.75 0 0 0 0 1.5h3.75a.75.75 0 0 0 0-1.5H15ZM14.25 12a.75.75 0 0 1 .75-.75h3.75a.75.75 0 0 1 0 1.5H15a.75.75 0 0 1-.75-.75Zm.75 2.25a.75.75 0 0 0 0 1.5h3.75a.75.75 0 0 0 0-1.5H15Z"
													clip-rule="evenodd"
												/>
											</svg>
										</div>
										<div class=" self-center">{$i18n.t('Admin Settings')}</div>
									</button>
								{/if} -->
							{/if}
						{/each}
					{:else}
						<div class="text-center text-gray-500 mt-4">
							{$i18n.t('No results found')}
						</div>
					{/if}
				</div>
			{/if}
			<div class="flex-1 md:min-h-[32rem]">
				{#if selectedTab === 'personalization'}
					<General
						{getModels}
						{saveSettings}
						on:save={() => {
							toast.success($i18n.t('Settings saved successfully!'));
						}}
					/>
				{:else if selectedTab === 'chats'}
					<Chats {saveSettings} />
				{:else if selectedTab === 'account'}
					<Account
						{saveSettings}
						saveHandler={() => {
							toast.success($i18n.t('Settings saved successfully!'));
						}}
					/>
				{/if}
			</div>
		</div>
	</div>
</Modal>

<style>
	input::-webkit-outer-spin-button,
	input::-webkit-inner-spin-button {
		/* display: none; <- Crashes Chrome on hover */
		-webkit-appearance: none;
		margin: 0; /* <-- Apparently some margin are still there even though it's hidden */
	}

	.tabs::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.tabs {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
	}

	input[type='number'] {
		-moz-appearance: textfield; /* Firefox */
	}
</style>
