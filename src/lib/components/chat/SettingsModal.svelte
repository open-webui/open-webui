<script lang="ts">
	import { browser } from '$app/environment';
	import { getContext, tick } from 'svelte';
	import type { Writable } from 'svelte/store';
	import { toast } from 'svelte-sonner';
	import { config, models, settings, user } from '$lib/stores';
	import type { SettingsModalRequest } from '$lib/stores';
	import { getUserSettings, updateUserSettings } from '$lib/apis/users';
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
	let personalUiSettings: Record<string, any> = {};

	const mergeUiSettings = (defaults: Record<string, any>, userSettings: Record<string, any>) => {
		const merged = { ...defaults };
		for (const [key, value] of Object.entries(userSettings)) {
			const defaultValue = merged[key];
			merged[key] =
				defaultValue &&
				value &&
				typeof defaultValue === 'object' &&
				typeof value === 'object' &&
				!Array.isArray(defaultValue) &&
				!Array.isArray(value)
					? mergeUiSettings(defaultValue, value)
					: value;
		}
		return merged;
	};

	const loadPersonalUiSettings = async () => {
		const userSettings = await getUserSettings(localStorage.token, true).catch((error) => {
			console.error(error);
			return null;
		});
		personalUiSettings =
			userSettings?.ui && typeof userSettings.ui === 'object' && !Array.isArray(userSettings.ui)
				? userSettings.ui
				: {};
	};

	$: if (show !== lastShow) {
		lastShow = show;
		if (show && typeof show === 'object') {
			selectedTab = show.tab;
			tabState = show.state ?? null;
			show = true;
			lastShow = true;
			modalShow = true;
			loadPersonalUiSettings();
		} else if (typeof show === 'string') {
			selectedTab = show;
			show = true;
			lastShow = true;
			modalShow = true;
			loadPersonalUiSettings();
		} else {
			modalShow = show;
			if (show) {
				loadPersonalUiSettings();
			}
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
	let personalSettingGroups: Record<string, string> = {};
	let adminSettingGroups: Record<string, string> = {};

	$: personalSettingGroups = {
		general: $i18n.t('Basics'),
		interface: $i18n.t('Basics'),
		notifications: $i18n.t('Basics'),
		shortcuts: $i18n.t('Basics'),
		connections: $i18n.t('Services'),
		tools: $i18n.t('Services'),
		personalization: $i18n.t('Preferences'),
		audio: $i18n.t('Preferences'),
		data_controls: $i18n.t('Data'),
		usage: $i18n.t('Data'),
		archived_chats: $i18n.t('Data'),
		account: $i18n.t('Profile'),
		about: $i18n.t('Profile')
	};
	$: adminSettingGroups = {
		'admin:general': $i18n.t('System'),
		'admin:authentication': $i18n.t('System'),
		'admin:connections': $i18n.t('AI'),
		'admin:models': $i18n.t('AI'),
		'admin:subagents': $i18n.t('AI'),
		'admin:evaluations': $i18n.t('Quality'),
		'admin:analytics': $i18n.t('Quality'),
		'admin:integrations': $i18n.t('Tools'),
		'admin:documents': $i18n.t('Tools'),
		'admin:web': $i18n.t('Tools'),
		'admin:code-execution': $i18n.t('Tools'),
		'admin:pipelines': $i18n.t('Tools'),
		'admin:interface': $i18n.t('Experience'),
		'admin:audio': $i18n.t('Experience'),
		'admin:images': $i18n.t('Experience'),
		'admin:db': $i18n.t('Data')
	};
	const settingGroupTitle = (tabId: string) =>
		(isAdminTab(tabId) ? adminSettingGroups[tabId] : personalSettingGroups[tabId]) ??
		$i18n.t('General');
	const shouldShowSettingGroup = (tabIds: string[], index: number) =>
		index === 0 || settingGroupTitle(tabIds[index]) !== settingGroupTitle(tabIds[index - 1]);
	const settingGroupHeadingClass = (first: boolean) =>
		`hidden md:block shrink-0 text-[0.625rem] text-gray-400 dark:text-gray-600 px-2 ${
			first ? 'mt-0.5' : 'mt-2'
		} mb-0.5`;

	const allSettings: SettingsTab[] = [
		{
			id: 'general',
			title: $i18n.t('General'),
			keywords: [
				'advanced parameters',
				'advanced params',
				'compaction',
				'configuration',
				'context compaction threshold',
				'custom parameter',
				'default parameters',
				'default settings',
				'function calling',
				'general',
				'keep alive',
				'language',
				'languages',
				'model parameters',
				'reasoning effort',
				'reasoning tags',
				'request mode',
				'seed',
				'stop sequence',
				'stream chat response',
				'stream delta chunk size',
				'system parameters',
				'system prompt',
				'system settings',
				'temperature',
				'theme',
				'token threshold',
				'translate',
				'webui settings'
			]
		},
		{
			id: 'interface',
			title: $i18n.t('Interface'),
			keywords: [
				'accessibility mode',
				'allow user location',
				'allow voice interruption in call',
				'always collapse code blocks',
				'always expand details',
				'always on web search',
				'always play notification sound',
				'android',
				'auto chat tags',
				'auto copy response to clipboard',
				'auto title',
				'call',
				'chat background image',
				'chat bubble ui',
				'chat direction',
				'chat tags autogeneration',
				'chat ui',
				'copy formatted text',
				'default model',
				'design',
				'detect artifacts automatically',
				'disable auto scroll',
				'display emoji in call',
				'display username',
				'enter key behavior',
				'expand mode',
				'file',
				'floating quick actions',
				'followup autogeneration',
				'full width mode',
				'fullscreen',
				'haptic feedback',
				'high contrast mode',
				'iframe sandbox allow forms',
				'iframe sandbox allow same origin',
				'image compression',
				'image max compression size',
				'interface customization',
				'interface options',
				'landing page mode',
				'layout',
				'left to right',
				'ltr',
				'paste large text as file',
				'reset background',
				'response auto copy',
				'response auto scroll',
				'rich text input for chat',
				'right to left',
				'rtl',
				'scroll behavior',
				'scroll on branch change',
				'select model',
				'settings',
				'show username',
				'stream large chunks',
				'stylized pdf export',
				'terminal preview allow same origin',
				'title autogeneration',
				'toast notifications for new updates',
				'upload background',
				'user interface',
				'user location access',
				'vibration',
				'voice control',
				'web search in chat',
				'whats new',
				'widescreen mode'
			]
		},
		{
			id: 'notifications',
			title: $i18n.t('Notifications'),
			keywords: [
				'automatic delivery',
				'automatic events',
				'browser notifications',
				'chat failed',
				'chat finished',
				'notification sound',
				'notification targets',
				'notifications',
				'notify',
				'send test notification',
				'webhook',
				'webhook notifications',
				'webhooks'
			]
		},
		{
			id: 'shortcuts',
			title: $i18n.t('Keyboard'),
			keywords: [
				'commands',
				'focus chat input',
				'hotkeys',
				'keybindings',
				'keyboard',
				'keyboard shortcuts',
				'keys',
				'rebind',
				'reset defaults',
				'shortcut',
				'shortcuts',
				'show shortcuts',
				'toggle sidebar'
			]
		},
		{
			id: 'connections',
			title: $i18n.t('Connections'),
			keywords: [
				'add connection',
				'api base url',
				'api key',
				'direct connections',
				'manage connections',
				'manage direct connections',
				'ollama api',
				'openai api',
				'settings'
			]
		},
		{
			id: 'tools',
			title: $i18n.t('Integrations'),
			keywords: [
				'add connection',
				'external tool servers',
				'integrations',
				'manage tool servers',
				'manage tools',
				'mcp',
				'mcp server',
				'model context protocol',
				'oauth',
				'open terminal',
				'openapi',
				'settings',
				'terminal',
				'tool server',
				'tools'
			]
		},

		{
			id: 'personalization',
			title: $i18n.t('Personalization'),
			keywords: [
				'account preferences',
				'account settings',
				'custom settings',
				'experimental',
				'memories',
				'memory',
				'personal settings',
				'personalization',
				'personalize',
				'profile',
				'saved memories',
				'search memories',
				'user preferences'
			]
		},
		{
			id: 'audio',
			title: $i18n.t('Audio'),
			keywords: [
				'audio',
				'audio config',
				'audio control',
				'audio features',
				'audio input',
				'audio output',
				'audio playback',
				'audio voice',
				'auto playback response',
				'auto transcribe',
				'dictation',
				'instant auto send after voice transcription',
				'language',
				'microphone',
				'non local voices',
				'set voice',
				'sound settings',
				'speech config',
				'speech mode',
				'speech playback speed',
				'speech rate',
				'speech recognition',
				'speech settings',
				'speech speed',
				'speech synthesis',
				'speech to text engine',
				'stt settings',
				'text to speech',
				'text to speech engine',
				'text to speech voice',
				'transcription',
				'voice',
				'voice control',
				'voice modes',
				'voice options',
				'voice playback',
				'voice recognition',
				'voice speed',
				'volume'
			]
		},
		{
			id: 'data_controls',
			title: $i18n.t('Data Controls'),
			keywords: [
				'archive all chats',
				'archive chats',
				'chat activity',
				'chat history',
				'chat settings',
				'conversation activity',
				'conversation history',
				'conversations',
				'convos',
				'delete all chats',
				'delete chats',
				'export chats',
				'files',
				'import chats',
				'manage files',
				'message archive',
				'message history',
				'shared chats'
			]
		},
		{
			id: 'usage',
			title: $i18n.t('Usage'),
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
				'top models',
				'usage'
			]
		},
		{
			id: 'archived_chats',
			title: $i18n.t('Archived Chats'),
			keywords: [
				'archive',
				'archive chat',
				'archived chats',
				'conversation archive',
				'message archive',
				'unarchive',
				'unarchive chats'
			]
		},
		{
			id: 'account',
			title: $i18n.t('Account'),
			keywords: [
				'account preferences',
				'account settings',
				'api key',
				'api keys',
				'bio',
				'birth date',
				'change password',
				'gender',
				'jwt token',
				'login',
				'new password',
				'notification webhook url',
				'password',
				'personal settings',
				'privacy settings',
				'profile avatar',
				'profile details',
				'profile image',
				'profile picture',
				'secrets',
				'security settings',
				'update account',
				'update password',
				'user account',
				'user data',
				'user preferences',
				'user profile',
				'user variables',
				'username',
				'webhook url'
			]
		},
		{
			id: 'about',
			title: $i18n.t('About'),
			keywords: [
				'about app',
				'about me',
				'about open webui',
				'about page',
				'about us',
				'check for updates',
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
				'settings',
				'software info',
				'support',
				'terms and conditions',
				'terms of use',
				'timothy j baek',
				'timothy jae ryang baek',
				'twitter',
				'update info',
				'version info'
			]
		}
	];

	const adminSettings: SettingsTab[] = [
		{
			id: 'admin:general',
			title: $i18n.t('General'),
			keywords: [
				'admin',
				'automations',
				'banners',
				'calendar',
				'channels',
				'check for updates',
				'community sharing',
				'default interface settings',
				'features',
				'folder max file count',
				'folders',
				'general',
				'license',
				'memories',
				'memory system context',
				'message rating',
				'model response mode',
				'notes',
				'response watermark',
				'settings',
				'update',
				'user status',
				'user webhooks',
				'version',
				'webui url'
			]
		},
		{
			id: 'admin:authentication',
			title: $i18n.t('Authentication'),
			keywords: [
				'admin roles',
				'allowed domains',
				'api key endpoint restrictions',
				'api keys',
				'auth',
				'authentication',
				'default user role',
				'endpoint restrictions',
				'group mapping',
				'jwt expiration',
				'ldap',
				'login',
				'login form',
				'new sign ups',
				'oauth',
				'oidc',
				'pending accounts',
				'redirect uri',
				'role mapping',
				'roles',
				'signup',
				'sso',
				'trusted header',
				'user access'
			]
		},
		{
			id: 'admin:connections',
			title: $i18n.t('Connections'),
			keywords: [
				'api',
				'api key',
				'base url',
				'cache base model list',
				'connections',
				'direct connections',
				'direct integrations',
				'ollama',
				'ollama api',
				'openai',
				'openai api',
				'proxy',
				'user connections'
			]
		},
		{
			id: 'admin:models',
			title: $i18n.t('Models'),
			keywords: [
				'base model',
				'create',
				'delete',
				'edit',
				'export',
				'gguf',
				'import',
				'model defaults',
				'modelfile',
				'models',
				'prompt suggestions',
				'pull'
			]
		},
		{
			id: 'admin:subagents',
			title: $i18n.t('Sub-agents'),
			keywords: [
				'agents',
				'background sub agents',
				'delegation',
				'max concurrent',
				'max iterations',
				'sub agents',
				'tool loops'
			]
		},
		{
			id: 'admin:interface',
			title: $i18n.t('Interface'),
			keywords: [
				'appearance',
				'autocomplete generation',
				'compaction',
				'context compaction',
				'context compaction model',
				'context compaction prompt',
				'external task model',
				'follow up generation',
				'image prompt generation',
				'interface',
				'local task model',
				'prompt template',
				'retained messages',
				'retrieval query generation',
				'tags generation',
				'task model',
				'task model parameters',
				'tasks',
				'title generation',
				'token cap',
				'token threshold',
				'tool permissions',
				'tools function calling prompt',
				'ui',
				'voice mode prompt',
				'web search query generation'
			]
		},
		{
			id: 'admin:audio',
			title: $i18n.t('Audio'),
			keywords: [
				'audio',
				'azure ai speech',
				'deepgram',
				'elevenlabs',
				'speech',
				'speech to text',
				'stt',
				'text to speech',
				'transcription',
				'tts',
				'voice',
				'whisper'
			]
		},
		{
			id: 'admin:images',
			title: $i18n.t('Images'),
			keywords: [
				'automatic1111',
				'comfyui',
				'dalle',
				'gemini',
				'image edit',
				'image generation',
				'image prompt generation',
				'image size',
				'images',
				'stable diffusion'
			]
		},
		{
			id: 'admin:evaluations',
			title: $i18n.t('Evaluations'),
			keywords: [
				'arena',
				'arena models',
				'evaluations',
				'feedback',
				'leaderboard',
				'preference',
				'rating'
			]
		},
		{
			id: 'admin:analytics',
			title: $i18n.t('Analytics'),
			keywords: ['analytics', 'dashboard', 'messages', 'models', 'stats', 'usage', 'users']
		},
		{
			id: 'admin:integrations',
			title: $i18n.t('Integrations'),
			keywords: [
				'add connection',
				'extensions',
				'external knowledge',
				'external tool servers',
				'functions',
				'integrations',
				'knowledge',
				'mcp',
				'mcp server',
				'model context protocol',
				'oauth',
				'open terminal',
				'openapi',
				'plugins',
				'server',
				'terminal',
				'tool server',
				'tools'
			]
		},
		{
			id: 'admin:documents',
			title: $i18n.t('Documents'),
			keywords: [
				'allowed file extensions',
				'bm25',
				'chunk overlap',
				'chunk size',
				'content extraction',
				'docling',
				'document intelligence',
				'documents',
				'embedding',
				'embedding model',
				'files',
				'google drive',
				'hybrid search',
				'knowledge',
				'mistral ocr',
				'ocr',
				'onedrive',
				'rag',
				'reranker',
				'retrieval',
				'upload',
				'vector db'
			]
		},
		{
			id: 'admin:web',
			title: $i18n.t('Web Search'),
			keywords: [
				'bing',
				'brave',
				'duckduckgo',
				'exa',
				'firecrawl',
				'google',
				'jina',
				'kagi',
				'mojeek',
				'perplexity',
				'playwright',
				'search engine',
				'searchapi',
				'searxng',
				'serpapi',
				'serper',
				'tavily',
				'web loader',
				'web search',
				'yacy',
				'yandex'
			]
		},
		{
			id: 'admin:code-execution',
			title: $i18n.t('Code Execution'),
			keywords: [
				'code execution',
				'code interpreter',
				'compiler',
				'interpreter',
				'jupyter',
				'pyodide',
				'python',
				'sandbox'
			]
		},
		{
			id: 'admin:pipelines',
			title: $i18n.t('Pipelines'),
			keywords: ['filters', 'middleware', 'pipelines', 'valves', 'workflows']
		},

		{
			id: 'admin:db',
			title: $i18n.t('Database'),
			keywords: ['backup', 'chats', 'database', 'db', 'export', 'import', 'users']
		}
	];
	let availableSettings: SettingsTab[] = [];
	let filteredSettings: string[] = [];
	let filteredPersonalSettings: string[] = [];
	let filteredAdminSettings: string[] = [];

	let search = '';
	let searchDebounceTimeout: ReturnType<typeof setTimeout> | null = null;

	const normalizeSearchText = (value: string) =>
		value
			.toLowerCase()
			.replace(/[^\p{L}\p{N}\p{M}]+/gu, ' ')
			.trim();

	const getSearchText = (tab: SettingsTab) => {
		const words = new Set<string>();

		for (const phrase of [tab.title, ...tab.keywords]) {
			const normalized = normalizeSearchText(phrase);

			for (const word of normalized.split(' ')) {
				words.add(word);
			}
			// Spaceless form too, so "chatui" finds the "chat ui" keyword.
			words.add(normalized.replace(/ /g, ''));
		}

		return [...words].join(' ');
	};

	const getAvailableSettings = () => {
		const personalSettings = allSettings.filter((tab) => {
			if (tab.id === 'connections') {
				return $config?.features?.enable_direct_connections;
			}

			if (tab.id === 'tools') {
				return (
					$config?.features?.enable_direct_integrations === true &&
					($user?.role === 'admin' ||
						($user?.role === 'user' && $user?.permissions?.features?.direct_tool_servers))
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
		const query = search.trim();
		const queryWords = normalizeSearchText(query).split(' ').filter(Boolean);

		filteredSettings = availableSettings
			.filter((tab) => {
				if (tab.id === 'admin:analytics' && !($config?.features.enable_admin_analytics ?? true)) {
					return false;
				}

				if (queryWords.length === 0) {
					return query === '';
				}

				// Word order must not matter: "compaction context" finds the same tab as "context compaction".
				const searchText = getSearchText(tab);
				return queryWords.every((word) => searchText.includes(word));
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
		const saved = await updateUserSettings(localStorage.token, {
			ui: updated
		}).catch((error) => {
			toast.error(`${error}`);
			throw error;
		});
		personalUiSettings =
			saved?.ui && typeof saved.ui === 'object' && !Array.isArray(saved.ui) ? saved.ui : {};
		await settings.set(
			mergeUiSettings($config?.ui?.default_interface_settings ?? {}, personalUiSettings)
		);
		await models.set(await getModels());
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

	$: if (selectedTab === 'tools' && !availableSettings.some((tab) => tab.id === 'tools')) {
		selectedTab = 'general';
	}

	$: if (modalShow && selectedTab) {
		scrollToSelectedTab();
	}

	$: if ($config && $user) {
		availableSettings = getAvailableSettings();
		setFilteredSettings();
	}
</script>

<Modal
	size="full"
	containerClassName="p-4 sm:p-6 lg:p-8"
	className="!w-[calc(100vw-2rem)] sm:!w-[calc(100vw-3rem)] lg:!w-[calc(100vw-4rem)] !max-w-[80rem] h-[min(max(54rem,80dvh),calc(100dvh-4rem))] max-h-[calc(100dvh-4rem)] flex flex-col md:flex-row bg-white dark:bg-gray-900 rounded-4xl overflow-hidden"
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
							{settingGroupTitle(tabId)}
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
							{settingGroupTitle(tabId)}
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
							<span>{tab.title}</span>
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

	<div class="flex-1 min-w-0 min-h-0 p-4 md:px-5 flex flex-col">
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
					personalSettingsValue={personalUiSettings}
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
