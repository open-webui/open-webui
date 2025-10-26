<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { config, models, settings, user } from '$lib/stores';
	import { updateUserSettings } from '$lib/apis/users';
	import { getModels as _getModels } from '$lib/apis';
	import { goto } from '$app/navigation';

	import Modal from '../common/Modal.svelte';
	import Account from './Settings/Account.svelte';
	import About from './Settings/About.svelte';
	import General from './Settings/General.svelte';
	import Interface from './Settings/Interface.svelte';
	import Audio from './Settings/Audio.svelte';
	import DataControls from './Settings/DataControls.svelte';
	import Personalization from './Settings/Personalization.svelte';
	import Search from '../icons/Search.svelte';
	import XMark from '../icons/XMark.svelte';
	import Connections from './Settings/Connections.svelte';
	import Tools from './Settings/Tools.svelte';
	import DatabaseSettings from '../icons/DatabaseSettings.svelte';
	import SettingsAlt from '../icons/SettingsAlt.svelte';
	import Link from '../icons/Link.svelte';
	import UserCircle from '../icons/UserCircle.svelte';
	import SoundHigh from '../icons/SoundHigh.svelte';
	import InfoCircle from '../icons/InfoCircle.svelte';
	import WrenchAlt from '../icons/WrenchAlt.svelte';
	import Face from '../icons/Face.svelte';
	import AppNotification from '../icons/AppNotification.svelte';
	import UserBadgeCheck from '../icons/UserBadgeCheck.svelte';

	const i18n = getContext('i18n');

	export let show = false;

	$: if (show) {
		addScrollListener();
	} else {
		removeScrollListener();
	}

	interface SettingsTab {
		id: string;
		title: string;
		keywords: string[];
	}

	const allSettings: SettingsTab[] = [
		{
			id: 'general',
			title: 'General',
			keywords: [
				'advancedparams',
				'advancedparameters',
				'advanced params',
				'advanced parameters',
				'configuration',
				'defaultparameters',
				'default parameters',
				'defaultsettings',
				'default settings',
				'general',
				'keepalive',
				'keep alive',
				'languages',
				'notifications',
				'requestmode',
				'request mode',
				'systemparameters',
				'system parameters',
				'systemprompt',
				'system prompt',
				'systemsettings',
				'system settings',
				'theme',
				'translate',
				'webuisettings',
				'webui settings'
			]
		},
		{
			id: 'interface',
			title: 'Interface',
			keywords: [
				'allow user location',
				'allow voice interruption in call',
				'allowuserlocation',
				'allowvoiceinterruptionincall',
				'always collapse codeblocks',
				'always collapse code blocks',
				'always expand details',
				'always on web search',
				'always play notification sound',
				'alwayscollapsecodeblocks',
				'alwaysexpanddetails',
				'alwaysonwebsearch',
				'alwaysplaynotificationsound',
				'android',
				'auto chat tags',
				'auto copy response to clipboard',
				'auto title',
				'autochattags',
				'autocopyresponsetoclipboard',
				'autotitle',
				'beta',
				'call',
				'chat background image',
				'chat bubble ui',
				'chat direction',
				'chat tags autogen',
				'chat tags autogeneration',
				'chat ui',
				'chatbackgroundimage',
				'chatbubbleui',
				'chatdirection',
				'chat tags autogeneration',
				'chattagsautogeneration',
				'chatui',
				'copy formatted text',
				'copyformattedtext',
				'default model',
				'defaultmodel',
				'design',
				'detect artifacts automatically',
				'detectartifactsautomatically',
				'display emoji in call',
				'display username',
				'displayemojiincall',
				'displayusername',
				'enter key behavior',
				'enterkeybehavior',
				'expand mode',
				'expandmode',
				'file',
				'followup autogeneration',
				'followupautogeneration',
				'fullscreen',
				'fullwidthmode',
				'full width mode',
				'haptic feedback',
				'hapticfeedback',
				'high contrast mode',
				'highcontrastmode',
				'iframe sandbox allow forms',
				'iframe sandbox allow same origin',
				'iframesandboxallowforms',
				'iframesandboxallowsameorigin',
				'imagecompression',
				'image compression',
				'imagemaxcompressionsize',
				'image max compression size',
				'interface customization',
				'interface options',
				'interfacecustomization',
				'interfaceoptions',
				'landing page mode',
				'landingpagemode',
				'layout',
				'left to right',
				'left-to-right',
				'lefttoright',
				'ltr',
				'paste large text as file',
				'pastelargetextasfile',
				'reset background',
				'resetbackground',
				'response auto copy',
				'responseautocopy',
				'rich text input for chat',
				'richtextinputforchat',
				'right to left',
				'right-to-left',
				'righttoleft',
				'rtl',
				'scroll behavior',
				'scroll on branch change',
				'scrollbehavior',
				'scrollonbranchchange',
				'select model',
				'selectmodel',
				'settings',
				'show username',
				'showusername',
				'stream large chunks',
				'streamlargechunks',
				'stylized pdf export',
				'stylizedpdfexport',
				'title autogeneration',
				'titleautogeneration',
				'toast notifications for new updates',
				'toastnotificationsfornewupdates',
				'upload background',
				'uploadbackground',
				'user interface',
				'user location access',
				'userinterface',
				'userlocationaccess',
				'vibration',
				'voice control',
				'voicecontrol',
				'widescreen mode',
				'widescreenmode',
				'whatsnew',
				'whats new',
				'websearchinchat',
				'web search in chat'
			]
		},
		{
			id: 'connections',
			title: 'Connections',
			keywords: [
				'addconnection',
				'add connection',
				'manageconnections',
				'manage connections',
				'manage direct connections',
				'managedirectconnections',
				'settings'
			]
		},
		{
			id: 'tools',
			title: 'External Tools',
			keywords: [
				'addconnection',
				'add connection',
				'managetools',
				'manage tools',
				'manage tool servers',
				'managetoolservers',
				'settings'
			]
		},

		{
			id: 'personalization',
			title: 'Personalization',
			keywords: [
				'account preferences',
				'account settings',
				'accountpreferences',
				'accountsettings',
				'custom settings',
				'customsettings',
				'experimental',
				'memories',
				'memory',
				'personalization',
				'personalize',
				'personal settings',
				'personalsettings',
				'profile',
				'user preferences',
				'userpreferences'
			]
		},
		{
			id: 'audio',
			title: 'Audio',
			keywords: [
				'audio config',
				'audio control',
				'audio features',
				'audio input',
				'audio output',
				'audio playback',
				'audio voice',
				'audioconfig',
				'audiocontrol',
				'audiofeatures',
				'audioinput',
				'audiooutput',
				'audioplayback',
				'audiovoice',
				'auto playback response',
				'autoplaybackresponse',
				'auto transcribe',
				'autotranscribe',
				'instant auto send after voice transcription',
				'instantautosendaftervoicetranscription',
				'language',
				'non local voices',
				'nonlocalvoices',
				'save settings',
				'savesettings',
				'set voice',
				'setvoice',
				'sound settings',
				'soundsettings',
				'speech config',
				'speech mode',
				'speech playback speed',
				'speech rate',
				'speech recognition',
				'speech settings',
				'speech speed',
				'speech synthesis',
				'speech to text engine',
				'speechconfig',
				'speechmode',
				'speechplaybackspeed',
				'speechrate',
				'speechrecognition',
				'speechsettings',
				'speechspeed',
				'speechsynthesis',
				'speechtotextengine',
				'speedch playback rate',
				'speedchplaybackrate',
				'stt settings',
				'sttsettings',
				'text to speech engine',
				'text to speech',
				'textospeechengine',
				'texttospeech',
				'texttospeechvoice',
				'text to speech voice',
				'voice control',
				'voice modes',
				'voice options',
				'voice playback',
				'voice recognition',
				'voice speed',
				'voicecontrol',
				'voicemodes',
				'voiceoptions',
				'voiceplayback',
				'voicerecognition',
				'voicespeed',
				'volume'
			]
		},
		{
			id: 'data_controls',
			title: 'Data Controls',
			keywords: [
				'archive all chats',
				'archive chats',
				'archiveallchats',
				'archivechats',
				'archived chats',
				'archivedchats',
				'chat activity',
				'chat history',
				'chat settings',
				'chatactivity',
				'chathistory',
				'chatsettings',
				'conversation activity',
				'conversation history',
				'conversationactivity',
				'conversationhistory',
				'conversations',
				'convos',
				'delete all chats',
				'delete chats',
				'deleteallchats',
				'deletechats',
				'export chats',
				'exportchats',
				'import chats',
				'importchats',
				'message activity',
				'message archive',
				'message history',
				'messagearchive',
				'messagehistory'
			]
		},
		{
			id: 'account',
			title: 'Account',
			keywords: [
				'account preferences',
				'account settings',
				'accountpreferences',
				'accountsettings',
				'api keys',
				'apikeys',
				'change password',
				'changepassword',
				'jwt token',
				'jwttoken',
				'login',
				'new password',
				'newpassword',
				'notification webhook url',
				'notificationwebhookurl',
				'personal settings',
				'personalsettings',
				'privacy settings',
				'privacysettings',
				'profileavatar',
				'profile avatar',
				'profile details',
				'profile image',
				'profile picture',
				'profiledetails',
				'profileimage',
				'profilepicture',
				'security settings',
				'securitysettings',
				'update account',
				'update password',
				'updateaccount',
				'updatepassword',
				'user account',
				'user data',
				'user preferences',
				'user profile',
				'useraccount',
				'userdata',
				'username',
				'userpreferences',
				'userprofile',
				'webhook url',
				'webhookurl'
			]
		},
		{
			id: 'about',
			title: 'About',
			keywords: [
				'about app',
				'about me',
				'about open webui',
				'about page',
				'about us',
				'aboutapp',
				'aboutme',
				'aboutopenwebui',
				'aboutpage',
				'aboutus',
				'check for updates',
				'checkforupdates',
				'contact',
				'copyright',
				'details',
				'discord',
				'documentation',
				'github',
				'help',
				'information',
				'license',
				'redistributions',
				'release',
				'see whats new',
				'seewhatsnew',
				'settings',
				'software info',
				'softwareinfo',
				'support',
				'terms and conditions',
				'terms of use',
				'termsandconditions',
				'termsofuse',
				'timothy jae ryang baek',
				'timothy j baek',
				'timothyjaeryangbaek',
				'timothyjbaek',
				'twitter',
				'update info',
				'updateinfo',
				'version info',
				'versioninfo'
			]
		}
	];

	let availableSettings = [];
	let filteredSettings = [];

	let search = '';
	let searchDebounceTimeout;

	const getAvailableSettings = () => {
		return allSettings.filter((tab) => {
			if (tab.id === 'connections') {
				return $config?.features?.enable_direct_connections;
			}

			if (tab.id === 'tools') {
				return (
					$user?.role === 'admin' ||
					($user?.role === 'user' && $user?.permissions?.features?.direct_tool_servers)
				);
			}

			return true;
		});
	};

	const setFilteredSettings = () => {
		filteredSettings = availableSettings
			.filter((tab) => {
				return (
					search === '' ||
					tab.title.toLowerCase().includes(search.toLowerCase().trim()) ||
					tab.keywords.some((keyword) => keyword.includes(search.toLowerCase().trim()))
				);
			})
			.map((tab) => tab.id);

		if (filteredSettings.length > 0 && !filteredSettings.includes(selectedTab)) {
			selectedTab = filteredSettings[0];
		}
	};

	const searchDebounceHandler = () => {
		if (searchDebounceTimeout) {
			clearTimeout(searchDebounceTimeout);
		}

		searchDebounceTimeout = setTimeout(() => {
			setFilteredSettings();
		}, 100);
	};

	const saveSettings = async (updated) => {
		console.log(updated);
		await settings.set({ ...$settings, ...updated });
		await models.set(await getModels());
		await updateUserSettings(localStorage.token, { ui: $settings });
	};

	const getModels = async () => {
		return await _getModels(
			localStorage.token,
			$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
		);
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

	onMount(() => {
		availableSettings = getAvailableSettings();
		setFilteredSettings();

		config.subscribe((configData) => {
			availableSettings = getAvailableSettings();
			setFilteredSettings();
		});
	});
</script>

<Modal size="xl" bind:show>
	<div class="text-gray-700 dark:text-gray-100 mx-1">
		<div class=" flex justify-between dark:text-gray-300 px-4 md:px-4.5 pt-4.5 pb-0.5 md:pb-2.5">
			<div class=" text-lg font-medium self-center">{$i18n.t('Settings')}</div>
			<button
				aria-label={$i18n.t('Close settings modal')}
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className="w-5 h-5"></XMark>
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full pt-1 pb-4">
			<div
				role="tablist"
				id="settings-tabs-container"
				class="tabs flex flex-row overflow-x-auto gap-2.5 mx-3 md:pr-4 md:gap-1 md:flex-col flex-1 md:flex-none md:w-50 md:min-h-[36rem] md:max-h-[36rem] dark:text-gray-200 text-sm text-left mb-1 md:mb-0 -translate-y-1"
			>
				<div
					class="hidden md:flex w-full rounded-full px-2.5 gap-2 bg-gray-100/80 dark:bg-gray-850/80 backdrop-blur-2xl my-1 mb-1.5"
					id="settings-search"
				>
					<div class="self-center rounded-l-xl bg-transparent">
						<Search
							className="size-3.5"
							strokeWidth={($settings?.highContrastMode ?? false) ? '3' : '1.5'}
						/>
					</div>
					<label class="sr-only" for="search-input-settings-modal">{$i18n.t('Search')}</label>
					<input
						class={`w-full py-1 text-sm bg-transparent dark:text-gray-300 outline-hidden
								${($settings?.highContrastMode ?? false) ? 'placeholder-gray-800' : ''}`}
						bind:value={search}
						id="search-input-settings-modal"
						on:input={searchDebounceHandler}
						placeholder={$i18n.t('Search')}
					/>
				</div>
				{#if filteredSettings.length > 0}
					{#each filteredSettings as tabId (tabId)}
						{#if tabId === 'general'}
							<button
								role="tab"
								aria-controls="tab-general"
								aria-selected={selectedTab === 'general'}
								class={`px-0.5 md:px-2.5 py-1 min-w-fit rounded-xl flex-1 md:flex-none flex text-left transition
								${
									selectedTab === 'general'
										? ($settings?.highContrastMode ?? false)
											? 'dark:bg-gray-800 bg-gray-200'
											: ''
										: ($settings?.highContrastMode ?? false)
											? 'hover:bg-gray-200 dark:hover:bg-gray-800'
											: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'
								}`}
								on:click={() => {
									selectedTab = 'general';
								}}
							>
								<div class=" self-center mr-2">
									<SettingsAlt strokeWidth="2" />
								</div>
								<div class=" self-center">{$i18n.t('General')}</div>
							</button>
						{:else if tabId === 'interface'}
							<button
								role="tab"
								aria-controls="tab-interface"
								aria-selected={selectedTab === 'interface'}
								class={`px-0.5 md:px-2.5 py-1 min-w-fit rounded-xl flex-1 md:flex-none flex text-left transition
								${
									selectedTab === 'interface'
										? ($settings?.highContrastMode ?? false)
											? 'dark:bg-gray-800 bg-gray-200'
											: ''
										: ($settings?.highContrastMode ?? false)
											? 'hover:bg-gray-200 dark:hover:bg-gray-800'
											: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'
								}`}
								on:click={() => {
									selectedTab = 'interface';
								}}
							>
								<div class=" self-center mr-2">
									<AppNotification strokeWidth="2" />
								</div>
								<div class=" self-center">{$i18n.t('Interface')}</div>
							</button>
						{:else if tabId === 'connections'}
							{#if $user?.role === 'admin' || ($user?.role === 'user' && $config?.features?.enable_direct_connections)}
								<button
									role="tab"
									aria-controls="tab-connections"
									aria-selected={selectedTab === 'connections'}
									class={`px-0.5 md:px-2.5 py-1 min-w-fit rounded-xl flex-1 md:flex-none flex text-left transition
								${
									selectedTab === 'connections'
										? ($settings?.highContrastMode ?? false)
											? 'dark:bg-gray-800 bg-gray-200'
											: ''
										: ($settings?.highContrastMode ?? false)
											? 'hover:bg-gray-200 dark:hover:bg-gray-800'
											: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'
								}`}
									on:click={() => {
										selectedTab = 'connections';
									}}
								>
									<div class=" self-center mr-2">
										<Link strokeWidth="2" />
									</div>
									<div class=" self-center">{$i18n.t('Connections')}</div>
								</button>
							{/if}
						{:else if tabId === 'tools'}
							{#if $user?.role === 'admin' || ($user?.role === 'user' && $user?.permissions?.features?.direct_tool_servers)}
								<button
									role="tab"
									aria-controls="tab-tools"
									aria-selected={selectedTab === 'tools'}
									class={`px-0.5 md:px-2.5 py-1 min-w-fit rounded-xl flex-1 md:flex-none flex text-left transition
								${
									selectedTab === 'tools'
										? ($settings?.highContrastMode ?? false)
											? 'dark:bg-gray-800 bg-gray-200'
											: ''
										: ($settings?.highContrastMode ?? false)
											? 'hover:bg-gray-200 dark:hover:bg-gray-800'
											: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'
								}`}
									on:click={() => {
										selectedTab = 'tools';
									}}
								>
									<div class=" self-center mr-2">
										<WrenchAlt strokeWidth="2" />
									</div>
									<div class=" self-center">{$i18n.t('External Tools')}</div>
								</button>
							{/if}
						{:else if tabId === 'personalization'}
							<button
								role="tab"
								aria-controls="tab-personalization"
								aria-selected={selectedTab === 'personalization'}
								class={`px-0.5 md:px-2.5 py-1 min-w-fit rounded-xl flex-1 md:flex-none flex text-left transition
								${
									selectedTab === 'personalization'
										? ($settings?.highContrastMode ?? false)
											? 'dark:bg-gray-800 bg-gray-200'
											: ''
										: ($settings?.highContrastMode ?? false)
											? 'hover:bg-gray-200 dark:hover:bg-gray-800'
											: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'
								}`}
								on:click={() => {
									selectedTab = 'personalization';
								}}
							>
								<div class=" self-center mr-2">
									<Face strokeWidth="2" />
								</div>
								<div class=" self-center">{$i18n.t('Personalization')}</div>
							</button>
						{:else if tabId === 'audio'}
							<button
								role="tab"
								aria-controls="tab-audio"
								aria-selected={selectedTab === 'audio'}
								class={`px-0.5 md:px-2.5 py-1 min-w-fit rounded-xl flex-1 md:flex-none flex text-left transition
								${
									selectedTab === 'audio'
										? ($settings?.highContrastMode ?? false)
											? 'dark:bg-gray-800 bg-gray-200'
											: ''
										: ($settings?.highContrastMode ?? false)
											? 'hover:bg-gray-200 dark:hover:bg-gray-800'
											: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'
								}`}
								on:click={() => {
									selectedTab = 'audio';
								}}
							>
								<div class=" self-center mr-2">
									<SoundHigh strokeWidth="2" />
								</div>
								<div class=" self-center">{$i18n.t('Audio')}</div>
							</button>
						{:else if tabId === 'data_controls'}
							<button
								role="tab"
								aria-controls="tab-data-controls"
								aria-selected={selectedTab === 'data_controls'}
								class={`px-0.5 md:px-2.5 py-1 min-w-fit rounded-xl flex-1 md:flex-none flex text-left transition
								${
									selectedTab === 'data_controls'
										? ($settings?.highContrastMode ?? false)
											? 'dark:bg-gray-800 bg-gray-200'
											: ''
										: ($settings?.highContrastMode ?? false)
											? 'hover:bg-gray-200 dark:hover:bg-gray-800'
											: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'
								}`}
								on:click={() => {
									selectedTab = 'data_controls';
								}}
							>
								<div class=" self-center mr-2">
									<DatabaseSettings strokeWidth="2" />
								</div>
								<div class=" self-center">{$i18n.t('Data Controls')}</div>
							</button>
						{:else if tabId === 'account'}
							<button
								role="tab"
								aria-controls="tab-account"
								aria-selected={selectedTab === 'account'}
								class={`px-0.5 md:px-2.5 py-1 min-w-fit rounded-xl flex-1 md:flex-none flex text-left transition
								${
									selectedTab === 'account'
										? ($settings?.highContrastMode ?? false)
											? 'dark:bg-gray-800 bg-gray-200'
											: ''
										: ($settings?.highContrastMode ?? false)
											? 'hover:bg-gray-200 dark:hover:bg-gray-800'
											: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'
								}`}
								on:click={() => {
									selectedTab = 'account';
								}}
							>
								<div class=" self-center mr-2">
									<UserCircle strokeWidth="2" />
								</div>
								<div class=" self-center">{$i18n.t('Account')}</div>
							</button>
						{:else if tabId === 'about'}
							<button
								role="tab"
								aria-controls="tab-about"
								aria-selected={selectedTab === 'about'}
								class={`px-0.5 md:px-2.5 py-1 min-w-fit rounded-xl flex-1 md:flex-none flex text-left transition
								${
									selectedTab === 'about'
										? ($settings?.highContrastMode ?? false)
											? 'dark:bg-gray-800 bg-gray-200'
											: ''
										: ($settings?.highContrastMode ?? false)
											? 'hover:bg-gray-200 dark:hover:bg-gray-800'
											: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'
								}`}
								on:click={() => {
									selectedTab = 'about';
								}}
							>
								<div class=" self-center mr-2">
									<InfoCircle strokeWidth="2" />
								</div>
								<div class=" self-center">{$i18n.t('About')}</div>
							</button>
						{/if}
					{/each}
				{:else}
					<div class="text-center text-gray-500 mt-4">
						{$i18n.t('No results found')}
					</div>
				{/if}
				{#if $user?.role === 'admin'}
					<a
						href="/admin/settings"
						class="px-0.5 md:px-2.5 py-1 min-w-fit rounded-xl flex-1 md:flex-none md:mt-auto flex text-left transition {$settings?.highContrastMode
							? 'hover:bg-gray-200 dark:hover:bg-gray-800'
							: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
						on:click={async (e) => {
							e.preventDefault();
							await goto('/admin/settings');
							show = false;
						}}
					>
						<div class=" self-center mr-2">
							<UserBadgeCheck strokeWidth="2" />
						</div>
						<div class=" self-center">{$i18n.t('Admin Settings')}</div>
					</a>
				{/if}
			</div>
			<div class="flex-1 px-3.5 md:pl-0 md:pr-4.5 md:min-h-[36rem] max-h-[36rem]">
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
				{:else if selectedTab === 'connections'}
					<Connections
						saveSettings={async (updated) => {
							await saveSettings(updated);
							toast.success($i18n.t('Settings saved successfully!'));
						}}
					/>
				{:else if selectedTab === 'tools'}
					<Tools
						saveSettings={async (updated) => {
							await saveSettings(updated);
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
				{:else if selectedTab === 'data_controls'}
					<DataControls {saveSettings} />
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
		appearance: textfield;
		-moz-appearance: textfield; /* Firefox */
	}
</style>
