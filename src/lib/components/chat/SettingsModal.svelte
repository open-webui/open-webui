<script lang="ts">
	import { browser } from '$app/environment';
	import { getContext, onMount, tick } from 'svelte';
	import type { Writable } from 'svelte/store';
	import { toast } from 'svelte-sonner';
	import { config, models, settings, user } from '$lib/stores';
	import type { SettingsModalRequest } from '$lib/stores';
	import { updateUserSettings } from '$lib/apis/users';
	import { getBackendConfig, getModels as _getModels } from '$lib/apis';

	import Modal from '../common/Modal.svelte';
	import Account from './Settings/Account.svelte';
	import About from './Settings/About.svelte';
	import General from './Settings/General.svelte';
	import Interface from './Settings/Interface.svelte';
	import Notifications from './Settings/Notifications.svelte';
	import Shortcuts from './Settings/Shortcuts.svelte';
	import Audio from './Settings/Audio.svelte';
	import DataControls from './Settings/DataControls.svelte';
	import Usage from './Settings/Usage.svelte';
	import ArchivedChats from './Settings/ArchivedChats.svelte';
	import Personalization from './Settings/Personalization.svelte';
	import Search from '../icons/Search.svelte';
	import Connections from './Settings/Connections.svelte';
	import Integrations from './Settings/Integrations.svelte';
	import DatabaseSettings from '../icons/DatabaseSettings.svelte';
	import SettingsAlt from '../icons/SettingsAlt.svelte';
	import Link from '../icons/Link.svelte';
	import UserCircle from '../icons/UserCircle.svelte';
	import SoundHigh from '../icons/SoundHigh.svelte';
	import InfoCircle from '../icons/InfoCircle.svelte';
	import WrenchAlt from '../icons/WrenchAlt.svelte';
	import Face from '../icons/Face.svelte';
	import AppNotification from '../icons/AppNotification.svelte';
	import AdjustmentsHorizontal from '../icons/AdjustmentsHorizontal.svelte';
	import ArchiveBox from '../icons/ArchiveBox.svelte';
	import ChevronLeft from '../icons/ChevronLeft.svelte';
	import Keyboard from '../icons/Keyboard.svelte';
	import UsageIcon from '../icons/UsageIcon.svelte';
	import AdminTabIcon from '$lib/components/admin/Settings/AdminTabIcon.svelte';
	import AdminGeneral from '$lib/components/admin/Settings/General.svelte';
	import AdminAuthentication from '$lib/components/admin/Settings/Authentication.svelte';
	import AdminConnections from '$lib/components/admin/Settings/Connections.svelte';
	import AdminModels from '$lib/components/admin/Settings/Models.svelte';
	import AdminSubagents from '$lib/components/admin/Settings/Subagents.svelte';
	import AdminEvaluations from '$lib/components/admin/Settings/Evaluations.svelte';
	import AdminAnalytics from '$lib/components/admin/Analytics.svelte';
	import AdminIntegrations from '$lib/components/admin/Settings/Integrations.svelte';
	import AdminDocuments from '$lib/components/admin/Settings/Documents.svelte';
	import AdminWebSearch from '$lib/components/admin/Settings/WebSearch.svelte';
	import AdminCodeExecution from '$lib/components/admin/Settings/CodeExecution.svelte';
	import AdminInterface from '$lib/components/admin/Settings/Interface.svelte';
	import AdminAudio from '$lib/components/admin/Settings/Audio.svelte';
	import AdminImages from '$lib/components/admin/Settings/Images.svelte';
	import AdminPipelines from '$lib/components/admin/Settings/Pipelines.svelte';
	import AdminDatabase from '$lib/components/admin/Settings/Database.svelte';

	const i18n: Writable<any> = getContext('i18n');

	export let show: boolean | string | SettingsModalRequest = false;
	let modalShow = false;
	let lastShow: boolean | string | SettingsModalRequest = false;
	let tabState: Record<string, unknown> | null = null;

	$: if (show !== lastShow) {
		lastShow = show;
		if (show && typeof show === 'object') {
			selectedTab = show.tab;
			tabState = show.state ?? null;
			show = true;
			lastShow = true;
			modalShow = true;
		} else if (typeof show === 'string') {
			selectedTab = show;
			show = true;
			lastShow = true;
			modalShow = true;
		} else {
			modalShow = show;
			if (!show) {
				selectedTab = 'general';
				tabState = null;
			}
		}
	}

	$: if (!modalShow && show !== false) {
		show = false;
		lastShow = false;
		selectedTab = 'general';
		tabState = null;
	}

	interface SettingsTab {
		id: string;
		title: string;
		keywords: string[];
	}

	const isAdminTab = (tabId: string) => tabId.startsWith('admin:');
	const adminTabSegment = (tabId: string) => tabId.replace('admin:', '');
	const adminTabPanelId = (tabId: string) => `tab-${tabId.replace(':', '-')}`;
	const personalSettingGroups: Record<string, string> = {
		general: 'Basics',
		interface: 'Basics',
		notifications: 'Basics',
		shortcuts: 'Basics',
		connections: 'Services',
		tools: 'Services',
		personalization: 'Preferences',
		audio: 'Preferences',
		data_controls: 'Data',
		usage: 'Data',
		archived_chats: 'Data',
		account: 'Profile',
		about: 'Profile'
	};
	const adminSettingGroups: Record<string, string> = {
		'admin:general': 'System',
		'admin:authentication': 'System',
		'admin:connections': 'AI',
		'admin:models': 'AI',
		'admin:subagents': 'AI',
		'admin:evaluations': 'Quality',
		'admin:analytics': 'Quality',
		'admin:integrations': 'Tools',
		'admin:documents': 'Tools',
		'admin:web': 'Tools',
		'admin:code-execution': 'Tools',
		'admin:pipelines': 'Tools',
		'admin:interface': 'Experience',
		'admin:audio': 'Experience',
		'admin:images': 'Experience',
		'admin:db': 'Data'
	};
	const settingGroupTitle = (tabId: string) =>
		(isAdminTab(tabId) ? adminSettingGroups[tabId] : personalSettingGroups[tabId]) ?? 'General';
	const shouldShowSettingGroup = (tabIds: string[], index: number) =>
		index === 0 || settingGroupTitle(tabIds[index]) !== settingGroupTitle(tabIds[index - 1]);
	const settingGroupHeadingClass = (first: boolean) =>
		`hidden md:block shrink-0 text-[0.625rem] text-gray-400 dark:text-gray-600 px-2 ${
			first ? 'mt-0.5' : 'mt-2'
		} mb-0.5`;

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
			id: 'notifications',
			title: 'Notifications',
			keywords: [
				'browser notifications',
				'browsernotifications',
				'chat failed',
				'chat finished',
				'notification sound',
				'notifications',
				'notify',
				'webhook',
				'webhook notifications',
				'webhooks'
			]
		},
		{
			id: 'shortcuts',
			title: 'Keyboard',
			keywords: [
				'commands',
				'hotkeys',
				'keyboard',
				'keyboard shortcuts',
				'keybindings',
				'keys',
				'shortcut',
				'shortcuts',
				'show shortcuts'
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
			title: 'Integrations',
			keywords: [
				'addconnection',
				'add connection',
				'integrations',
				'managetools',
				'manage tools',
				'manage tool servers',
				'managetoolservers',
				'open terminal',
				'openterminal',
				'terminal',
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
			id: 'usage',
			title: 'Usage',
			keywords: [
				'activity',
				'activity heatmap',
				'analytics',
				'chat activity',
				'heatmap',
				'model usage',
				'stats',
				'streak',
				'token activity',
				'token usage',
				'tokens',
				'usage'
			]
		},
		{
			id: 'archived_chats',
			title: 'Archived Chats',
			keywords: [
				'archive',
				'archive chat',
				'archive chats',
				'archived',
				'archived chat',
				'archived chats',
				'archivedchat',
				'archivedchats',
				'conversation archive',
				'message archive',
				'unarchive',
				'unarchive chat',
				'unarchive chats'
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

	const adminSettings: SettingsTab[] = [
		{
			id: 'admin:general',
			title: 'General',
			keywords: ['general', 'admin', 'settings', 'version', 'update', 'community', 'channels']
		},
		{
			id: 'admin:authentication',
			title: 'Authentication',
			keywords: [
				'authentication',
				'auth',
				'login',
				'signup',
				'ldap',
				'oauth',
				'oidc',
				'sso',
				'roles'
			]
		},
		{
			id: 'admin:connections',
			title: 'Connections',
			keywords: [
				'connections',
				'ollama',
				'openai',
				'api',
				'base url',
				'direct connections',
				'proxy'
			]
		},
		{
			id: 'admin:models',
			title: 'Models',
			keywords: [
				'models',
				'pull',
				'delete',
				'create',
				'edit',
				'modelfile',
				'gguf',
				'import',
				'export'
			]
		},
		{
			id: 'admin:subagents',
			title: 'Sub-agents',
			keywords: ['sub-agents', 'subagents', 'delegation', 'background', 'agents']
		},
		{
			id: 'admin:interface',
			title: 'Interface',
			keywords: ['interface', 'ui', 'appearance', 'banners', 'tasks', 'prompt suggestions', 'tags']
		},
		{
			id: 'admin:audio',
			title: 'Audio',
			keywords: ['audio', 'voice', 'speech', 'tts', 'stt', 'whisper', 'deepgram', 'azure']
		},
		{
			id: 'admin:images',
			title: 'Images',
			keywords: ['images', 'generation', 'dalle', 'stable diffusion', 'comfyui', 'automatic1111']
		},
		{
			id: 'admin:evaluations',
			title: 'Evaluations',
			keywords: ['evaluations', 'feedback', 'rating', 'arena', 'leaderboard', 'preference']
		},
		{
			id: 'admin:analytics',
			title: 'Analytics',
			keywords: ['analytics', 'usage', 'stats', 'dashboard', 'models', 'users', 'messages']
		},
		{
			id: 'admin:integrations',
			title: 'Integrations',
			keywords: ['tools', 'integrations', 'plugins', 'extensions', 'functions', 'openapi', 'server']
		},
		{
			id: 'admin:documents',
			title: 'Documents',
			keywords: ['documents', 'files', 'rag', 'knowledge', 'upload', 'embedding', 'vector db']
		},
		{
			id: 'admin:web',
			title: 'Web Search',
			keywords: ['web search', 'google', 'bing', 'duckduckgo', 'serp', 'searxng', 'tavily', 'exa']
		},
		{
			id: 'admin:code-execution',
			title: 'Code Execution',
			keywords: ['code execution', 'python', 'sandbox', 'compiler', 'jupyter', 'interpreter']
		},
		{
			id: 'admin:pipelines',
			title: 'Pipelines',
			keywords: ['pipelines', 'workflows', 'filters', 'valves', 'middleware']
		},

		{
			id: 'admin:db',
			title: 'Database',
			keywords: ['database', 'export', 'import', 'backup', 'chats', 'users']
		}
	];
	let availableSettings: SettingsTab[] = [];
	let filteredSettings: string[] = [];
	let filteredPersonalSettings: string[] = [];
	let filteredAdminSettings: string[] = [];

	let search = '';
	let searchDebounceTimeout: ReturnType<typeof setTimeout> | null = null;

	const getAvailableSettings = () => {
		const personalSettings = allSettings.filter((tab) => {
			if (tab.id === 'connections') {
				return $config?.features?.enable_direct_connections;
			}

			if (tab.id === 'tools') {
				return (
					$user?.role === 'admin' ||
					($user?.role === 'user' && $user?.permissions?.features?.direct_tool_servers)
				);
			}

			if (tab.id === 'interface') {
				return $user?.role === 'admin' || ($user?.permissions?.settings?.interface ?? true);
			}

			if (tab.id === 'personalization') {
				return (
					$config?.features?.enable_memories &&
					($user?.role === 'admin' || ($user?.permissions?.features?.memories ?? true))
				);
			}

			return true;
		});

		return $user?.role === 'admin' ? [...personalSettings, ...adminSettings] : personalSettings;
	};

	const setFilteredSettings = () => {
		filteredSettings = availableSettings
			.filter((tab) => {
				const query = search.toLowerCase().trim();
				if (tab.id === 'admin:analytics' && !($config?.features.enable_admin_analytics ?? true)) {
					return false;
				}

				return (
					query === '' ||
					tab.title.toLowerCase().includes(query) ||
					tab.keywords.some((keyword) => keyword.includes(query))
				);
			})
			.map((tab) => tab.id);
		filteredPersonalSettings = filteredSettings.filter((tabId) => !isAdminTab(tabId));
		filteredAdminSettings = filteredSettings.filter((tabId) => isAdminTab(tabId));

		if ($user?.role !== 'admin' && isAdminTab(selectedTab)) {
			selectedTab = 'general';
		} else if (filteredSettings.length > 0 && !filteredSettings.includes(selectedTab)) {
			selectedTab = filteredSettings[0];
		}

		scrollToSelectedTab();
	};

	const saveSettings = async (updated: Record<string, any>) => {
		console.log(updated);
		await settings.set({ ...$settings, ...updated });
		await models.set(await getModels());
		await updateUserSettings(localStorage.token, { ui: $settings });
	};

	const getModels = async () => {
		return await _getModels(
			localStorage.token,
			$config?.features?.enable_direct_connections ? ($settings?.directConnections ?? null) : null
		);
	};

	const adminConfigSaveHandler = async () => {
		toast.success($i18n.t('Settings saved successfully!'));
		await tick();
		await config.set(await getBackendConfig());
	};

	const searchDebounceHandler = () => {
		if (searchDebounceTimeout) {
			clearTimeout(searchDebounceTimeout);
		}

		searchDebounceTimeout = setTimeout(() => {
			setFilteredSettings();
		}, 100);
	};

	const tabButtonClass = (active: boolean) =>
		`flex items-center gap-1.5 h-7 px-2 md:w-full shrink-0 rounded-lg text-xs text-left transition-colors duration-75 ${
			active
				? 'font-medium text-gray-900 dark:text-white bg-gray-50 dark:bg-white/[0.04]'
				: 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
		}`;

	let selectedTab = 'general';
	const scrollToSelectedTab = async () => {
		if (!browser || !modalShow || !selectedTab) {
			return;
		}

		await tick();
		const tabElement = document.querySelector<HTMLElement>(
			'#settings-tabs-container [role="tab"][aria-selected="true"]'
		);
		tabElement?.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'start' });
	};

	$: if ($user?.role !== 'admin' && isAdminTab(selectedTab)) {
		selectedTab = 'general';
	}

	$: if (modalShow && selectedTab) {
		scrollToSelectedTab();
	}

	onMount(() => {
		availableSettings = getAvailableSettings();
		setFilteredSettings();

		config.subscribe((configData) => {
			availableSettings = getAvailableSettings();
			setFilteredSettings();
		});
	});
</script>

<Modal
	size="full"
	containerClassName="p-4 sm:p-6 lg:p-8"
	className="!w-[calc(100vw-2rem)] sm:!w-[calc(100vw-3rem)] lg:!w-[calc(100vw-4rem)] !max-w-[80rem] h-[min(54rem,calc(100dvh-4rem))] max-h-[calc(100dvh-4rem)] flex flex-col md:flex-row bg-white dark:bg-gray-900 rounded-4xl"
	bind:show={modalShow}
>
	<nav
		id="settings-tabs-container"
		class="shrink-0 min-w-0 md:min-h-0 flex md:flex-col border-b md:border-b-0 md:border-r border-gray-100/30 dark:border-white/[0.02] md:w-[15rem]"
	>
		<button
			class="flex items-center gap-1.5 h-7 px-2 m-1 md:mb-0 md:w-[calc(100%-0.5rem)] shrink-0 rounded-lg text-xs text-gray-400 dark:text-gray-600 hover:text-gray-700 dark:hover:text-gray-300 transition-colors duration-75"
			type="button"
			on:click={() => {
				show = false;
			}}
		>
			<ChevronLeft className="size-3" strokeWidth="2" />
			<span>{$i18n.t('Back')}</span>
		</button>

		<div
			class="hidden md:flex items-center gap-1.5 h-7 px-2 mx-1 mt-1 mb-0.5 shrink-0 rounded-lg text-xs bg-gray-50/70 dark:bg-white/[0.03]"
		>
			<div class="self-center rounded-l-xl bg-transparent">
				<Search className="size-3.5" strokeWidth="1.5" />
			</div>
			<label class="sr-only" for="search-input-settings-modal">{$i18n.t('Search')}</label>
			<input
				data-settings-search
				class="w-full text-xs bg-transparent py-1 outline-hidden dark:text-gray-300"
				bind:value={search}
				id="search-input-settings-modal"
				on:input={searchDebounceHandler}
				placeholder={$i18n.t('Search')}
			/>
		</div>

		<div
			class="tabs scrollbar-none flex min-w-0 flex-1 min-h-0 overflow-x-auto md:overflow-x-hidden md:overflow-y-auto md:flex-col p-1 pl-0 md:pl-1 gap-px"
		>
			<span
				class="hidden md:block text-[0.625rem] text-gray-400 dark:text-gray-600 px-2 mt-1.5 mb-0.5"
			>
				{$i18n.t('Personal')}
			</span>

			{#if filteredPersonalSettings.length > 0}
				{#each filteredPersonalSettings as tabId, index (tabId)}
					{#if shouldShowSettingGroup(filteredPersonalSettings, index)}
						<span class={settingGroupHeadingClass(index === 0)}>
							{$i18n.t(settingGroupTitle(tabId))}
						</span>
					{/if}

					{#if tabId === 'general'}
						<button
							role="tab"
							aria-controls="tab-general"
							aria-selected={selectedTab === 'general'}
							class={tabButtonClass(selectedTab === 'general')}
							on:click={() => {
								selectedTab = 'general';
							}}
						>
							<SettingsAlt className="size-3.5" strokeWidth="2" />
							<span>{$i18n.t('General')}</span>
						</button>
					{:else if tabId === 'interface'}
						<button
							role="tab"
							aria-controls="tab-interface"
							aria-selected={selectedTab === 'interface'}
							class={tabButtonClass(selectedTab === 'interface')}
							on:click={() => {
								selectedTab = 'interface';
							}}
						>
							<AdjustmentsHorizontal className="size-3.5" strokeWidth="2" />
							<span>{$i18n.t('Interface')}</span>
						</button>
					{:else if tabId === 'notifications'}
						<button
							role="tab"
							aria-controls="tab-notifications"
							aria-selected={selectedTab === 'notifications'}
							class={tabButtonClass(selectedTab === 'notifications')}
							on:click={() => {
								selectedTab = 'notifications';
							}}
						>
							<AppNotification className="size-3.5" strokeWidth="2" />
							<span>{$i18n.t('Notifications')}</span>
						</button>
					{:else if tabId === 'shortcuts'}
						<button
							role="tab"
							aria-controls="tab-shortcuts"
							aria-selected={selectedTab === 'shortcuts'}
							class={tabButtonClass(selectedTab === 'shortcuts')}
							on:click={() => {
								selectedTab = 'shortcuts';
							}}
						>
							<Keyboard className="size-3.5" strokeWidth="2" />
							<span>{$i18n.t('Keyboard')}</span>
						</button>
					{:else if tabId === 'connections'}
						{#if $user?.role === 'admin' || ($user?.role === 'user' && $config?.features?.enable_direct_connections)}
							<button
								role="tab"
								aria-controls="tab-connections"
								aria-selected={selectedTab === 'connections'}
								class={tabButtonClass(selectedTab === 'connections')}
								on:click={() => {
									selectedTab = 'connections';
								}}
							>
								<Link className="size-3.5" strokeWidth="2" />
								<span>{$i18n.t('Connections')}</span>
							</button>
						{/if}
					{:else if tabId === 'tools'}
						{#if $user?.role === 'admin' || ($user?.role === 'user' && $user?.permissions?.features?.direct_tool_servers)}
							<button
								role="tab"
								aria-controls="tab-tools"
								aria-selected={selectedTab === 'tools'}
								class={tabButtonClass(selectedTab === 'tools')}
								on:click={() => {
									selectedTab = 'tools';
								}}
							>
								<WrenchAlt className="size-3.5" strokeWidth="2" />
								<span>{$i18n.t('Integrations')}</span>
							</button>
						{/if}
					{:else if tabId === 'personalization'}
						<button
							role="tab"
							aria-controls="tab-personalization"
							aria-selected={selectedTab === 'personalization'}
							class={tabButtonClass(selectedTab === 'personalization')}
							on:click={() => {
								selectedTab = 'personalization';
							}}
						>
							<Face className="size-3.5" strokeWidth="2" />
							<span>{$i18n.t('Personalization')}</span>
						</button>
					{:else if tabId === 'audio'}
						<button
							role="tab"
							aria-controls="tab-audio"
							aria-selected={selectedTab === 'audio'}
							class={tabButtonClass(selectedTab === 'audio')}
							on:click={() => {
								selectedTab = 'audio';
							}}
						>
							<SoundHigh className="size-3.5" strokeWidth="2" />
							<span>{$i18n.t('Audio')}</span>
						</button>
					{:else if tabId === 'data_controls'}
						<button
							role="tab"
							aria-controls="tab-data-controls"
							aria-selected={selectedTab === 'data_controls'}
							class={tabButtonClass(selectedTab === 'data_controls')}
							on:click={() => {
								selectedTab = 'data_controls';
							}}
						>
							<DatabaseSettings className="size-3.5" strokeWidth="2" />
							<span>{$i18n.t('Data Controls')}</span>
						</button>
					{:else if tabId === 'usage'}
						<button
							role="tab"
							aria-controls="tab-usage"
							aria-selected={selectedTab === 'usage'}
							class={tabButtonClass(selectedTab === 'usage')}
							on:click={() => {
								selectedTab = 'usage';
							}}
						>
							<UsageIcon className="size-3.5" strokeWidth="2" />
							<span>{$i18n.t('Usage')}</span>
						</button>
					{:else if tabId === 'archived_chats'}
						<button
							role="tab"
							aria-controls="tab-archived-chats"
							aria-selected={selectedTab === 'archived_chats'}
							class={tabButtonClass(selectedTab === 'archived_chats')}
							on:click={() => {
								selectedTab = 'archived_chats';
							}}
						>
							<ArchiveBox className="size-3.5" strokeWidth="2" />
							<span>{$i18n.t('Archived Chats')}</span>
						</button>
					{:else if tabId === 'account'}
						<button
							role="tab"
							aria-controls="tab-account"
							aria-selected={selectedTab === 'account'}
							class={tabButtonClass(selectedTab === 'account')}
							on:click={() => {
								selectedTab = 'account';
							}}
						>
							<UserCircle className="size-3.5" strokeWidth="2" />
							<span>{$i18n.t('Account')}</span>
						</button>
					{:else if tabId === 'about'}
						<button
							role="tab"
							aria-controls="tab-about"
							aria-selected={selectedTab === 'about'}
							class={tabButtonClass(selectedTab === 'about')}
							on:click={() => {
								selectedTab = 'about';
							}}
						>
							<InfoCircle className="size-3.5" strokeWidth="2" />
							<span>{$i18n.t('About')}</span>
						</button>
					{/if}
				{/each}
			{/if}

			{#if $user?.role === 'admin' && filteredAdminSettings.length > 0}
				<div
					class="hidden md:block shrink-0 self-stretch h-px mx-1 my-2 bg-gray-100/40 dark:bg-white/[0.025]"
				></div>
				<span class="hidden md:block text-[0.625rem] text-gray-400 dark:text-gray-600 px-2 mb-0.5">
					{$i18n.t('Admin')}
				</span>

				{#each filteredAdminSettings as tabId, index (tabId)}
					{#if shouldShowSettingGroup(filteredAdminSettings, index)}
						<span class={settingGroupHeadingClass(index === 0)}>
							{$i18n.t(settingGroupTitle(tabId))}
						</span>
					{/if}

					{@const tab = adminSettings.find((setting) => setting.id === tabId)}
					{#if tab}
						<button
							role="tab"
							aria-controls={adminTabPanelId(tab.id)}
							aria-selected={selectedTab === tab.id}
							class={tabButtonClass(selectedTab === tab.id)}
							on:click={() => {
								selectedTab = tab.id;
							}}
						>
							<AdminTabIcon id={adminTabSegment(tab.id)} className="size-3.5" strokeWidth="2" />
							<span>{$i18n.t(tab.title)}</span>
						</button>
					{/if}
				{/each}
			{/if}

			{#if filteredSettings.length === 0}
				<div class="px-2 py-1 text-xs text-gray-400 dark:text-gray-600">
					{$i18n.t('No matches')}
				</div>
			{/if}
		</div>
	</nav>

	<div class="flex-1 min-h-0 p-4 md:px-5 flex flex-col">
		<div class="flex-1 min-h-0 overflow-hidden">
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
			{:else if selectedTab === 'notifications'}
				<Notifications {saveSettings} />
			{:else if selectedTab === 'shortcuts'}
				<Shortcuts {saveSettings} />
			{:else if selectedTab === 'connections'}
				<Connections
					saveSettings={async (updated: Record<string, any>) => {
						await saveSettings(updated);
						toast.success($i18n.t('Settings saved successfully!'));
					}}
				/>
			{:else if selectedTab === 'tools'}
				<Integrations
					saveSettings={async (updated: Record<string, any>) => {
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
			{:else if selectedTab === 'usage'}
				<Usage />
			{:else if selectedTab === 'archived_chats'}
				<ArchivedChats />
			{:else if selectedTab === 'account'}
				<Account
					saveHandler={() => {
						toast.success($i18n.t('Settings saved successfully!'));
					}}
				/>
			{:else if selectedTab === 'about'}
				<About />
			{:else if selectedTab === 'admin:general'}
				<AdminGeneral saveHandler={adminConfigSaveHandler} />
			{:else if selectedTab === 'admin:authentication'}
				<AdminAuthentication />
			{:else if selectedTab === 'admin:connections'}
				<AdminConnections
					on:save={() => {
						toast.success($i18n.t('Settings saved successfully!'));
					}}
				/>
			{:else if selectedTab === 'admin:models'}
				<AdminModels bind:tabState />
			{:else if selectedTab === 'admin:subagents'}
				<AdminSubagents />
			{:else if selectedTab === 'admin:evaluations'}
				<AdminEvaluations />
			{:else if selectedTab === 'admin:analytics'}
				<AdminAnalytics />
			{:else if selectedTab === 'admin:integrations'}
				<AdminIntegrations {saveSettings} />
			{:else if selectedTab === 'admin:documents'}
				<AdminDocuments on:save={adminConfigSaveHandler} />
			{:else if selectedTab === 'admin:web'}
				<AdminWebSearch saveHandler={adminConfigSaveHandler} />
			{:else if selectedTab === 'admin:code-execution'}
				<AdminCodeExecution saveHandler={adminConfigSaveHandler} />
			{:else if selectedTab === 'admin:interface'}
				<AdminInterface
					on:save={() => {
						toast.success($i18n.t('Settings saved successfully!'));
					}}
				/>
			{:else if selectedTab === 'admin:audio'}
				<AdminAudio
					saveHandler={() => {
						toast.success($i18n.t('Settings saved successfully!'));
					}}
				/>
			{:else if selectedTab === 'admin:images'}
				<AdminImages
					on:save={() => {
						toast.success($i18n.t('Settings saved successfully!'));
					}}
				/>
			{:else if selectedTab === 'admin:db'}
				<AdminDatabase
					saveHandler={() => {
						toast.success($i18n.t('Settings saved successfully!'));
					}}
				/>
			{:else if selectedTab === 'admin:pipelines'}
				<AdminPipelines
					saveHandler={() => {
						toast.success($i18n.t('Settings saved successfully!'));
					}}
				/>
			{/if}
		</div>
	</div>
</Modal>
