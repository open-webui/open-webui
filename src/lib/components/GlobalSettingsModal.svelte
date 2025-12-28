<script lang="ts">
	import { onMount, tick, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import {
		showSettingsSearch,
		showSettings,
		activeSettingsTab,
		user,
		config,
		settings
	} from '$lib/stores';

	import Search from '$lib/components/icons/Search.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';

	// Admin Icons
	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import Cloud from '$lib/components/icons/Cloud.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';
	import DocumentChartBar from '$lib/components/icons/DocumentChartBar.svelte';
	import Wrench from '$lib/components/icons/Wrench.svelte';
	import BookOpen from '$lib/components/icons/BookOpen.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import CommandLine from '$lib/components/icons/CommandLine.svelte';
	import ChatBubbleOval from '$lib/components/icons/ChatBubbleOval.svelte';
	import Headphone from '$lib/components/icons/Headphone.svelte';
	import Photo from '$lib/components/icons/Photo.svelte';
	import AdjustmentsHorizontal from '$lib/components/icons/AdjustmentsHorizontal.svelte';
	import Database from '$lib/components/icons/Database.svelte';

	// User Icons
	import SettingsAlt from '$lib/components/icons/SettingsAlt.svelte';
	import AppNotification from '$lib/components/icons/AppNotification.svelte';
	import Link from '$lib/components/icons/Link.svelte';
	import WrenchAlt from '$lib/components/icons/WrenchAlt.svelte';
	import Face from '$lib/components/icons/Face.svelte';
	import SoundHigh from '$lib/components/icons/SoundHigh.svelte';
	import DatabaseSettings from '$lib/components/icons/DatabaseSettings.svelte';
	import UserCircle from '$lib/components/icons/UserCircle.svelte';
	import InfoCircle from '$lib/components/icons/InfoCircle.svelte';

	import type { Writable } from 'svelte/store';

	const i18n: Writable<any> = getContext('i18n');

	export let show = false;

	let search = '';
	let searchInput: HTMLInputElement;
	let selectedIndex = 0;

	// Admin Settings Data
	const adminSettings = [
		{
			id: 'general',
			title: 'General',
			route: '/admin/settings/general',
			type: 'admin',
			icon: Cog6,
			keywords: [
				'admin',
				'authentication',
				'channels',
				'community',
				'data',
				'general',
				'language',
				'ldap',
				'reverse proxy',
				'roles',
				'settings',
				'theme',
				'update',
				'users',
				'version',
				'webhook'
			]
		},
		{
			id: 'connections',
			title: 'Connections',
			route: '/admin/settings/connections',
			type: 'admin',
			icon: Cloud,
			keywords: [
				'api',
				'base url',
				'connections',
				'direct connections',
				'key',
				'ollama',
				'openai',
				'proxy'
			]
		},
		{
			id: 'models',
			title: 'Models',
			route: '/admin/settings/models',
			type: 'admin',
			icon: Sparkles,
			keywords: [
				'create',
				'delete',
				'edit',
				'export',
				'gguf',
				'import',
				'modelfile',
				'models',
				'pull'
			]
		},
		{
			id: 'evaluations',
			title: 'Evaluations',
			route: '/admin/settings/evaluations',
			type: 'admin',
			icon: DocumentChartBar,
			keywords: [
				'arena models',
				'arena',
				'evaluations',
				'feedback',
				'leaderboard',
				'preference',
				'rating'
			]
		},
		{
			id: 'tools',
			title: 'External Tools',
			route: '/admin/settings/tools',
			type: 'admin',
			icon: Wrench,
			keywords: [
				'extensions',
				'functions',
				'mcp',
				'openapi',
				'plugins',
				'server',
				'tool servers',
				'tools'
			]
		},
		{
			id: 'documents',
			title: 'Documents',
			route: '/admin/settings/documents',
			type: 'admin',
			icon: BookOpen,
			keywords: [
				'chunk',
				'docling',
				'documents',
				'embedding',
				'files',
				'hybrid search',
				'knowledge',
				'ocr',
				'overlap',
				'pdf',
				'query params',
				'rag',
				'splitter',
				'tika',
				'top k',
				'unstructured',
				'upload',
				'vector db'
			]
		},
		{
			id: 'web',
			title: 'Web Search',
			route: '/admin/settings/web',
			type: 'admin',
			icon: GlobeAlt,
			keywords: [
				'bing',
				'duckduckgo',
				'exa',
				'firecrawl',
				'google',
				'moojeh',
				'perplexity',
				'searxng',
				'serp',
				'serper',
				'serply',
				'tavily',
				'web search',
				'yacy'
			]
		},
		{
			id: 'code-execution',
			title: 'Code Execution',
			route: '/admin/settings/code-execution',
			type: 'admin',
			icon: CommandLine,
			keywords: [
				'code execution',
				'compiler',
				'interpreter',
				'jupyter',
				'python',
				'sandbox',
				'unsafe mode'
			]
		},
		{
			id: 'interface',
			title: 'Interface',
			route: '/admin/settings/interface',
			type: 'admin',
			icon: ChatBubbleOval,
			keywords: [
				'appearance',
				'banners',
				'default models',
				'interface',
				'prompt suggestions',
				'tags',
				'tasks',
				'title generation',
				'ui'
			]
		},
		{
			id: 'audio',
			title: 'Audio',
			route: '/admin/settings/audio',
			type: 'admin',
			icon: Headphone,
			keywords: [
				'audio',
				'azure',
				'deepgram',
				'elevenlabs',
				'openai',
				'speech to text',
				'speech',
				'stt',
				'text to speech',
				'tts',
				'voice',
				'whisper'
			]
		},
		{
			id: 'images',
			title: 'Images',
			route: '/admin/settings/images',
			type: 'admin',
			icon: Photo,
			keywords: [
				'automatic1111',
				'comfyui',
				'dalle',
				'gemini',
				'generation',
				'image generation',
				'image size',
				'images',
				'stable diffusion',
				'steps'
			]
		},
		{
			id: 'pipelines',
			title: 'Pipelines',
			route: '/admin/settings/pipelines',
			type: 'admin',
			icon: AdjustmentsHorizontal,
			keywords: [
				'filters',
				'middleware',
				'pipelines',
				'plugins',
				'valves',
				'workflows'
			]
		},
		{
			id: 'db',
			title: 'Database',
			route: '/admin/settings/db',
			type: 'admin',
			icon: Database,
			keywords: [
				'backup',
				'chats',
				'database',
				'download',
				'export',
				'import',
				'reset',
				'users'
			]
		}
	];

	// User Settings Data
	const userSettings = [
		{
			id: 'general',
			title: 'General',
			type: 'user',
			icon: SettingsAlt,
			keywords: [
				'advanced parameters',
				'advanced params',
				'advanced',
				'configuration',
				'default parameters',
				'default settings',
				'general settings',
				'general',
				'keep alive',
				'languages',
				'notifications',
				'params',
				'repeat penalty',
				'request mode',
				'stream response',
				'system parameters',
				'system prompt',
				'system settings',
				'temperature',
				'theme',
				'top k',
				'top p',
				'translate',
				'webui settings'
			]
		},
		{
			id: 'interface',
			title: 'Interface',
			type: 'user',
			icon: AppNotification,
			keywords: [
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
				'beta',
				'call',
				'changelog',
				'chat background image',
				'chat bubble ui',
				'chat bubble',
				'chat direction',
				'chat tags',
				'chat ui',
				'copy formatted text',
				'dark mode',
				'default model',
				'design',
				'detect artifacts automatically',
				'display emoji in call',
				'display username',
				'enter key behavior',
				'expand mode',
				'file',
				'floating action buttons',
				'followup autogeneration',
				'full width',
				'fullscreen',
				'haptic feedback',
				'high contrast mode',
				'high contrast',
				'iframe sandbox',
				'image compression',
				'interface customization',
				'interface options',
				'landing page mode',
				'landing page',
				'language',
				'layout',
				'light mode',
				'ltr',
				'notifications',
				'oled',
				'paste large text as file',
				'reset background',
				'response auto copy',
				'rich text input',
				'rtl',
				'scroll behavior',
				'scroll on branch change',
				'select model',
				'settings',
				'show username',
				'stream large chunks',
				'stylized pdf export',
				'temporary chat',
				'text scale',
				'theme',
				'title autogeneration',
				'toast notifications',
				'toast',
				'ui scale',
				'upload background',
				'user interface',
				'user location',
				'vibration',
				'voice control',
				'web search in chat',
				'whats new',
				'widescreen mode',
				'widescreen'
			]
		},
		{
			id: 'connections',
			title: 'Connections',
			type: 'user',
			icon: Link,
			keywords: [
				'add connection',
				'api key',
				'base url',
				'connections',
				'direct connection',
				'manage connections',
				'manage direct connections',
				'ollama',
				'openai',
				'settings'
			]
		},
		{
			id: 'tools',
			title: 'External Tools',
			type: 'user',
			icon: WrenchAlt,
			keywords: [
				'add connection',
				'external tools',
				'manage tool servers',
				'manage tools',
				'mcp',
				'settings',
				'tool servers'
			]
		},
		{
			id: 'personalization',
			title: 'Personalization',
			type: 'user',
			icon: Face,
			keywords: [
				'account preferences',
				'account settings',
				'custom instructions',
				'custom settings',
				'experimental',
				'manage memories',
				'memories',
				'memory',
				'personal settings',
				'personalization',
				'personalize',
				'profile',
				'user preferences'
			]
		},
		{
			id: 'audio',
			title: 'Audio',
			type: 'user',
			icon: SoundHigh,
			keywords: [
				'audio config',
				'audio control',
				'audio features',
				'audio input',
				'audio output',
				'audio playback',
				'audio voice',
				'auto playback response',
				'auto playback',
				'auto send',
				'auto transcribe',
				'instant auto send',
				'kokoro',
				'language',
				'non local voices',
				'playback speed',
				'save settings',
				'set voice',
				'sound settings',
				'speech config',
				'speech playback speed',
				'speech rate',
				'speech recognition',
				'speech settings',
				'speech synthesis',
				'speech to text',
				'stt settings',
				'stt',
				'text to speech',
				'tts settings',
				'tts',
				'voice control',
				'voice options',
				'voice playback',
				'voice recognition',
				'voice speed',
				'voice',
				'volume',
				'whisper'
			]
		},
		{
			id: 'data_controls',
			title: 'Data Controls',
			type: 'user',
			icon: DatabaseSettings,
			keywords: [
				'archive all chats',
				'archive chats',
				'archived chats',
				'archive',
				'chat activity',
				'chat history',
				'chat settings',
				'chats',
				'conversation activity',
				'conversation history',
				'conversations',
				'delete all chats',
				'delete chats',
				'delete',
				'export chats',
				'export',
				'history',
				'import chats',
				'import',
				'message activity',
				'message archive',
				'message history',
				'reset'
			]
		},
		{
			id: 'account',
			title: 'Account',
			type: 'user',
			icon: UserCircle,
			keywords: [
				'account preferences',
				'account settings',
				'api keys',
				'api key',
				'avatar',
				'bio',
				'change password',
				'jwt token',
				'jwt',
				'login',
				'name',
				'new password',
				'notification webhook',
				'password',
				'personal settings',
				'privacy settings',
				'profile avatar',
				'profile details',
				'profile image',
				'profile picture',
				'security settings',
				'security',
				'update account',
				'update password',
				'user account',
				'user data',
				'user preferences',
				'user profile',
				'webhook url',
				'webhook'
			]
		},
		{
			id: 'about',
			title: 'About',
			type: 'user',
			icon: InfoCircle,
			keywords: [
				'about app',
				'about me',
				'about open webui',
				'about page',
				'about us',
				'changelog',
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
				'twitter',
				'update info',
				'update',
				'version info',
				'version'
			]
		}
	];

	let filteredResults: any[] = [];

	$: if (show) {
		search = '';
		selectedIndex = 0;
		filterSettings();
		tick().then(() => {
			searchInput?.focus();
		});
	}

	const filterSettings = () => {
		const query = search.toLowerCase().trim();
		let results: any[] = [];

		if (query === '') {
			filteredResults = [];
			return;
		}

		// Filter Admin Settings
		if ($user?.role === 'admin') {
			const adminMatches = adminSettings.filter(item => 
				item.title.toLowerCase().includes(query) || 
				item.keywords.some(k => k.includes(query))
			);
			results = [...results, ...adminMatches];
		}

		// Filter User Settings
		const userMatches = userSettings.filter(item => {
			if (item.id === 'connections' && !$config?.features?.enable_direct_connections) return false;
			if (item.id === 'tools' && !($user?.role === 'admin' || $user?.permissions?.features?.direct_tool_servers)) return false;

			return item.title.toLowerCase().includes(query) || 
				   item.keywords.some(k => k.includes(query));
		});
		results = [...results, ...userMatches];

		filteredResults = results;
		selectedIndex = 0;
	};

	const handleSelect = async (item: any) => {
		show = false;
		if (item.type === 'admin') {
			goto(item.route);
		} else {
			activeSettingsTab.set(item.id);
			showSettings.set(true);
		}
	};

	const handleKeydown = (e: KeyboardEvent) => {
		if (!show) return;

		if (e.key === 'ArrowDown') {
			e.preventDefault();
			selectedIndex = (selectedIndex + 1) % filteredResults.length;
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			selectedIndex = (selectedIndex - 1 + filteredResults.length) % filteredResults.length;
		} else if (e.key === 'Enter') {
			e.preventDefault();
			if (filteredResults[selectedIndex]) {
				handleSelect(filteredResults[selectedIndex]);
			}
		} else if (e.key === 'Escape') {
			show = false;
		}
	};

</script>

<svelte:window on:keydown={handleKeydown} />

<Modal size="lg" bind:show className="bg-transparent dark:bg-transparent rounded-xl">
	<div class="flex flex-col max-h-[500px] bg-white dark:bg-gray-900 rounded-xl overflow-hidden text-gray-700 dark:text-gray-100">
		<!-- Search Input Header -->
		<div class="flex items-center p-3 border-b border-gray-100 dark:border-gray-800">
			<div class="px-2 text-gray-500">
				<Search className="size-5" />
			</div>
			<input
				bind:this={searchInput}
				bind:value={search}
				on:input={filterSettings}
				class="flex-1 bg-transparent px-2 py-1 outline-none text-lg placeholder-gray-400"
				placeholder={$i18n.t('Search settings...')}
				autocomplete="off"
				spellcheck="false"
			/>
			<div class="flex items-center gap-1.5 ">
				<div class="text-xs text-gray-500 bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded-md font-medium border border-gray-200 dark:border-gray-700">
					ESC
				</div>
			</div>
		</div>

		<!-- Results List -->
		<div class="overflow-y-auto p-2">
			{#if filteredResults.length > 0}
				{#each filteredResults as item, index}
					<button
						class="w-full flex items-center gap-3 p-3 rounded-lg text-left transition-colors {index === selectedIndex ? 'bg-gray-100 dark:bg-gray-800' : 'hover:bg-gray-50 dark:hover:bg-gray-850'}"
						on:click={() => handleSelect(item)}
						on:mouseenter={() => selectedIndex = index}
					>
						<div class="flex-shrink-0 text-gray-400 bg-gray-50 dark:bg-gray-800 p-2 rounded-lg">
							<svelte:component this={item.icon} className="size-5" />
						</div>
						<div class="flex-1 min-w-0">
							<div class="font-medium flex items-center gap-2">
								{item.title}
								{#if item.type === 'admin'}
									<span class="text-[10px] uppercase tracking-wider text-gray-400 bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded-md">Admin</span>
								{/if}
							</div>
							<div class="text-xs text-gray-500 truncate flex items-center gap-1">
								{#if item.type === 'admin'}
									<span>Admin Panel</span>
									<ChevronRight className="size-3" />
									<span>Settings</span>
									<ChevronRight className="size-3" />
									<span>{item.title}</span>
								{:else}
									<span>Settings</span>
									<ChevronRight className="size-3" />
									<span>{item.title}</span>
								{/if}
							</div>
						</div>
					</button>
				{/each}
			{:else}
				<div class="text-center py-12 text-gray-500">
					{#if search === ''}
						<div class="text-sm">Type to search settings...</div>
					{:else}
						<div class="text-sm">No settings found.</div>
					{/if}
				</div>
			{/if}
		</div>
	</div>
</Modal>
