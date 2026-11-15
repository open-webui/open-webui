<script lang="ts">
	import { getContext, onDestroy } from 'svelte';
	import {
		searchFiles,
		type TerminalConnection,
		type TerminalFileSearchResult
	} from '$lib/apis/terminal';
	import { settings } from '$lib/stores';
	import { matchKeybinding, Shortcut } from '$lib/shortcuts';
	import Modal from '$lib/components/common/Modal.svelte';
	import KeyPill from '$lib/components/common/KeyPill.svelte';
	import Icon from '../FileNav/Icon.svelte';
	import { fileIconName } from '../FileNav/fileIcon';

	const i18n = getContext<any>('i18n');
	export let connection: TerminalConnection;
	export let chatId: string | null = null;
	export let onclose: () => void;
	export let onselect: (path: string) => void;

	let query = '';
	let results: TerminalFileSearchResult[] = [];
	let loading = false;
	let failed = false;
	let selectedIndex = 0;
	let timer: ReturnType<typeof setTimeout>;
	let requestVersion = 0;

	const queueSearch = (query: string, connection: TerminalConnection, chatId: string | null) => {
		clearTimeout(timer);
		const version = ++requestVersion;
		results = [];
		selectedIndex = 0;
		failed = false;
		loading = !!query.trim();
		if (!loading) return;
		timer = setTimeout(async () => {
			const path = query.trim().replace(/\\/g, '/');
			const slash = path.lastIndexOf('/');
			const response = await searchFiles(
				connection.baseUrl,
				connection.key,
				path.slice(slash + 1),
				slash < 0 ? '.' : path.slice(0, slash) || '/',
				50,
				'file',
				chatId ?? undefined,
				localStorage.getItem('fileNav:showHidden') === 'true'
			).catch(() => null);
			if (version !== requestVersion) return;
			results = (response?.results ?? []).filter((result) => result.type === 'file');
			failed = !response;
			loading = false;
		}, 200);
	};

	$: queueSearch(query, connection, chatId);
	onDestroy(() => {
		clearTimeout(timer);
		requestVersion++;
	});

	const selectResult = (result: TerminalFileSearchResult) => {
		onclose();
		onselect(result.path);
	};

	const handleKeydown = (event: KeyboardEvent) => {
		if (event.isComposing) return;
		if ($settings?.keyboardShortcuts !== false && matchKeybinding(event) === Shortcut.QUICK_OPEN) {
			event.preventDefault();
			event.stopPropagation();
			onclose();
		} else if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
			event.preventDefault();
			event.stopPropagation();
			selectedIndex = Math.max(
				0,
				Math.min(results.length - 1, selectedIndex + (event.key === 'ArrowDown' ? 1 : -1))
			);
			document
				.getElementById(`quick-open-result-${selectedIndex}`)
				?.scrollIntoView({ block: 'nearest' });
		} else if (event.key === 'Enter' && results[selectedIndex]) {
			event.preventDefault();
			event.stopPropagation();
			selectResult(results[selectedIndex]);
		}
	};
</script>

<Modal
	size="sm"
	ariaLabel={$i18n.t('settings.personal.shortcuts.quickOpen.label')}
	onRequestClose={onclose}
	className="bg-white dark:bg-gray-850 rounded-xl overflow-hidden !border-gray-100 dark:!border-gray-800 text-gray-700 dark:text-gray-100 font-normal"
>
	<div class="flex h-10 items-center gap-2 px-3">
		<span class="shrink-0 text-gray-500 dark:text-gray-400"><Icon name="search" size={14} /></span>
		<input
			bind:value={query}
			role="combobox"
			aria-label={$i18n.t('Search Files')}
			aria-autocomplete="list"
			aria-expanded={results.length > 0}
			aria-controls="quick-open-results"
			aria-activedescendant={results.length ? `quick-open-result-${selectedIndex}` : undefined}
			autocomplete="off"
			spellcheck="false"
			placeholder={$i18n.t('Search Files')}
			class="h-8 min-w-0 flex-1 bg-transparent text-[0.8125rem] font-normal outline-none placeholder:text-gray-400 dark:placeholder:text-gray-500"
			on:keydown={handleKeydown}
		/>
		<button type="button" aria-label={$i18n.t('Close')} on:click={onclose}>
			<KeyPill text="Esc" />
		</button>
	</div>
	<div
		id="quick-open-results"
		role="listbox"
		aria-label={$i18n.t('Search Files')}
		aria-busy={loading}
		class="max-h-[min(20rem,60dvh)] overflow-y-auto px-1 pb-1"
	>
		{#each results as result, index (result.path)}
			<button
				type="button"
				role="option"
				tabindex="-1"
				id="quick-open-result-{index}"
				aria-selected={index === selectedIndex}
				class="flex h-[1.6875rem] w-full items-center gap-2 rounded-lg px-2 text-start text-[0.8125rem] font-normal transition-colors duration-75 {index ===
				selectedIndex
					? 'bg-gray-100/60 dark:bg-gray-800/60'
					: 'hover:bg-gray-50/40 dark:hover:bg-gray-800/40'}"
				on:click={() => selectResult(result)}
			>
				<span class="shrink-0 text-gray-500 dark:text-gray-400"
					><Icon name={fileIconName(result.name)} size={14} /></span
				>
				<span class="min-w-0 flex-1 truncate">{result.name}</span>
				<span
					class="max-w-[55%] truncate text-[0.6875rem] text-gray-400 dark:text-gray-500"
					title={result.path}>{result.path}</span
				>
			</button>
		{/each}
	</div>
	{#if !results.length}
		<div role="status" class="px-3 pb-3 pt-1 text-[0.6875rem] text-gray-400 dark:text-gray-500">
			{#if loading}{$i18n.t('Searching...')}
			{:else if failed}{$i18n.t('Failed to search files')}
			{:else if query.trim()}{$i18n.t('No files found')}
			{:else}{$i18n.t('Type a file name or path to search.')}{/if}
		</div>
	{/if}
</Modal>
