<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onDestroy, onMount, tick } from 'svelte';
	import { goto } from '$app/navigation';

	import Modal from '$lib/components/common/Modal.svelte';
	import SearchInput from './Sidebar/SearchInput.svelte';
	import {
		getChatById,
		getChatCount,
		searchChats,
		type ChatSearchHit,
		type ChatSearchFacets,
		type ChatSearchResponse
	} from '$lib/apis/chats';
	import Spinner from '../common/Spinner.svelte';
	import { searchHistoryAdd, sanitizeMarkSnippet } from '$lib/utils';

	import dayjs from '$lib/dayjs';
	import calendar from 'dayjs/plugin/calendar';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(calendar);
	dayjs.extend(relativeTime);

	import { createMessagesList } from '$lib/utils';
	import { chats as chatsStore, config, user } from '$lib/stores';
	import Messages from '../chat/Messages.svelte';
	import PencilSquare from '../icons/PencilSquare.svelte';
	import PageEdit from '../icons/PageEdit.svelte';
	import FilterChips from './SearchModal/FilterChips.svelte';
	import ResultRow from './SearchModal/ResultRow.svelte';
	import RecentSearches from './SearchModal/RecentSearches.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let onClose = () => {};

	// ── Inputs ────────────────────────────────────────────────────────────
	let query = '';

	// Filter chip state
	let archived: boolean | null = null;
	let pinned: boolean | null = null;
	let folderIds: string[] = [];
	let tagIds: string[] = [];
	let modelIds: string[] = [];
	let datePreset: 'all' | 'today' | '7d' | '30d' | 'year' = 'all';
	let sort: 'relevance' | 'recent' = 'relevance';

	// ── Results ───────────────────────────────────────────────────────────
	let response: ChatSearchResponse | null = null;
	$: hits = (response?.hits ?? []) as ChatSearchHit[];
	$: facets = (response?.facets ?? null) as ChatSearchFacets | null;
	$: usedFuzzy = response?.used_fuzzy ?? false;
	$: totalCount = response?.total ?? 0;

	let optimisticHits: ChatSearchHit[] = [];
	$: displayHits = hits.length > 0 ? hits : optimisticHits;

	let loading = false;
	let chatCount: number | null = null;

	let recentSearchesRef: { reload: () => void } | undefined;

	// ── Debounce / abort plumbing ──────────────────────────────────────────
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;
	let firstCharFired = false;
	let inFlightController: AbortController | null = null;

	// ── Keyboard nav ──────────────────────────────────────────────────────
	let actions: { label: string; onClick: () => Promise<void>; icon: any }[] = [];
	let selectedIdx: number | null = null;

	// ── Preview pane ──────────────────────────────────────────────────────
	let selectedHit: ChatSearchHit | null = null;
	let selectedModels = [''];
	let history: any = null;
	let messages: any[] | null = null;
	let chatCache: Record<string, any> = {};
	let previewDebounce: ReturnType<typeof setTimeout> | null = null;
	let previewRequestId = 0;

	const computeDateRange = (): { updated_after: number | null; updated_before: number | null } => {
		const now = Math.floor(Date.now() / 1000);
		const day = 86400;
		switch (datePreset) {
			case 'today':
				return { updated_after: now - day, updated_before: null };
			case '7d':
				return { updated_after: now - 7 * day, updated_before: null };
			case '30d':
				return { updated_after: now - 30 * day, updated_before: null };
			case 'year':
				return { updated_after: now - 365 * day, updated_before: null };
			default:
				return { updated_after: null, updated_before: null };
		}
	};

	const runSearch = async (immediate = false) => {
		if (!show) return;
		if (debounceTimer) {
			clearTimeout(debounceTimer);
			debounceTimer = null;
		}
		const fire = async () => {
			if (inFlightController) inFlightController.abort();
			inFlightController = new AbortController();
			const { updated_after, updated_before } = computeDateRange();
			loading = true;
			try {
				const res = await searchChats(
					localStorage.token,
					{
						text: query,
						page: 1,
						limit: 30,
						folder_ids: folderIds,
						tag_ids: tagIds,
						pinned,
						archived,
						updated_after,
						updated_before,
						sort
					},
					inFlightController.signal
				);
				response = res;
				selectedIdx = res.hits.length > 0 ? actions.length : null;
				schedulePreview(selectedIdx);
				optimisticHits = [];
			} catch (err: any) {
				if (err?.name === 'AbortError') return;
				console.error(err);
			} finally {
				loading = false;
			}
		};

		// First-character optimism: render title-prefix matches from the
		// already-loaded sidebar chats immediately, then fire backend after a
		// short 50ms gap. Subsequent keystrokes use 150ms debounce.
		const text = query.trim();
		if (text.length > 0 && !firstCharFired) {
			firstCharFired = true;
			const loaded = ($chatsStore ?? []) as { id: string; title: string; updated_at: number }[];
			const lower = text.toLowerCase();
			optimisticHits = loaded
				.filter((c) => (c.title ?? '').toLowerCase().includes(lower))
				.slice(0, 8)
				.map((c) => ({
					id: c.id,
					title: c.title ?? '',
					updated_at: c.updated_at,
					created_at: 0,
					archived: false,
					pinned: false,
					folder_id: null,
					snippet: null,
					match_count: 0,
					matched_message_id: null,
					matched_role: null,
					score: 0
				}));
			debounceTimer = setTimeout(fire, 50);
			return;
		}

		if (text.length === 0) {
			firstCharFired = false;
			optimisticHits = [];
		}

		if (immediate) {
			fire();
		} else {
			debounceTimer = setTimeout(fire, 150);
		}
	};

	const schedulePreview = (idx: number | null) => {
		if (previewDebounce) clearTimeout(previewDebounce);
		previewDebounce = setTimeout(() => {
			loadChatPreview(idx);
		}, 120);
	};

	const loadChatPreview = async (idx: number | null) => {
		if (idx === null) {
			selectedHit = null;
			messages = null;
			history = null;
			return;
		}
		const hitIdx = idx - actions.length;
		if (hitIdx < 0) {
			selectedHit = null;
			return;
		}
		const hit = displayHits[hitIdx];
		if (!hit) return;
		const requestId = ++previewRequestId;

		let chat = chatCache[hit.id];
		if (!chat) {
			chat = await getChatById(localStorage.token, hit.id).catch(() => null);
			if (chat) chatCache[hit.id] = chat;
		}
		if (requestId !== previewRequestId) return;

		if (chat) {
			selectedHit = hit;
			selectedModels =
				(chat?.chat?.models ?? undefined) !== undefined
					? chat?.chat?.models
					: [chat?.chat?.models ?? ''];
			history = chat?.chat?.history;
			messages = createMessagesList(chat?.chat?.history, chat?.chat?.history?.currentId);

			await tick();
			scrollPreviewToMatch(hit.matched_message_id);
		} else {
			toast.error($i18n.t('Failed to load chat preview'));
			selectedHit = null;
			messages = null;
			history = null;
		}
	};

	// Scroll the preview pane to the matched message (the "mind-reading" bit).
	const scrollPreviewToMatch = async (messageId: string | null) => {
		const container = document.getElementById('chat-preview');
		if (!container) return;
		if (!messageId) {
			container.scrollTop = container.scrollHeight;
			return;
		}
		// Messages render with `id={message-${id}}` in Messages.svelte's child markup.
		// We use a broad attribute selector to be resilient to small naming shifts.
		let target = container.querySelector(
			`[data-message-id="${CSS.escape(messageId)}"], #message-${CSS.escape(messageId)}`
		) as HTMLElement | null;
		if (!target) {
			// Fall back: try to find any element whose id contains the message id
			target = container.querySelector(`[id*="${CSS.escape(messageId)}"]`) as HTMLElement | null;
		}
		if (target) {
			target.scrollIntoView({ block: 'center', behavior: 'instant' });
			target.classList.add('search-match-flash');
			setTimeout(() => target?.classList.remove('search-match-flash'), 1400);
		} else {
			container.scrollTop = container.scrollHeight;
		}
	};

	const onKeyDown = (e: KeyboardEvent) => {
		if (!show) return;
		if (e.code === 'Escape') {
			show = false;
			onClose();
			return;
		}
		if (e.code === 'Enter') {
			const el = document.querySelector(`[data-arrow-selected="true"]`) as HTMLElement | null;
			if (el) {
				if (query.trim()) searchHistoryAdd(query.trim());
				el.click();
				show = false;
			}
			return;
		}
		if (e.code === 'ArrowDown') {
			const total = actions.length + displayHits.length;
			selectedIdx = Math.min((selectedIdx ?? -1) + 1, total - 1);
			schedulePreview(selectedIdx);
			const el = document.querySelector(`[data-arrow-selected="true"]`) as HTMLElement | null;
			el?.scrollIntoView({ block: 'center', behavior: 'instant' });
		} else if (e.code === 'ArrowUp') {
			selectedIdx = Math.max((selectedIdx ?? 0) - 1, 0);
			schedulePreview(selectedIdx);
			const el = document.querySelector(`[data-arrow-selected="true"]`) as HTMLElement | null;
			el?.scrollIntoView({ block: 'center', behavior: 'instant' });
		}
	};

	const onChipsChange = () => {
		runSearch(true);
	};

	const onSearchInput = () => {
		runSearch(false);
	};

	const inputKeydown = (e: KeyboardEvent) => {
		if (e.code === 'Enter' && displayHits.length > 0) {
			const el = document.querySelector(`[data-arrow-selected="true"]`) as HTMLElement | null;
			if (el) {
				if (query.trim()) searchHistoryAdd(query.trim());
				el.click();
				show = false;
			}
			return;
		}
		if (e.code === 'ArrowDown') {
			selectedIdx = Math.min((selectedIdx ?? -1) + 1, actions.length + displayHits.length - 1);
		} else if (e.code === 'ArrowUp') {
			selectedIdx = Math.max((selectedIdx ?? 0) - 1, 0);
		} else {
			selectedIdx = actions.length;
		}
		schedulePreview(selectedIdx);
		const el = document.querySelector(`[data-arrow-selected="true"]`) as HTMLElement | null;
		el?.scrollIntoView({ block: 'center', behavior: 'instant' });
	};

	const onRecentPick = (e: CustomEvent<string>) => {
		query = e.detail;
		runSearch(true);
	};

	$: if (show) {
		void initOpen();
	}

	const initOpen = async () => {
		await tick();
		// Reset transient state on each open
		response = null;
		optimisticHits = [];
		selectedHit = null;
		messages = null;
		history = null;
		selectedIdx = null;
		firstCharFired = false;
		chatCount = await getChatCount(localStorage.token).catch(() => null);
		recentSearchesRef?.reload();
		// Initial: fetch with whatever query/filters are set (usually empty)
		runSearch(true);
	};

	onMount(() => {
		actions = [
			{
				label: $i18n.t('Start a new conversation'),
				onClick: async () => {
					await goto(`/${query ? `?q=${encodeURIComponent(query)}` : ''}`);
					show = false;
					onClose();
				},
				icon: PencilSquare
			},
			...(($config?.features?.enable_notes ?? false) &&
			($user?.role === 'admin' || ($user?.permissions?.features?.notes ?? true))
				? [
						{
							label: $i18n.t('Create a new note'),
							onClick: async () => {
								await goto(`/notes${query ? `?content=${encodeURIComponent(query)}` : ''}`);
								show = false;
								onClose();
							},
							icon: PageEdit
						}
					]
				: [])
		];
		document.addEventListener('keydown', onKeyDown);
	});

	onDestroy(() => {
		if (debounceTimer) clearTimeout(debounceTimer);
		if (previewDebounce) clearTimeout(previewDebounce);
		if (inFlightController) inFlightController.abort();
		document.removeEventListener('keydown', onKeyDown);
	});
