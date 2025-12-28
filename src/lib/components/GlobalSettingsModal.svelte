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

	import { ADMIN_SETTINGS, USER_SETTINGS } from '$lib/constants/settings';
	import Search from '$lib/components/icons/Search.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';

	import type { Writable } from 'svelte/store';

	const i18n: Writable<any> = getContext('i18n');

	export let show = false;

	let search = '';
	let searchInput: HTMLInputElement;
	let selectedIndex = 0;

	// Admin Settings Data
	const adminSettings = ADMIN_SETTINGS;

	// User Settings Data
	const userSettings = USER_SETTINGS;

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

		// Filter Admin Settings
		if ($user?.role === 'admin') {
			const adminMatches = adminSettings.filter(item => 
				query === '' || 
				item.title.toLowerCase().includes(query) || 
				item.keywords.some(k => k.includes(query))
			);
			results = [...results, ...adminMatches];
		}

		// Filter User Settings
		const userMatches = userSettings.filter(item => {
			if (item.id === 'connections' && !$config?.features?.enable_direct_connections) return false;
			if (item.id === 'tools' && !($user?.role === 'admin' || $user?.permissions?.features?.direct_tool_servers)) return false;

			return query === '' ||
				   item.title.toLowerCase().includes(query) || 
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
			if (filteredResults.length > 0) {
				selectedIndex = (selectedIndex + 1) % filteredResults.length;
			}
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			if (filteredResults.length > 0) {
				selectedIndex = (selectedIndex - 1 + filteredResults.length) % filteredResults.length;
			}
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
