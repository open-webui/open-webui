<script>
	import { getContext, tick, onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	import { config } from '$lib/stores';
	import { getBackendConfig } from '$lib/apis';
	import Database from './Settings/Database.svelte';

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

	import { ADMIN_SETTINGS } from '$lib/constants/settings';	
    import Search from '../icons/Search.svelte';
	import XMark from '../icons/XMark.svelte';

	const i18n = getContext('i18n');

	let selectedTab = 'general';

	// Get current tab from URL pathname, default to 'general'
	$: {
		const pathParts = $page.url.pathname.split('/');
		const tabFromPath = pathParts[pathParts.length - 1];
		selectedTab = [
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
			'db'
		].includes(tabFromPath)
			? tabFromPath
			: 'general';
	}

	$: if (selectedTab) {
		// scroll to selectedTab
		scrollToTab(selectedTab);
	}

	const scrollToTab = (tabId) => {
		const tabElement = document.getElementById(tabId);
		if (tabElement) {
			tabElement.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'start' });
		}
	};

	let search = '';
	let searchDebounceTimeout;
	let filteredSettings = [];

	const allSettings = ADMIN_SETTINGS;

	const setFilteredSettings = () => {
		filteredSettings = allSettings.filter((tab) => {
			const searchTerm = search.toLowerCase().trim();
			return (
				search === '' ||
				tab.title.toLowerCase().includes(searchTerm) ||
				tab.keywords.some((keyword) => keyword.includes(searchTerm))
			);
		});
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
		const containerElement = document.getElementById('admin-settings-tabs-container');

		const onWheel = (event) => {
			if (event.deltaY !== 0 && containerElement) {
				// Adjust horizontal scroll position based on vertical scroll
				containerElement.scrollLeft += event.deltaY;
			}
		};

		if (containerElement) {
			containerElement.addEventListener('wheel', onWheel);
		}

		setFilteredSettings();
		// Scroll to the selected tab on mount
		scrollToTab(selectedTab);

		return () => {
			if (containerElement) {
				containerElement.removeEventListener('wheel', onWheel);
			}
		};
	});
</script>

<div class="flex flex-col lg:flex-row w-full h-full pb-2 lg:space-x-4">
	<div
		id="admin-settings-tabs-container"
		class="tabs mx-[16px] lg:mx-0 lg:px-[16px] flex flex-row overflow-x-auto gap-2.5 max-w-full lg:gap-1 lg:flex-col lg:flex-none lg:w-50 dark:text-gray-200 text-sm font-medium text-left scrollbar-none"
	>
		<div
			class="hidden md:flex w-full rounded-full px-2.5 gap-2 bg-gray-100/80 dark:bg-gray-850/80 backdrop-blur-2xl my-1 mb-1.5"
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

		{#each filteredSettings as tab (tab.id)}
			<button
				id={tab.id}
				class="px-0.5 py-1 min-w-fit rounded-lg flex-1 lg:flex-none flex text-right transition {selectedTab ===
				tab.id
					? ''
					: ' text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'}"
				on:click={() => {
					goto(tab.route);
				}}
			>
				<div class=" self-center mr-2">
					<svelte:component this={tab.icon} className="size-4" />
				</div>
				<div class=" self-center">{$i18n.t(tab.title)}</div>
			</button>
		{/each}
	</div>

	<div
		class="flex-1 mt-3 lg:mt-0 px-[16px] lg:pr-[16px] lg:pl-0 overflow-y-scroll scrollbar-hidden"
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
		{/if}
	</div>
</div>
