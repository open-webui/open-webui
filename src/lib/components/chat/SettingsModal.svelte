<script lang="ts">
	import { getContext, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { models, settings, user } from '$lib/stores';
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

	const i18n = getContext('i18n');

	export let show = false;

	interface SettingsTab {
		id: string;
		title: string;
		keywords: string[];
	}

	const searchData: SettingsTab[] = [
		{
			id: 'general',
			title: 'General',
			keywords: [
				'general',
				'theme',
				'language',
				'notifications',
				'system',
				'systemprompt',
				'prompt',
				'advanced',
				'settings',
				'defaultsettings',
				'configuration',
				'systemsettings',
				'notificationsettings',
				'systempromptconfig',
				'languageoptions',
				'defaultparameters',
				'systemparameters'
			]
		},
		{
			id: 'interface',
			title: 'Interface',
			keywords: [
				'defaultmodel',
				'selectmodel',
				'ui',
				'userinterface',
				'display',
				'layout',
				'design',
				'landingpage',
				'landingpagemode',
				'default',
				'chat',
				'chatbubble',
				'chatui',
				'username',
				'showusername',
				'displayusername',
				'widescreen',
				'widescreenmode',
				'fullscreen',
				'expandmode',
				'chatdirection',
				'lefttoright',
				'ltr',
				'righttoleft',
				'rtl',
				'notifications',
				'toast',
				'toastnotifications',
				'largechunks',
				'streamlargechunks',
				'scroll',
				'scrollonbranchchange',
				'scrollbehavior',
				'richtext',
				'richtextinput',
				'background',
				'chatbackground',
				'chatbackgroundimage',
				'backgroundimage',
				'uploadbackground',
				'resetbackground',
				'titleautogen',
				'titleautogeneration',
				'autotitle',
				'chattags',
				'autochattags',
				'responseautocopy',
				'clipboard',
				'location',
				'userlocation',
				'userlocationaccess',
				'haptic',
				'hapticfeedback',
				'vibration',
				'voice',
				'voicecontrol',
				'voiceinterruption',
				'call',
				'emojis',
				'displayemoji',
				'save',
				'interfaceoptions',
				'interfacecustomization'
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
			id: 'audio',
			title: 'Audio',
			keywords: [
				'audio',
				'sound',
				'soundsettings',
				'audiocontrol',
				'volume',
				'speech',
				'speechrecognition',
				'stt',
				'speechtotext',
				'tts',
				'texttospeech',
				'playback',
				'playbackspeed',
				'voiceplayback',
				'speechplayback',
				'audiooutput',
				'speechengine',
				'voicecontrol',
				'audioplayback',
				'transcription',
				'autotranscribe',
				'autosend',
				'speechsettings',
				'audiovoice',
				'voiceoptions',
				'setvoice',
				'nonlocalvoices',
				'savesettings',
				'audioconfig',
				'speechconfig',
				'voicerecognition',
				'speechsynthesis',
				'speechmode',
				'voicespeed',
				'speechrate',
				'speechspeed',
				'audioinput',
				'audiofeatures',
				'voicemodes'
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
			id: 'account',
			title: 'Account',
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
		{
			id: 'about',
			title: 'About',
			keywords: [
				'about',
				'info',
				'information',
				'version',
				'documentation',
				'help',
				'support',
				'details',
				'aboutus',
				'softwareinfo',
				'timothyjaeryangbaek',
				'openwebui',
				'release',
				'updates',
				'updateinfo',
				'versioninfo',
				'aboutapp',
				'terms',
				'termsandconditions',
				'contact',
				'aboutpage'
			]
		}
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

	let selectedTab = 'general';

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

	$: if (show) {
		addScrollListener();
	} else {
		removeScrollListener();
	}
</script>

<Modal size="xl" bind:show>
	<div class="text-gray-700 dark:text-gray-100">
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-1">
			<div class=" text-lg font-medium self-center">{$i18n.t('Settings')}</div>
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

		<div class="flex flex-col md:flex-row w-full px-4 pt-1 pb-4 md:space-x-4">
			<div
				id="settings-tabs-container"
				class="tabs flex flex-row overflow-x-auto gap-2.5 md:gap-1 md:flex-col flex-1 md:flex-none md:w-40 dark:text-gray-200 text-sm font-medium text-left mb-1 md:mb-0 -translate-y-1"
			>
				<div class="hidden md:flex w-full rounded-xl -mb-1 px-0.5 gap-2" id="settings-search">
					<div class="self-center rounded-l-xl bg-transparent">
						<Search className="size-3.5" />
					</div>
					<input
						class="w-full py-1.5 text-sm bg-transparent dark:text-gray-300 outline-none"
						bind:value={search}
						on:input={searchDebounceHandler}
						placeholder={$i18n.t('Search')}
					/>
				</div>

				{#if visibleTabs.length > 0}
					{#each visibleTabs as tabId (tabId)}
						{#if tabId === 'general'}
							<button
								class="px-0.5 py-1 min-w-fit rounded-lg flex-1 md:flex-none flex text-left transition {selectedTab ===
								'general'
									? ''
									: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
								on:click={() => {
									selectedTab = 'general';
								}}
							>
								<div class=" self-center mr-2">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 20 20"
										fill="currentColor"
										class="w-4 h-4"
									>
										<path
											fill-rule="evenodd"
											d="M8.34 1.804A1 1 0 019.32 1h1.36a1 1 0 01.98.804l.295 1.473c.497.144.971.342 1.416.587l1.25-.834a1 1 0 011.262.125l.962.962a1 1 0 01.125 1.262l-.834 1.25c.245.445.443.919.587 1.416l1.473.294a1 1 0 01.804.98v1.361a1 1 0 01-.804.98l-1.473.295a6.95 6.95 0 01-.587 1.416l.834 1.25a1 1 0 01-.125 1.262l-.962.962a1 1 0 01-1.262.125l-1.25-.834a6.953 6.953 0 01-1.416.587l-.294 1.473a1 1 0 01-.98.804H9.32a1 1 0 01-.98-.804l-.295-1.473a6.957 6.957 0 01-1.416-.587l-1.25.834a1 1 0 01-1.262-.125l-.962-.962a1 1 0 01-.125-1.262l.834-1.25a6.957 6.957 0 01-.587-1.416l-1.473-.294A1 1 0 011 10.68V9.32a1 1 0 01.804-.98l1.473-.295c.144-.497.342-.971.587-1.416l-.834-1.25a1 1 0 01.125-1.262l.962-.962A1 1 0 015.38 3.03l1.25.834a6.957 6.957 0 011.416-.587l.294-1.473zM13 10a3 3 0 11-6 0 3 3 0 016 0z"
											clip-rule="evenodd"
										/>
									</svg>
								</div>
								<div class=" self-center">{$i18n.t('General')}</div>
							</button>
						{:else if tabId === 'interface'}
							<button
								class="px-0.5 py-1 min-w-fit rounded-lg flex-1 md:flex-none flex text-left transition {selectedTab ===
								'interface'
									? ''
									: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
								on:click={() => {
									selectedTab = 'interface';
								}}
							>
								<div class=" self-center mr-2">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 16 16"
										fill="currentColor"
										class="w-4 h-4"
									>
										<path
											fill-rule="evenodd"
											d="M2 4.25A2.25 2.25 0 0 1 4.25 2h7.5A2.25 2.25 0 0 1 14 4.25v5.5A2.25 2.25 0 0 1 11.75 12h-1.312c.1.128.21.248.328.36a.75.75 0 0 1 .234.545v.345a.75.75 0 0 1-.75.75h-4.5a.75.75 0 0 1-.75-.75v-.345a.75.75 0 0 1 .234-.545c.118-.111.228-.232.328-.36H4.25A2.25 2.25 0 0 1 2 9.75v-5.5Zm2.25-.75a.75.75 0 0 0-.75.75v4.5c0 .414.336.75.75.75h7.5a.75.75 0 0 0 .75-.75v-4.5a.75.75 0 0 0-.75-.75h-7.5Z"
											clip-rule="evenodd"
										/>
									</svg>
								</div>
								<div class=" self-center">{$i18n.t('Interface')}</div>
							</button>
						{:else if tabId === 'personalization'}
							<button
								class="px-0.5 py-1 min-w-fit rounded-lg flex-1 md:flex-none flex text-left transition {selectedTab ===
								'personalization'
									? ''
									: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
								on:click={() => {
									selectedTab = 'personalization';
								}}
							>
								<div class=" self-center mr-2">
									<User />
								</div>
								<div class=" self-center">{$i18n.t('Personalization')}</div>
							</button>
						{:else if tabId === 'audio'}
							<button
								class="px-0.5 py-1 min-w-fit rounded-lg flex-1 md:flex-none flex text-left transition {selectedTab ===
								'audio'
									? ''
									: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
								on:click={() => {
									selectedTab = 'audio';
								}}
							>
								<div class=" self-center mr-2">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 16 16"
										fill="currentColor"
										class="w-4 h-4"
									>
										<path
											d="M7.557 2.066A.75.75 0 0 1 8 2.75v10.5a.75.75 0 0 1-1.248.56L3.59 11H2a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h1.59l3.162-2.81a.75.75 0 0 1 .805-.124ZM12.95 3.05a.75.75 0 1 0-1.06 1.06 5.5 5.5 0 0 1 0 7.78.75.75 0 1 0 1.06 1.06 7 7 0 0 0 0-9.9Z"
										/>
										<path
											d="M10.828 5.172a.75.75 0 1 0-1.06 1.06 2.5 2.5 0 0 1 0 3.536.75.75 0 1 0 1.06 1.06 4 4 0 0 0 0-5.656Z"
										/>
									</svg>
								</div>
								<div class=" self-center">{$i18n.t('Audio')}</div>
							</button>
						{:else if tabId === 'chats'}
							<button
								class="px-0.5 py-1 min-w-fit rounded-lg flex-1 md:flex-none flex text-left transition {selectedTab ===
								'chats'
									? ''
									: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
								on:click={() => {
									selectedTab = 'chats';
								}}
							>
								<div class=" self-center mr-2">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 16 16"
										fill="currentColor"
										class="w-4 h-4"
									>
										<path
											fill-rule="evenodd"
											d="M8 2C4.262 2 1 4.57 1 8c0 1.86.98 3.486 2.455 4.566a3.472 3.472 0 0 1-.469 1.26.75.75 0 0 0 .713 1.14 6.961 6.961 0 0 0 3.06-1.06c.403.062.818.094 1.241.094 3.738 0 7-2.57 7-6s-3.262-6-7-6ZM5 9a1 1 0 1 0 0-2 1 1 0 0 0 0 2Zm7-1a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM8 9a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
											clip-rule="evenodd"
										/>
									</svg>
								</div>
								<div class=" self-center">{$i18n.t('Chats')}</div>
							</button>
						{:else if tabId === 'account'}
							<button
								class="px-0.5 py-1 min-w-fit rounded-lg flex-1 md:flex-none flex text-left transition {selectedTab ===
								'account'
									? ''
									: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
								on:click={() => {
									selectedTab = 'account';
								}}
							>
								<div class=" self-center mr-2">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 16 16"
										fill="currentColor"
										class="w-4 h-4"
									>
										<path
											fill-rule="evenodd"
											d="M15 8A7 7 0 1 1 1 8a7 7 0 0 1 14 0Zm-5-2a2 2 0 1 1-4 0 2 2 0 0 1 4 0ZM8 9c-1.825 0-3.422.977-4.295 2.437A5.49 5.49 0 0 0 8 13.5a5.49 5.49 0 0 0 4.294-2.063A4.997 4.997 0 0 0 8 9Z"
											clip-rule="evenodd"
										/>
									</svg>
								</div>
								<div class=" self-center">{$i18n.t('Account')}</div>
							</button>
						{:else if tabId === 'about'}
							<button
								class="px-0.5 py-1 min-w-fit rounded-lg flex-1 md:flex-none flex text-left transition {selectedTab ===
								'about'
									? ''
									: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
								on:click={() => {
									selectedTab = 'about';
								}}
							>
								<div class=" self-center mr-2">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 20 20"
										fill="currentColor"
										class="w-4 h-4"
									>
										<path
											fill-rule="evenodd"
											d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z"
											clip-rule="evenodd"
										/>
									</svg>
								</div>
								<div class=" self-center">{$i18n.t('About')}</div>
							</button>
						{:else if tabId === 'admin'}
							{#if $user.role === 'admin'}
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
							{/if}
						{/if}
					{/each}
				{:else}
					<div class="text-center text-gray-500 mt-4">
						{$i18n.t('No results found')}
					</div>
				{/if}
			</div>
			<div class="flex-1 md:min-h-[32rem] max-h-[32rem]">
				{#if selectedTab === 'general'}
					<General
						{getModels}
						{saveSettings}
						on:save={() => {
							toast.success($i18n.t('Settings saved successfully!'));
						}}
					/>
				{:else if selectedTab === 'interface'}
					<Interface
						{saveSettings}
						on:save={() => {
							toast.success($i18n.t('Settings saved successfully!'));
						}}
					/>
				{:else if selectedTab === 'personalization'}
					<Personalization
						{saveSettings}
						on:save={() => {
							toast.success($i18n.t('Settings saved successfully!'));
						}}
					/>
				{:else if selectedTab === 'audio'}
					<Audio
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
				{:else if selectedTab === 'about'}
					<About />
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