</script>

<Modal size="xl" bind:show>
	<div class="py-3 dark:text-gray-300 text-gray-700">
		<div class="px-4 pb-1.5">
			<SearchInput
				bind:value={query}
				on:input={onSearchInput}
				placeholder={$i18n.t('Search')}
				showClearButton={true}
				onFocus={() => {
					selectedIdx = null;
					messages = null;
				}}
				onKeydown={inputKeydown}
			/>
		</div>

		<FilterChips
			bind:archived
			bind:pinned
			bind:folderIds
			bind:tagIds
			bind:datePreset
			bind:sort
			{facets}
			on:change={onChipsChange}
		/>

		{#if !query && response && hits.length === 0}
			<RecentSearches bind:this={recentSearchesRef} on:pick={onRecentPick} />
		{/if}

		{#if usedFuzzy && response?.did_you_mean}
			<div
				class="mx-4 mb-2 px-3 py-1.5 text-xs rounded-lg bg-amber-50 dark:bg-amber-900/20 text-amber-800 dark:text-amber-300"
			>
				{$i18n.t('No exact matches for')} <strong>{response.did_you_mean}</strong>.
				{$i18n.t('Showing similar matches.')}
			</div>
		{/if}

		{#if chatCount !== null && !query}
			<div class="px-6 pb-2 text-xs text-gray-400 dark:text-gray-500">
				{$i18n.t('You have {{count}} chats', { count: chatCount.toLocaleString() })}
			</div>
		{/if}

		{#if response && (query || archived !== null || pinned !== null || folderIds.length || tagIds.length || datePreset !== 'all')}
			<div class="px-6 pb-1 text-xs text-gray-500 dark:text-gray-500">
				{#if loading}
					{$i18n.t('Searching...')}
				{:else if totalCount === 0}
					{$i18n.t('No matches')}
				{:else}
					{$i18n.t('{{count}} results', { count: totalCount.toLocaleString() })}
				{/if}
			</div>
		{/if}

		<div class="flex px-4 pb-1">
			<div
				class="flex flex-col overflow-y-auto h-96 md:h-[40rem] max-h-full scrollbar-hidden w-full flex-1 pr-2"
			>
				{#if actions.length > 0}
					<div class="w-full text-xs text-gray-500 dark:text-gray-500 font-medium pb-2 px-2">
						{$i18n.t('Actions')}
					</div>
					{#each actions as action, idx (action.label)}
						<button
							class="w-full flex items-center rounded-xl text-sm py-2 px-3 hover:bg-gray-50 dark:hover:bg-gray-850 {selectedIdx ===
							idx
								? 'bg-gray-50 dark:bg-gray-850'
								: ''}"
							data-arrow-selected={selectedIdx === idx ? 'true' : undefined}
							on:mouseenter={() => {
								selectedIdx = idx;
								schedulePreview(idx);
							}}
							on:click={async () => {
								await action.onClick();
							}}
							type="button"
						>
							<div class="pr-2">
								<svelte:component this={action.icon} />
							</div>
							<div class="flex-1 text-left text-ellipsis line-clamp-1">
								{action.label}
							</div>
						</button>
					{/each}
				{/if}

				{#if response || optimisticHits.length > 0}
					<hr class="border-gray-50 dark:border-gray-850 my-3" />
					{#if displayHits.length === 0 && !loading}
						<div class="text-xs text-gray-500 dark:text-gray-400 text-center px-5 py-4">
							{$i18n.t('No matches')}
						</div>
					{:else}
						{#each displayHits as hit, idx (hit.id)}
							<ResultRow
								{hit}
								selected={selectedIdx === idx + actions.length}
								on:mouseenter={() => {
									selectedIdx = idx + actions.length;
									schedulePreview(selectedIdx);
								}}
								on:click={async () => {
									if (query.trim()) searchHistoryAdd(query.trim());
									await goto(`/c/${hit.id}`);
									show = false;
									onClose();
								}}
							/>
						{/each}
					{/if}
				{:else}
					<div class="w-full h-full flex justify-center items-center">
						<Spinner className="size-5" />
					</div>
				{/if}
			</div>

			<div
				id="chat-preview"
				class="hidden md:flex md:flex-1 w-full overflow-y-auto h-96 md:h-[40rem] scrollbar-hidden"
			>
				{#if messages === null}
					<div
						class="w-full h-full flex justify-center items-center text-gray-500 dark:text-gray-400 text-sm"
					>
						{$i18n.t('Select a conversation to preview')}
					</div>
				{:else}
					<div class="w-full h-full flex flex-col">
						<Messages
							className="h-full flex pt-4 pb-8 w-full"
							chatId={`chat-preview-${selectedHit?.id ?? ''}`}
							user={$user}
							readOnly={true}
							{selectedModels}
							bind:history
							bind:messages
							autoScroll={false}
							sendMessage={() => {}}
							continueResponse={() => {}}
							regenerateResponse={() => {}}
						/>
					</div>
				{/if}
			</div>
		</div>
	</div>
</Modal>

<style>
	:global(.search-match-flash) {
		animation: search-match-flash 1.2s ease-out;
	}
	@keyframes search-match-flash {
		0% {
			background-color: rgba(250, 204, 21, 0.35);
		}
		100% {
			background-color: transparent;
		}
	}
</style>
