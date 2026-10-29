<script lang="ts">
	import { getContext, onDestroy, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { folders, settings, tags } from '$lib/stores';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import DropdownSub from '$lib/components/common/DropdownSub.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Loader from '$lib/components/common/Loader.svelte';
	import {
		searchWorkspace,
		type SearchResult,
		type SearchScope,
		type SearchKind
	} from '$lib/apis/search';
	import Modal from '$lib/components/common/Modal.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import ChatBubble from '$lib/components/icons/ChatBubble.svelte';
	import Hashtag from '$lib/components/icons/Hashtag.svelte';
	import Document from '$lib/components/icons/Document.svelte';
	import Adjustments from '$lib/components/icons/AdjustmentsHorizontal.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Eye from '$lib/components/icons/Eye.svelte';
	import ArrowLeft from '$lib/components/icons/ArrowLeft.svelte';
	import Pin from '$lib/components/icons/Pin.svelte';
	import HighlightedText from './Search/HighlightedText.svelte';
	import ChatPreview from './Sidebar/ChatPreview.svelte';
	import NotePreview from './Search/NotePreview.svelte';
	import PreviewMarkdown from './Search/PreviewMarkdown.svelte';

	const i18n: any = getContext('i18n');
	// Preserve translations from the former chat search and preview during extraction.
	// $i18n.t('Failed to load chat'); $i18n.t('Select a conversation to preview');
	export let show = false;
	export let onClose = () => {};
	let query = '';
	let kind: 'all' | SearchKind = 'all';
	let sharing = 'all';
	let scope = '';
	let kinds: SearchKind[] = ['chat'];
	let scopes: SearchScope[] = [];
	let results: SearchResult[] = [];
	let selectedIndex = 0;
	let loading = false;
	let error = '';
	let page = 1;
	let hasMore = false;
	let preview = false;
	let panel: 'filters' | 'actions' | 'types' | null = null;
	let input: HTMLInputElement;
	let list: HTMLDivElement;
	let request: AbortController | undefined;
	let timer: ReturnType<typeof setTimeout>;
	let generation = 0;
	let suggesting = false;
	let suggestionIndex = -1;
	const icons = { chat: ChatBubble, message: Hashtag, note: Document };
	const labels = { chat: 'Chats', message: 'Messages', note: 'Notes' };
	const locations = [
		{ kind: 'folder', label: 'Folders', type: 'chat' },
		{ kind: 'channel', label: 'Channels', type: 'message' }
	];
	const filterDescriptions: Record<string, string> = {
		tag: 'search for tags',
		folder: 'search for folders',
		pinned: 'search for pinned chats',
		shared: 'search for shared chats',
		archived: 'search for archived chats'
	};
	// Fixed labels from the search API; folder and channel names stay as typed.
	$: contextLabels = new Map([
		['Personal chat', $i18n.t('Personal chat')],
		['Shared chat', $i18n.t('Shared chat')],
		['Shared snapshot', $i18n.t('Shared snapshot')],
		['Personal note', $i18n.t('Personal note')],
		['Shared note', $i18n.t('Shared note')]
	]);
	$: selected = results[selectedIndex];
	$: suggestions = suggesting && !panel ? getSuggestions(query, $tags, $folders) : [];
	$: scopeName = scopes.find((item) => item.id === scope)?.name ?? '';
	$: canCreateNote = kinds.includes('note');
	$: selectionClass = $settings?.highContrastMode
		? 'bg-gray-200 dark:bg-gray-800'
		: 'bg-gray-50/70 dark:bg-gray-800/60';
	const quietButton =
		'focus-ring flex h-[1.6875rem] shrink-0 items-center justify-center gap-1 rounded-lg px-1.5 text-[0.6875rem] font-normal text-gray-500 hover:bg-gray-50/60 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800/60 dark:hover:text-gray-200';
	$: if (show && typeof window !== 'undefined') {
		preview =
			window.matchMedia('(min-width: 1024px)').matches &&
			localStorage.getItem('searchPreview') !== 'false';
	}
	$: schedule(show, query, kind, sharing, scope);

	function setPreview(value: boolean) {
		preview = value;
		localStorage.setItem('searchPreview', String(value));
	}

	function schedule(visible: boolean, q: string, type: string, share: string, location: string) {
		clearTimeout(timer);
		request?.abort();
		generation += 1;
		if (!visible) return;
		loading = true;
		error = '';
		results = [];
		selectedIndex = 0;
		hasMore = false;
		page = 1;
		timer = setTimeout(() => fetchResults(1), q.trim() ? 180 : 0);
	}

	async function fetchResults(nextPage: number) {
		request?.abort();
		const controller = new AbortController();
		request = controller;
		const version = ++generation;
		loading = true;
		error = '';
		try {
			const response = await searchWorkspace(
				localStorage.token,
				{ q: query, kind, sharing, scope, page: nextPage },
				controller.signal
			);
			if (version !== generation || !show) return;
			const existingIds = new Set(results.map((item) => item.id));
			results =
				nextPage === 1
					? response.items
					: [...results, ...response.items.filter((item) => !existingIds.has(item.id))];
			scopes = response.scopes;
			kinds = response.kinds;
			hasMore = response.has_more;
			page = nextPage;
		} catch (cause) {
			if (version === generation && !controller.signal.aborted)
				error = $i18n.t('Search is unavailable. Please try again.');
		} finally {
			if (version === generation) loading = false;
		}
	}

	function getSuggestions(
		text: string,
		tagList: { id: string; name: string }[],
		folderList: { name: string }[]
	) {
		const word = text.split(' ').at(-1)?.toLowerCase() ?? '';
		const [name, value] = word.split(':');
		if (value === undefined) {
			return word
				? Object.keys(filterDescriptions)
						.filter((key) => key.startsWith(word))
						.map((key) => ({
							value: `${key}:`,
							label: `${key}:`,
							description: $i18n.t(filterDescriptions[key])
						}))
				: [];
		}
		const items =
			name === 'tag'
				? [...tagList, { id: 'none', name: $i18n.t('Untagged') }]
				: name === 'folder'
					? folderList.map((folder) => ({
							id: folder.name.replaceAll(' ', '_').toLowerCase(),
							name: folder.name
						}))
					: name in filterDescriptions
						? [
								{ id: 'true', name: 'true' },
								{ id: 'false', name: 'false' }
							]
						: [];
		return items
			.filter((item) => item.id.startsWith(value) && item.id !== value)
			.map((item) => ({
				value: `${name}:${item.id} `,
				label: item.name,
				description: item.id === item.name ? '' : item.id
			}));
	}

	function applySuggestion(suggestion: { value: string }) {
		query = query.slice(0, query.lastIndexOf(' ') + 1) + suggestion.value;
		suggestionIndex = 0;
		input.focus();
	}

	function close() {
		show = false;
		suggesting = false;
		panel = null;
		preview = false;
		onClose();
	}

	async function open(result = selected) {
		if (!result) return;
		await goto(result.url);
		close();
	}

	async function select(index: number) {
		selectedIndex = Math.max(0, Math.min(results.length - 1, index));
		await tick();
		list?.querySelector(`[data-index="${selectedIndex}"]`)?.scrollIntoView({ block: 'nearest' });
	}

	function keydown(event: KeyboardEvent) {
		if (!show || event.isComposing) return;
		if (event.target === input && suggestions.length) {
			if (event.key === 'Escape') {
				event.stopPropagation();
				suggesting = false;
				return;
			}
			if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
				event.preventDefault();
				suggestionIndex = Math.max(
					0,
					Math.min(suggestions.length - 1, suggestionIndex + (event.key === 'ArrowDown' ? 1 : -1))
				);
				return;
			}
			if (event.key === 'Tab' || (event.key === 'Enter' && suggestions[suggestionIndex])) {
				event.preventDefault();
				applySuggestion(suggestions[Math.max(0, suggestionIndex)]);
				return;
			}
		}
		if (event.key === 'Escape') return;
		if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
			event.preventDefault();
			event.stopPropagation();
			panel = panel === 'actions' ? null : 'actions';
			return;
		}
		if (panel || (event.target !== input && event.target !== list)) return;
		if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
			event.preventDefault();
			select(selectedIndex + (event.key === 'ArrowDown' ? 1 : -1));
		} else if (event.key === 'Enter' && selected) {
			event.preventDefault();
			if (event.metaKey || event.ctrlKey) setPreview(!preview);
			else open();
		}
	}

	function formatSearchDate(seconds: number) {
		if (!Number.isFinite(seconds) || seconds <= 0) return '';
		const date = new Date(seconds * 1000);
		return Number.isFinite(date.getTime())
			? date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
			: '';
	}

	async function copyLink() {
		if (!selected) return;
		try {
			await navigator.clipboard.writeText(new URL(selected.url, location.origin).href);
			toast.success($i18n.t('Link copied to clipboard'));
			panel = null;
		} catch {
			toast.error($i18n.t('Unable to copy link'));
		}
	}

	async function create(type: 'chat' | 'note') {
		await goto(
			type === 'chat'
				? `/?q=${encodeURIComponent(query)}`
				: `/notes/new?content=${encodeURIComponent(query)}`
		);
		close();
	}

	function resetFilters() {
		kind = 'all';
		sharing = 'all';
		scope = '';
		panel = null;
		input?.focus();
	}
	onDestroy(() => {
		clearTimeout(timer);
		request?.abort();
		generation += 1;
	});
