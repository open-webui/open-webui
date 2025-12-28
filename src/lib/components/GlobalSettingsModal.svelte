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

	const i18n = getContext('i18n');

	export let show = false;

	let search = '';
	let searchInput;
	let selectedIndex = 0;

	// Admin Settings Data
	const adminSettings = [
		{
			id: 'general',
			title: 'General',
			route: '/admin/settings/general',
			type: 'admin',
			icon: Cog6,
			keywords: ['general', 'admin', 'settings', 'version', 'update', 'language', 'theme', 'data', 'users', 'roles', 'ldap', 'auth']
		},
		{
			id: 'connections',
			title: 'Connections',
			route: '/admin/settings/connections',
			type: 'admin',
			icon: Cloud,
			keywords: ['connections', 'ollama', 'openai', 'api', 'base url', 'proxy', 'key']
		},
		{
			id: 'models',
			title: 'Models',
			route: '/admin/settings/models',
			type: 'admin',
			icon: Sparkles,
			keywords: ['models', 'pull', 'delete', 'create', 'edit', 'modelfile', 'gguf', 'import', 'export']
		},
		{
			id: 'evaluations',
			title: 'Evaluations',
			route: '/admin/settings/evaluations',
			type: 'admin',
			icon: DocumentChartBar,
			keywords: ['evaluations', 'feedback', 'rating', 'arena', 'leaderboard']
		},
		{
			id: 'tools',
			title: 'External Tools',
			route: '/admin/settings/tools',
			type: 'admin',
			icon: Wrench,
			keywords: ['tools', 'plugins', 'extensions', 'functions', 'openapi']
		},
		{
			id: 'documents',
			title: 'Documents',
			route: '/admin/settings/documents',
			type: 'admin',
			icon: BookOpen,
			keywords: ['documents', 'files', 'rag', 'knowledge', 'embedding', 'vector', 'pdf', 'ocr']
		},
		{
			id: 'web',
			title: 'Web Search',
			route: '/admin/settings/web',
			type: 'admin',
			icon: GlobeAlt,
			keywords: ['web search', 'google', 'bing', 'duckduckgo', 'serp', 'searxng']
		},
		{
			id: 'code-execution',
			title: 'Code Execution',
			route: '/admin/settings/code-execution',
			type: 'admin',
			icon: CommandLine,
			keywords: ['code execution', 'python', 'sandbox', 'jupyter']
		},
		{
			id: 'interface',
			title: 'Interface',
			route: '/admin/settings/interface',
			type: 'admin',
			icon: ChatBubbleOval,
			keywords: ['interface', 'ui', 'appearance', 'banners', 'tasks']
		},
		{
			id: 'audio',
			title: 'Audio',
			route: '/admin/settings/audio',
			type: 'admin',
			icon: Headphone,
			keywords: ['audio', 'voice', 'speech', 'tts', 'stt', 'whisper']
		},
		{
			id: 'images',
			title: 'Images',
			route: '/admin/settings/images',
			type: 'admin',
			icon: Photo,
			keywords: ['images', 'generation', 'dalle', 'stable diffusion', 'comfyui']
		},
		{
			id: 'pipelines',
			title: 'Pipelines',
			route: '/admin/settings/pipelines',
			type: 'admin',
			icon: AdjustmentsHorizontal,
			keywords: ['pipelines', 'workflows', 'filters', 'valves']
		},
		{
			id: 'db',
			title: 'Database',
			route: '/admin/settings/db',
			type: 'admin',
			icon: Database,
			keywords: ['database', 'export', 'import', 'backup', 'chats']
		}
	];

	// User Settings Data
	const userSettings = [
		{
			id: 'general',
			title: 'General',
			type: 'user',
			icon: SettingsAlt,
			keywords: ['general', 'settings', 'language', 'theme', 'notifications', 'system']
		},
		{
			id: 'interface',
			title: 'Interface',
			type: 'user',
			icon: AppNotification,
			keywords: ['interface', 'ui', 'appearance', 'chat', 'model', 'haptic', 'response']
		},
		{
			id: 'connections',
			title: 'Connections',
			type: 'user',
			icon: Link,
			keywords: ['connections', 'api', 'manage']
		},
		{
			id: 'tools',
			title: 'External Tools',
			type: 'user',
			icon: WrenchAlt,
			keywords: ['tools', 'manage']
		},
		{
			id: 'personalization',
			title: 'Personalization',
			type: 'user',
			icon: Face,
			keywords: ['personalization', 'memory', 'profile', 'custom']
		},
		{
			id: 'audio',
			title: 'Audio',
			type: 'user',
			icon: SoundHigh,
			keywords: ['audio', 'voice', 'speech', 'tts', 'stt']
		},
		{
			id: 'data_controls',
			title: 'Data Controls',
			type: 'user',
			icon: DatabaseSettings,
			keywords: ['data', 'history', 'chats', 'export', 'delete', 'archive']
		},
		{
			id: 'account',
			title: 'Account',
			type: 'user',
			icon: UserCircle,
			keywords: ['account', 'profile', 'password', 'security', 'api key']
		},
		{
			id: 'about',
			title: 'About',
			type: 'user',
			icon: InfoCircle,
			keywords: ['about', 'version', 'update', 'info']
		}
	];

	let filteredResults = [];

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
		let results = [];

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

	const handleSelect = async (item) => {
		show = false;
		if (item.type === 'admin') {
			goto(item.route);
		} else {
			activeSettingsTab.set(item.id);
			showSettings.set(true);
		}
	};

	const handleKeydown = (e) => {
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

<Modal size="lg" bind:show>
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
