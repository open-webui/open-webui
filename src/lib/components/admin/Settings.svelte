<script lang="ts">
	import { getContext, tick, onMount, onDestroy } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	import { config, user, settings, models } from '$lib/stores';
	import { getBackendConfig, getModels as _getModels } from '$lib/apis';
	import { updateUserSettings } from '$lib/apis/users';
	import Database from './Settings/Database.svelte';

	// Admin Settings Components
	import General from './Settings/General.svelte';
	import Pipelines from './Settings/Pipelines.svelte';
	import Audio from './Settings/Audio.svelte';
	import Images from './Settings/Images.svelte';
	import Interface from './Settings/Interface.svelte';
	import Models from './Settings/Models.svelte';
	import Connections from './Settings/Connections.svelte';
	import Documents from './Settings/Documents.svelte';
	import WebSearch from './Settings/WebSearch.svelte';

	import Evaluations from './Settings/Evaluations.svelte';
	import CodeExecution from './Settings/CodeExecution.svelte';
	import Tools from './Settings/Tools.svelte';

	// User Settings Components
	import UserGeneral from './Settings/User/General.svelte';
	import UserAudio from './Settings/User/Audio.svelte';
	import UserConnections from './Settings/User/Connections.svelte';
	import UserTools from './Settings/User/Tools.svelte';
	import UserPersonalization from './Settings/User/Personalization.svelte';
	import UserDataControls from './Settings/User/DataControls.svelte';
	import UserAccount from './Settings/User/Account.svelte';
	import UserAbout from './Settings/User/About.svelte';

	import Search from '../icons/Search.svelte';

	import type { Writable } from 'svelte/store';
	const i18n: Writable<any> = getContext('i18n');

	let selectedTab = 'general';

	// Get current tab from URL pathname, default to 'user-general' for non-admin users
	$: {
		const pathParts = $page.url.pathname.split('/');
		const tabFromPath = pathParts[pathParts.length - 1];
		const validTabs = [
			// Admin tabs
			'general',
			'connections',
			'models',
			'evaluations',
			'tools',
			'documents',
			'web',
			'code-execution',
			'interface',
			'audio',
			'images',
			'pipelines',
			'db',
			// User tabs
			'user-general',
			'user-connections',
			'user-tools',
			'user-personalization',
			'user-audio',
			'user-data',
			'user-account',
			'user-about'
		];

		if (validTabs.includes(tabFromPath)) {
			selectedTab = tabFromPath;
		} else {
			// Default to user-general for non-admin, general for admin
			selectedTab = $user?.role === 'admin' ? 'general' : 'user-general';
		}
	}

	$: if (selectedTab) {
		// scroll to selectedTab
		scrollToTab(selectedTab);
	}

	const scrollToTab = (tabId: string) => {
		const tabElement = document.getElementById(tabId);
		if (tabElement) {
			tabElement.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'start' });
		}
	};

	let search = '';
	let searchDebounceTimeout: any;
	let filteredSettings: any[] = [];
	let searchVisible = true;

	let tabsContainer: HTMLElement | null = null;
	const tabsWheelHandler = (event: WheelEvent) => {
		if (!tabsContainer) {
			return;
		}

		if (event.deltaY !== 0) {
			tabsContainer.scrollLeft += event.deltaY;
		}
	};

	const updateSearchVisibility = () => {
		if (typeof window === 'undefined') {
			return;
		}

		const visible = window.matchMedia('(min-width: 768px)').matches;
		if (searchVisible !== visible) {
			searchVisible = visible;
			if (!searchVisible && search !== '') {
				search = '';
			}
		}
	};

	const allSettings = [
		// ========== 用户设置 (所有用户可见) ==========
		{
			id: 'user-general',
			title: '个人设置',
			route: '/settings/user-general',
			keywords: ['user', 'general', 'theme', 'language', 'notifications', 'system prompt', 'parameters'],
			adminOnly: false,
			category: 'user'
		},
		{
			id: 'user-account',
			title: '账户信息',
			route: '/settings/user-account',
			keywords: ['account', 'profile', 'password', 'api key', 'webhook'],
			adminOnly: false,
			category: 'user'
		},
		{
			id: 'user-connections',
			title: '个人连接',
			route: '/settings/user-connections',
			keywords: ['connections', 'direct', 'openai', 'api'],
			adminOnly: false,
			category: 'user',
			featureFlag: 'enable_direct_connections'
		},
		{
			id: 'user-tools',
			title: '个人工具',
			route: '/settings/user-tools',
			keywords: ['tools', 'servers', 'openapi'],
			adminOnly: false,
			category: 'user',
			permissionCheck: (user) => user?.role === 'admin' || user?.permissions?.features?.direct_tool_servers
		},
		{
			id: 'user-personalization',
			title: '个性化',
			route: '/settings/user-personalization',
			keywords: ['personalization', 'memory', 'memories'],
			adminOnly: false,
			category: 'user',
			featureFlag: 'enable_memories',
			permissionCheck: (user) => user?.role === 'admin' || (user?.permissions?.features?.memories ?? true)
		},
		{
			id: 'user-audio',
			title: '语音偏好',
			route: '/settings/user-audio',
			keywords: ['audio', 'voice', 'tts', 'stt', 'speech'],
			adminOnly: false,
			category: 'user'
		},
		{
			id: 'user-data',
			title: '数据控制',
			route: '/settings/user-data',
			keywords: ['data', 'chats', 'export', 'import', 'archive', 'delete'],
			adminOnly: false,
			category: 'user'
		},
		{
			id: 'user-about',
			title: '关于',
			route: '/settings/user-about',
			keywords: ['about', 'version', 'update'],
			adminOnly: false,
			category: 'user'
		},
		// ========== 管理员设置 (仅管理员可见) ==========
		{
			id: 'general',
			title: '通用设置',
			route: '/settings/general',
			keywords: [
				'general',
				'admin',
				'settings',
				'version',
				'update',
				'language',
				'theme',
				'data',
				'users',
				'roles',
				'ldap',
				'authentication',
				'reverse proxy',
				'webhook',
				'community',
				'channels'
			],
			adminOnly: true,
			category: 'admin'
		},
		{
			id: 'connections',
			title: '接口配置',
			route: '/settings/connections',
			keywords: [
				'connections',
				'ollama',
				'openai',
				'api',
				'base url',
				'direct connections',
				'proxy',
				'key'
			],
			adminOnly: true,
			category: 'admin'
		},
		{
			id: 'models',
			title: '模型列表',
			route: '/settings/models',
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
			],
			adminOnly: true,
			category: 'admin'
		},
		{
			id: 'evaluations',
			title: '竞技评估',
			route: '/settings/evaluations',
			keywords: ['evaluations', 'feedback', 'rating', 'arena', 'leaderboard', 'preference'],
			adminOnly: true,
			category: 'admin'
		},
		{
			id: 'tools',
			title: 'External Tools',
			route: '/settings/tools',
			keywords: ['tools', 'plugins', 'extensions', 'functions', 'openapi', 'server'],
			adminOnly: true,
			category: 'admin'
		},
		{
			id: 'documents',
			title: '文档处理',
			route: '/settings/documents',
			keywords: [
				'documents',
				'files',
				'rag',
				'knowledge',
				'upload',
				'embedding',
				'vector db',
				'chunk',
				'overlap',
				'splitter',
				'pdf',
				'ocr',
				'tika',
				'docling',
				'unstructured'
			],
			adminOnly: true,
			category: 'admin'
		},
		{
			id: 'web',
			title: 'Web Search',
			route: '/settings/web',
			keywords: [
				'web search',
				'google',
				'bing',
				'duckduckgo',
				'serp',
				'searxng',
				'moojeh',
				'yacy',
				'serper',
				'serply',
				'tavily',
				'exa',
				'perplexity',
				'firecrawl'
			],
			adminOnly: true,
			category: 'admin'
		},
		{
			id: 'code-execution',
			title: 'Code Execution',
			route: '/settings/code-execution',
			keywords: ['code execution', 'python', 'sandbox', 'compiler', 'jupyter', 'interpreter'],
			adminOnly: true,
			category: 'admin'
		},
		{
			id: 'interface',
			title: '界面设置',
			route: '/settings/interface',
			keywords: [
				'interface',
				'ui',
				'appearance',
				'banners',
				'tasks',
				'prompt suggestions',
				'title generation',
				'tags'
			],
			adminOnly: true,
			category: 'admin'
		},
		{
			id: 'audio',
			title: '语音设置',
			route: '/settings/audio',
			keywords: [
				'audio',
				'voice',
				'speech',
				'tts',
				'stt',
				'whisper',
				'deepgram',
				'azure',
				'openai',
				'elevenlabs'
			],
			adminOnly: true,
			category: 'admin'
		},
		{
			id: 'images',
			title: '图像设置',
			route: '/settings/images',
			keywords: [
				'images',
				'generation',
				'dalle',
				'stable diffusion',
				'comfyui',
				'automatic1111',
				'gemini'
			],
			adminOnly: true,
			category: 'admin'
		},
		{
			id: 'pipelines',
			title: '扩展管线',
			route: '/settings/pipelines',
			keywords: ['pipelines', 'workflows', 'filters', 'valves', 'middleware'],
			adminOnly: true,
			category: 'admin'
		},
		{
			id: 'db',
			title: '数据管理',
			route: '/settings/db',
			keywords: ['database', 'export', 'import', 'backup', 'chats', 'users'],
			adminOnly: true,
			category: 'admin'
		}
	];

	const setFilteredSettings = () => {
		filteredSettings = allSettings.filter((tab) => {
			// 1. 检查管理员权限
			if (tab.adminOnly && $user?.role !== 'admin') {
				return false;
			}

			// 2. 检查功能开关
			if (tab.featureFlag && !$config?.features?.[tab.featureFlag]) {
				return false;
			}

			// 3. 检查用户权限
			if (tab.permissionCheck && !tab.permissionCheck($user)) {
				return false;
			}

			// 4. 搜索过滤
			const searchTerm = search.toLowerCase().trim();
			return (
				search === '' ||
				tab.title.toLowerCase().includes(searchTerm) ||
				tab.keywords.some((keyword) => keyword.includes(searchTerm))
			);
		});
	};

	// 用户设置保存函数
	const saveUserSettings = async (updated: Record<string, any>) => {
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

	const handleResize = () => {
		updateSearchVisibility();
		setFilteredSettings();
	};

	const searchDebounceHandler = () => {
		if (searchDebounceTimeout) {
			clearTimeout(searchDebounceTimeout);
		}

		searchDebounceTimeout = setTimeout(() => {
			setFilteredSettings();
		}, 100);
	};

	onMount(() => {
		tabsContainer = document.getElementById('admin-settings-tabs-container');

		if (tabsContainer) {
			tabsContainer.addEventListener('wheel', tabsWheelHandler);
		}

		handleResize();
		window.addEventListener('resize', handleResize);
		// Scroll to the selected tab on mount
		scrollToTab(selectedTab);
	});

	onDestroy(() => {
		if (tabsContainer) {
			tabsContainer.removeEventListener('wheel', tabsWheelHandler);
		}

		if (typeof window !== 'undefined') {
			window.removeEventListener('resize', handleResize);
		}
	});
</script>

<div class="flex flex-col lg:flex-row w-full h-full pb-2 lg:space-x-4">
	<div
		id="admin-settings-tabs-container"
		class="tabs mx-[16px] lg:mx-0 lg:px-[16px] flex flex-row overflow-x-auto gap-2.5 max-w-full lg:gap-1 lg:flex-col lg:flex-none lg:w-50 dark:text-gray-200 text-sm font-medium text-left scrollbar-none"
	>
		<div
			class="hidden md:flex w-full rounded-full px-2.5 gap-2 bg-gray-100/80 dark:bg-gray-850/80 backdrop-blur-2xl my-1 -mx-1 mt-1.5"
			id="settings-search"
		>
			<div class="self-center rounded-l-xl bg-transparent">
				<Search className="size-3.5" strokeWidth="1.5" />
			</div>
			<label class="sr-only" for="search-input-settings-modal">{$i18n.t('Search')}</label>
			<input
				class="w-full py-1 text-sm bg-transparent dark:text-gray-300 outline-hidden"
				bind:value={search}
				id="search-input-settings-modal"
				on:input={searchDebounceHandler}
				placeholder={$i18n.t('Search')}
			/>
		</div>

		<!-- {$i18n.t('General')} -->
		<!-- {$i18n.t('Connections')} -->
		<!-- {$i18n.t('Models')} -->
		<!-- {$i18n.t('Evaluations')} -->
		<!-- {$i18n.t('External Tools')} -->
		<!-- {$i18n.t('Documents')} -->
		<!-- {$i18n.t('Web Search')} -->
		<!-- {$i18n.t('Code Execution')} -->
		<!-- {$i18n.t('Interface')} -->
		<!-- {$i18n.t('Audio')} -->
		<!-- {$i18n.t('Images')} -->
		<!-- {$i18n.t('Pipelines')} -->
		<!-- {$i18n.t('Database')} -->
		{#each filteredSettings as tab (tab.id)}
			<button
				id={tab.id}
				class="px-2 py-1.5 min-w-fit rounded-lg flex-1 lg:flex-none flex items-center text-right transition {selectedTab ===
				tab.id
					? 'bg-gray-100 dark:bg-gray-800 text-black dark:text-white font-medium'
					: 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-850 hover:text-gray-800 dark:hover:text-gray-200 font-normal'}"
				on:click={() => {
					goto(tab.route);
				}}
			>
				<div class="self-center mr-2 flex items-center justify-center size-8 rounded-lg bg-gray-200/90 dark:bg-gray-700 transition-all {selectedTab === tab.id ? 'bg-gray-300 dark:bg-gray-600 shadow-sm' : ''}"
				>
					{#if tab.id === 'general'}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-4"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 0 1 0 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 0 1 0-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281Z"
							/>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
							/>
						</svg>
					{:else if tab.id === 'connections'}
						<!-- 链接图标 - 更符合"接口配置"的含义 -->
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-4"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244"
							/>
						</svg>
					{:else if tab.id === 'models'}
						<!-- 立方体图标 - 更符合"模型"的含义 -->
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-4"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="m21 7.5-9-5.25L3 7.5m18 0-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9"
							/>
						</svg>
					{:else if tab.id === 'evaluations'}
						<!-- 奖牌图标 - 表达"竞技评估/排名" -->
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-4"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M9 12.75 11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 0 1-1.043 3.296 3.745 3.745 0 0 1-3.296 1.043A3.745 3.745 0 0 1 12 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 0 1-3.296-1.043 3.745 3.745 0 0 1-1.043-3.296A3.745 3.745 0 0 1 3 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 0 1 1.043-3.296 3.746 3.746 0 0 1 3.296-1.043A3.746 3.746 0 0 1 12 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 0 1 3.296 1.043 3.746 3.746 0 0 1 1.043 3.296A3.745 3.745 0 0 1 21 12Z"
							/>
						</svg>
					{:else if tab.id === 'tools'}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-4"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M21.75 6.75a4.5 4.5 0 0 1-4.884 4.484c-1.076-.091-2.264.071-2.95.904l-7.152 8.684a2.548 2.548 0 1 1-3.586-3.586l8.684-7.152c.833-.686.995-1.874.904-2.95a4.5 4.5 0 0 1 6.336-4.486l-3.276 3.276a3.004 3.004 0 0 0 2.25 2.25l3.276-3.276c.294.295.352.757.29 1.148Z"
							/>
						</svg>
					{:else if tab.id === 'documents'}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-4"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
							/>
						</svg>
					{:else if tab.id === 'web'}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-4"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M12 21a9.004 9.004 0 0 0 8.716-6.747M12 21a9.004 9.004 0 0 1-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 0 1 7.843 4.582M12 3a8.997 8.997 0 0 0-7.843 4.582m15.686 0A11.953 11.953 0 0 1 12 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0 1 21 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0 1 12 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 0 1 3 12c0-1.605.42-3.113 1.157-4.418"
							/>
						</svg>
					{:else if tab.id === 'code-execution'}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-4"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="m6.75 7.5 3 2.25-3 2.25m4.5 0h3"
							/>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M3 3h18a2.25 2.25 0 0 1 2.25 2.25v13.5A2.25 2.25 0 0 1 21 21H3a2.25 2.25 0 0 1-2.25-2.25V5.25A2.25 2.25 0 0 1 3 3Z"
							/>
						</svg>
					{:else if tab.id === 'interface'}
						<!-- 滑块调节器图标 - 更符合"界面设置"的含义 -->
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-4"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M10.5 6h9.75M10.5 6a1.5 1.5 0 1 1-3 0m3 0a1.5 1.5 0 1 0-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-9.75 0h9.75"
							/>
						</svg>
					{:else if tab.id === 'audio'}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-4"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M19.114 5.636a9 9 0 0 1 0 12.728M16.463 8.288a5.25 5.25 0 0 1 0 7.424M6.75 8.25l4.72-4.72a.75.75 0 0 1 1.28.53v15.88a.75.75 0 0 1-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 0 1 2.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75Z"
							/>
						</svg>
					{:else if tab.id === 'images'}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-4"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 0 0 1.5-1.5V6a1.5 1.5 0 0 0-1.5-1.5H3.75A1.5 1.5 0 0 0 2.25 6v12a1.5 1.5 0 0 0 1.5 1.5Zm10.5-11.25h.008v.008h-.008V8.25Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z"
							/>
						</svg>
					{:else if tab.id === 'pipelines'}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-4"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5"
							/>
						</svg>
					{:else if tab.id === 'db'}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-4"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125"
							/>
						</svg>
					<!-- ========== 用户设置图标 ========== -->
					{:else if tab.id === 'user-general'}
						<!-- 用户设置图标 -->
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 0 1 0 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 0 1 0-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281Z" />
							<path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
						</svg>
					{:else if tab.id === 'user-account'}
						<!-- 用户账户图标 -->
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="M17.982 18.725A7.488 7.488 0 0 0 12 15.75a7.488 7.488 0 0 0-5.982 2.975m11.963 0a9 9 0 1 0-11.963 0m11.963 0A8.966 8.966 0 0 1 12 21a8.966 8.966 0 0 1-5.982-2.275M15 9.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
						</svg>
					{:else if tab.id === 'user-connections'}
						<!-- 用户连接图标 -->
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244" />
						</svg>
					{:else if tab.id === 'user-tools'}
						<!-- 用户工具图标 -->
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="M21.75 6.75a4.5 4.5 0 0 1-4.884 4.484c-1.076-.091-2.264.071-2.95.904l-7.152 8.684a2.548 2.548 0 1 1-3.586-3.586l8.684-7.152c.833-.686.995-1.874.904-2.95a4.5 4.5 0 0 1 6.336-4.486l-3.276 3.276a3.004 3.004 0 0 0 2.25 2.25l3.276-3.276c.294.295.352.757.29 1.148Z" />
						</svg>
					{:else if tab.id === 'user-personalization'}
						<!-- 个性化图标 -->
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="M15.182 15.182a4.5 4.5 0 0 1-6.364 0M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM9.75 9.75c0 .414-.168.75-.375.75S9 10.164 9 9.75 9.168 9 9.375 9s.375.336.375.75Zm-.375 0h.008v.015h-.008V9.75Zm5.625 0c0 .414-.168.75-.375.75s-.375-.336-.375-.75.168-.75.375-.75.375.336.375.75Zm-.375 0h.008v.015h-.008V9.75Z" />
						</svg>
					{:else if tab.id === 'user-audio'}
						<!-- 用户语音图标 -->
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="M19.114 5.636a9 9 0 0 1 0 12.728M16.463 8.288a5.25 5.25 0 0 1 0 7.424M6.75 8.25l4.72-4.72a.75.75 0 0 1 1.28.53v15.88a.75.75 0 0 1-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 0 1 2.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75Z" />
						</svg>
					{:else if tab.id === 'user-data'}
						<!-- 数据控制图标 -->
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
						</svg>
					{:else if tab.id === 'user-about'}
						<!-- 关于图标 -->
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z" />
						</svg>
					{/if}
				</div>
				<div class=" self-center">{$i18n.t(tab.title)}</div>
			</button>
		{/each}
	</div>

	<div
		class="flex-1 mt-3 lg:mt-1 px-[16px] lg:pr-[16px] lg:pl-0 overflow-y-auto scrollbar-none"
	>
		{#if selectedTab === 'general'}
			<General
				saveHandler={async () => {
					toast.success($i18n.t('Settings saved successfully!'));

					await tick();
					await config.set(await getBackendConfig());
				}}
			/>
		{:else if selectedTab === 'connections'}
			<Connections
				on:save={() => {
					toast.success($i18n.t('Settings saved successfully!'));
				}}
			/>
		{:else if selectedTab === 'models'}
			<Models />
		{:else if selectedTab === 'evaluations'}
			<Evaluations />
		{:else if selectedTab === 'tools'}
			<Tools />
		{:else if selectedTab === 'documents'}
			<Documents
				on:save={async () => {
					toast.success($i18n.t('Settings saved successfully!'));

					await tick();
					await config.set(await getBackendConfig());
				}}
			/>
		{:else if selectedTab === 'web'}
			<WebSearch
				saveHandler={async () => {
					toast.success($i18n.t('Settings saved successfully!'));

					await tick();
					await config.set(await getBackendConfig());
				}}
			/>
		{:else if selectedTab === 'code-execution'}
			<CodeExecution
				saveHandler={async () => {
					toast.success($i18n.t('Settings saved successfully!'));

					await tick();
					await config.set(await getBackendConfig());
				}}
			/>
		{:else if selectedTab === 'interface'}
			<Interface
				on:save={() => {
					toast.success($i18n.t('Settings saved successfully!'));
				}}
			/>
		{:else if selectedTab === 'audio'}
			<Audio
				saveHandler={() => {
					toast.success($i18n.t('Settings saved successfully!'));
				}}
			/>
		{:else if selectedTab === 'images'}
			<Images
				on:save={() => {
					toast.success($i18n.t('Settings saved successfully!'));
				}}
			/>
		{:else if selectedTab === 'db'}
			<Database
				saveHandler={() => {
					toast.success($i18n.t('Settings saved successfully!'));
				}}
			/>
		{:else if selectedTab === 'pipelines'}
			<Pipelines
				saveHandler={() => {
					toast.success($i18n.t('Settings saved successfully!'));
				}}
			/>
		<!-- ========== 用户设置组件 ========== -->
		{:else if selectedTab === 'user-general'}
			<UserGeneral
				getModels={getModels}
				saveSettings={async (updated) => {
					await saveUserSettings(updated);
					toast.success($i18n.t('Settings saved successfully!'));
				}}
				on:save={() => {
					toast.success($i18n.t('Settings saved successfully!'));
				}}
			/>
		{:else if selectedTab === 'user-account'}
			<UserAccount
				saveSettings={saveUserSettings}
				saveHandler={() => {
					toast.success($i18n.t('Settings saved successfully!'));
				}}
			/>
		{:else if selectedTab === 'user-connections'}
			<UserConnections
				saveSettings={async (updated) => {
					await saveUserSettings(updated);
					toast.success($i18n.t('Settings saved successfully!'));
				}}
			/>
		{:else if selectedTab === 'user-tools'}
			<UserTools
				saveSettings={async (updated) => {
					await saveUserSettings(updated);
					toast.success($i18n.t('Settings saved successfully!'));
				}}
			/>
		{:else if selectedTab === 'user-personalization'}
			<UserPersonalization
				saveSettings={saveUserSettings}
				on:save={() => {
					toast.success($i18n.t('Settings saved successfully!'));
				}}
			/>
		{:else if selectedTab === 'user-audio'}
			<UserAudio
				saveSettings={saveUserSettings}
				on:save={() => {
					toast.success($i18n.t('Settings saved successfully!'));
				}}
			/>
		{:else if selectedTab === 'user-data'}
			<UserDataControls saveSettings={saveUserSettings} />
		{:else if selectedTab === 'user-about'}
			<UserAbout />
		{/if}
	</div>
</div>