</script>

<svelte:window
	on:click={(event) => {
		if (panel && event.target instanceof Element && !event.target.closest('[data-search-panel]'))
			panel = null;
	}}
/>

<Modal
	bind:show
	size={preview ? 'xl' : 'lg'}
	ariaLabel={$i18n.t('Search workspace')}
	onRequestClose={close}
	className="bg-white dark:bg-gray-850 rounded-2xl !border-gray-100 dark:!border-gray-800"
>
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		class="relative flex max-h-[85dvh] flex-col font-normal text-[0.8125rem] text-gray-700 dark:text-gray-100"
		on:keydown={keydown}
	>
		<div class="flex h-11 shrink-0 items-center gap-2 px-3">
			<Search className="size-3.5 shrink-0 text-gray-500 dark:text-gray-400" strokeWidth="2" />
			<input
				bind:this={input}
				bind:value={query}
				class="h-8 min-w-0 flex-1 bg-transparent text-[0.8125rem] font-normal outline-hidden placeholder:text-gray-400 dark:placeholder:text-gray-500"
				placeholder={$i18n.t('Search workspace…')}
				aria-label={$i18n.t('Search your workspace')}
				role="combobox"
				aria-autocomplete="list"
				aria-expanded={suggestions.length > 0 || results.length > 0}
				aria-controls={suggestions.length
					? 'workspace-search-suggestions'
					: 'workspace-search-results'}
				aria-activedescendant={suggestions.length
					? suggestions[suggestionIndex]
						? `search-suggestion-${suggestionIndex}`
						: undefined
					: selected
						? `search-result-${selectedIndex}`
						: undefined}
				autocomplete="off"
				spellcheck="false"
				maxlength="500"
				on:input={(event) => {
					suggesting = true;
					suggestionIndex = event.currentTarget.value.split(' ').at(-1)?.includes(':') ? 0 : -1;
				}}
				on:blur={() => (suggesting = false)}
			/>
			{#if query}<button
					class={quietButton}
					aria-label={$i18n.t('Clear search')}
					on:click={() => {
						query = '';
						input.focus();
					}}><XMark className="size-3" /></button
				>{/if}
			<button
				class={quietButton}
				aria-label={`${$i18n.t('Content type')}: ${$i18n.t(kind === 'all' ? 'Everything' : labels[kind])}`}
				data-search-panel
				aria-expanded={panel === 'types'}
				on:click={() => (panel = panel === 'types' ? null : 'types')}
				>{$i18n.t(kind === 'all' ? 'Everything' : labels[kind])}<ChevronDown
					className="size-2.5"
				/></button
			>
			<button
				class={quietButton}
				aria-label={$i18n.t('Filters')}
				data-search-panel
				aria-expanded={panel === 'filters'}
				on:click={() => (panel = panel === 'filters' ? null : 'filters')}
				><Adjustments className="size-3.5" /></button
			>
			<button class={quietButton} aria-label={$i18n.t('Close search')} on:click={close}
				><XMark className="size-3.5" /></button
			>
		</div>
		{#if sharing !== 'all' || scope}
			<div class="flex flex-wrap items-center gap-1 px-3 pb-1.5">
				{#if sharing !== 'all'}<button
						class="{quietButton} !h-[1.375rem] bg-gray-50/60 dark:bg-gray-800/40"
						on:click={() => (sharing = 'all')}
						aria-label={$i18n.t('Remove sharing filter')}
						>{$i18n.t(sharing === 'mine' ? 'Created by you' : 'Shared with you')}<XMark
							className="size-2.5"
						/></button
					>{/if}
				{#if scope}<button
						class="{quietButton} !h-[1.375rem] max-w-48 bg-gray-50/60 dark:bg-gray-800/40"
						on:click={() => (scope = '')}
						aria-label={$i18n.t('Remove location filter')}
						><span class="truncate">{scopeName}</span><XMark
							className="size-2.5 shrink-0"
						/></button
					>{/if}
			</div>
		{/if}
		{#if suggestions.length}
			<div
				id="workspace-search-suggestions"
				class="absolute left-6 top-10 z-10 w-64 max-w-[calc(100%-2rem)]"
				role="listbox"
				aria-label={$i18n.t('Search options')}
			>
				<DropdownMenu className="max-h-64 overflow-y-auto scrollbar-hover font-normal"
					>{#each suggestions as suggestion, index}<button
							id="search-suggestion-{index}"
							role="option"
							aria-selected={suggestionIndex === index}
							tabindex="-1"
							class={suggestionIndex === index ? selectionClass : ''}
							on:mousedown={(e) => e.preventDefault()}
							on:mouseenter={() => (suggestionIndex = index)}
							on:click={() => applySuggestion(suggestion)}
							><span class="min-w-0 truncate">{suggestion.label}</span
							>{#if suggestion.description}<span
									class="ml-auto truncate text-[0.6875rem] text-gray-500 dark:text-gray-400"
									>{suggestion.description}</span
								>{/if}</button
						>{/each}</DropdownMenu
				>
			</div>
		{/if}
		{#if panel === 'types'}
			<div class="absolute top-10 right-12 z-10" data-search-panel>
				<DropdownMenu className="min-w-32 font-normal"
					><button
						on:click={() => {
							kind = 'all';
							panel = null;
							input.focus();
						}}>{$i18n.t('Everything')}</button
					>{#each kinds as type}<button
							on:click={() => {
								kind = type;
								if (
									!locations.some(
										(group) => group.type === type && scope.startsWith(`${group.kind}:`)
									)
								)
									scope = '';
								panel = null;
								input.focus();
							}}
							><svelte:component this={icons[type]} className="size-3.5" />{$i18n.t(
								labels[type]
							)}</button
						>{/each}</DropdownMenu
				>
			</div>
		{/if}
		{#if panel === 'filters'}
			<div class="absolute right-2 top-10 z-10 w-52 max-w-[calc(100%-1rem)]" data-search-panel>
				<DropdownMenu>
					<DropdownSub maxWidth={208} contentClass="w-52 font-normal">
						<button
							slot="trigger"
							class="focus-ring flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[0.8125rem] font-normal"
						>
							<span>{$i18n.t('View')}</span>
							<span class="ml-auto truncate text-gray-500 dark:text-gray-400"
								>{$i18n.t(
									sharing === 'all'
										? 'All'
										: sharing === 'mine'
											? 'Created by you'
											: 'Shared with you'
								)}</span
							>
							<ChevronRight className="size-3.5 shrink-0 text-gray-400" />
						</button>
						{#each [{ value: 'all', label: 'All' }, { value: 'mine', label: 'Created by you' }, { value: 'shared', label: 'Shared with you' }] as option}
							<button
								data-search-panel
								aria-pressed={sharing === option.value}
								on:click={() => {
									sharing = option.value;
									panel = null;
									input.focus();
								}}
							>
								{$i18n.t(option.label)}
								{#if sharing === option.value}<Check className="ml-auto size-3.5" />{/if}
							</button>
						{/each}
					</DropdownSub>
					<DropdownSub
						maxWidth={208}
						contentClass="w-52 max-h-64 overflow-y-auto scrollbar-hover font-normal"
					>
						<button
							slot="trigger"
							class="focus-ring flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[0.8125rem] font-normal"
						>
							<span>{$i18n.t('Location')}</span>
							<span class="ml-auto truncate text-gray-500 dark:text-gray-400"
								>{scopeName || $i18n.t('Everywhere')}</span
							>
							<ChevronRight className="size-3.5 shrink-0 text-gray-400" />
						</button>
						<button
							data-search-panel
							aria-pressed={!scope}
							on:click={() => {
								scope = '';
								panel = null;
								input.focus();
							}}
						>
							{$i18n.t('Everywhere')}{#if !scope}<Check className="ml-auto size-3.5" />{/if}
						</button>
						{#each locations as group}
							{#if (kind === 'all' || kind === group.type) && scopes.some((item) => item.kind === group.kind)}
								<div
									data-search-panel
									class="px-2 pb-1 pt-2 text-[0.6875rem] text-gray-500 dark:text-gray-400"
								>
									{$i18n.t(group.label)}
								</div>
								{#each scopes.filter((item) => item.kind === group.kind) as item}
									<button
										data-search-panel
										aria-pressed={scope === item.id}
										on:click={() => {
											scope = item.id;
											panel = null;
											input.focus();
										}}
									>
										<span class="min-w-0 truncate">{item.name}</span>{#if scope === item.id}<Check
												className="ml-auto size-3.5 shrink-0"
											/>{/if}
									</button>
								{/each}
							{/if}
						{/each}
					</DropdownSub>
					{#if kind !== 'all' || sharing !== 'all' || scope}
						<hr class="border-gray-100 dark:border-gray-800" />
						<button on:click={resetFilters}>{$i18n.t('Reset')}</button>
					{/if}
				</DropdownMenu>
			</div>
		{/if}
		<div
			class="flex h-[min(36rem,70dvh)] min-h-40 border-t border-gray-100/60 dark:border-gray-800/40"
			aria-busy={loading}
		>
			<div
				class="min-w-0 flex-1 flex-col overflow-y-auto p-1 scrollbar-hidden {preview && selected
					? 'hidden sm:flex'
					: 'flex'}"
			>
				<div
					class="flex h-6 shrink-0 items-center justify-between px-2 text-[0.6875rem] text-gray-500 dark:text-gray-400"
				>
					<span id="workspace-search-results-label"
						>{query.trim() ? $i18n.t('Results') : $i18n.t('Pinned & recent')}</span
					><span aria-live="polite"
						>{loading
							? $i18n.t('Searching…')
							: results.length
								? `${results.length}${hasMore ? '+' : ''}`
								: ''}</span
					>
				</div>
				<div
					bind:this={list}
					id="workspace-search-results"
					role="listbox"
					aria-labelledby="workspace-search-results-label"
					tabindex="-1"
					class="outline-hidden"
				>
					{#each results as result, index (result.id)}
						<!-- svelte-ignore a11y-click-events-have-key-events -->
						<div
							id="search-result-{index}"
							role="option"
							aria-selected={selectedIndex === index}
							tabindex="-1"
							data-index={index}
							class="flex min-h-8 cursor-pointer items-center gap-2 rounded-xl px-2 py-1 text-left font-normal transition-colors duration-75 {selectedIndex ===
							index
								? selectionClass
								: 'hover:bg-gray-50/40 dark:hover:bg-gray-800/40'}"
							on:mouseenter={() => (selectedIndex = index)}
							on:click={() => {
								selectedIndex = index;
								if (preview) input?.focus();
								else open(result);
							}}
							on:dblclick={() => open(result)}
						>
							<svelte:component
								this={icons[result.kind]}
								className="size-3.5 shrink-0 text-gray-500 dark:text-gray-400"
							/>
							<div class="min-w-0 flex-1">
								<div class="flex items-center gap-2 leading-5">
									<span class="min-w-0 flex-1 truncate"
										><HighlightedText text={result.title} {query} /></span
									><span
										class="hidden max-w-[35%] truncate text-[0.6875rem] text-gray-500 dark:text-gray-400 sm:block"
										>{contextLabels.get(result.context) ?? result.context}</span
									>{#if result.pinned}<Pin className="size-2.5 shrink-0 text-gray-400" />{/if}
								</div>
								{#if query.trim() && result.snippet}<div
										class="truncate text-xs leading-4 text-gray-500 dark:text-gray-400"
									>
										<HighlightedText text={result.snippet} {query} />
									</div>{/if}
							</div>
						</div>
					{/each}
				</div>
				{#if loading && !results.length}<div
						class="flex flex-1 items-center justify-center text-gray-400"
						aria-label={$i18n.t('Searching')}
					>
						<Spinner className="size-4" />
					</div>{/if}
				{#if error}<div
						class="m-auto px-5 py-6 text-center text-xs text-gray-500 dark:text-gray-400"
						role="alert"
					>
						<p>{error}</p>
						<button
							class="mt-2 underline underline-offset-2"
							on:click={() => fetchResults(results.length ? page + 1 : 1)}
							>{$i18n.t('Try again')}</button
						>
					</div>
				{:else if !loading && !results.length}<div
						class="m-auto px-5 py-6 text-center text-xs text-gray-500 dark:text-gray-400"
					>
						<p>{query ? $i18n.t('No matches found') : $i18n.t('Nothing here yet')}</p>
						<p class="mt-1 text-[0.6875rem]">
							{$i18n.t('Try another word or broaden your filters.')}
						</p>
						{#if kind !== 'all' || sharing !== 'all' || scope}<button
								class="mt-2 underline underline-offset-2"
								on:click={resetFilters}>{$i18n.t('Clear filters')}</button
							>{/if}
					</div>{/if}
				{#if hasMore && !error}
					<Loader
						on:visible={() => {
							if (!loading) fetchResults(page + 1);
						}}
					>
						<div
							class="flex h-7 items-center justify-center text-gray-400"
							role="status"
							aria-label={$i18n.t('Loading more results')}
						>
							<Spinner className="size-3" />
						</div>
					</Loader>
				{/if}
			</div>
			{#if preview && selected}
				<section
					class="flex w-full min-w-0 flex-col border-gray-100/60 sm:w-[45%] sm:border-l dark:border-gray-800/40"
					aria-label={$i18n.t('Result preview')}
				>
					<div
						class="flex h-8 shrink-0 items-center justify-between px-2 text-[0.6875rem] text-gray-500 dark:text-gray-400"
					>
						<button
							class={quietButton}
							on:click={() => {
								preview = false;
								input.focus();
							}}><ArrowLeft className="size-3" /><span>{$i18n.t('Back')}</span></button
						><span>{$i18n.t(labels[selected.kind])}</span>
					</div>
					{#if selected.kind === 'chat'}
						<div class="truncate px-3 pb-1 text-[0.8125rem] font-normal">{selected.title}</div>
						<div class="min-h-0 flex-1">
							<ChatPreview
								chatId={selected.id.startsWith('chat:') ? selected.id.slice(5) : ''}
								shareId={selected.id.startsWith('shared:') ? selected.id.slice(7) : ''}
								messageId={new URL(selected.url, 'http://localhost').searchParams.get('message') ??
									''}
							/>
						</div>
					{:else}
						<div class="min-h-0 flex-1 overflow-y-auto px-3 pb-3 scrollbar-hidden">
							<h2 class="text-[0.8125rem] font-normal leading-5 break-words">{selected.title}</h2>
							<div class="mt-1 text-[0.6875rem] text-gray-500 dark:text-gray-400">
								{contextLabels.get(selected.context) ?? selected.context} · {formatSearchDate(
									selected.updated_at
								)}
							</div>
							<div class="mt-3 break-words text-xs leading-snug text-gray-600 dark:text-gray-300">
								{#if selected.kind === 'note'}
									<NotePreview id={selected.id.slice(5)} {query} />
								{:else}
									<PreviewMarkdown
										id={`message-preview-${selected.id}`}
										content={selected.preview}
									/>
								{/if}
							</div>
						</div>
					{/if}
				</section>
			{/if}
		</div>
		{#if panel === 'actions'}<div class="absolute bottom-9 right-1 z-10" data-search-panel>
				<DropdownMenu className="min-w-56 font-normal"
					>{#if selected}<button
							on:click={() => {
								panel = null;
								open();
							}}
							>{$i18n.t('Open result')}<span class="ml-auto text-xs text-gray-400">↵</span></button
						><button
							on:click={() => {
								setPreview(!preview);
								panel = null;
								input.focus();
							}}>{preview ? $i18n.t('Hide preview') : $i18n.t('Show preview')}</button
						><button on:click={copyLink}>{$i18n.t('Copy link')}</button>
						<hr class="border-gray-100 dark:border-gray-800" />{/if}<button
						on:click={() => create('chat')}>{$i18n.t('Start a new conversation')}</button
					>{#if canCreateNote}<button on:click={() => create('note')}
							>{$i18n.t('Create a new note')}</button
						>{/if}</DropdownMenu
				>
			</div>{/if}
		<div
			class="flex h-8 shrink-0 items-center justify-between gap-2 border-t border-gray-100/60 px-2 dark:border-gray-800/40"
		>
			<span class="min-w-0 truncate pl-1 text-[0.6875rem] text-gray-500 dark:text-gray-400"
				>{selected
					? (contextLabels.get(selected.context) ?? selected.context)
					: $i18n.t('Workspace search')}</span
			>
			<div class="flex shrink-0 items-center gap-0.5">
				<button class={quietButton} disabled={!selected} on:click={() => open()}
					>{$i18n.t('Open')}<span class="text-gray-400">↵</span></button
				><button
					class={quietButton}
					disabled={!selected}
					on:click={() => setPreview(!preview)}
					aria-pressed={preview}
					title={$i18n.t('Preview (Ctrl/Cmd + Enter)')}
					><Eye className="size-3" /><span class="hidden sm:inline">{$i18n.t('Preview')}</span
					></button
				><button
					class={quietButton}
					data-search-panel
					aria-expanded={panel === 'actions'}
					on:click={() => (panel = panel === 'actions' ? null : 'actions')}
					>{$i18n.t('Actions')}<span class="text-[0.625rem] text-gray-400">⌘K</span></button
				>
			</div>
		</div>
	</div>
</Modal>
