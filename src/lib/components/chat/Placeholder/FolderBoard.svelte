<script lang="ts">
	import { getContext, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { chatId, chatTitle } from '$lib/stores';
	import { updateChatById } from '$lib/apis/chats';
	import { refreshChatList, setChatTitle } from '$lib/stores/chatList';
	import type { AppLayoutContext } from '$lib/types';
	import { openFolderChat } from './folderChat';
	import type { Readable } from 'svelte/store';
	import {
		type CanEditChat,
		type FolderStatus,
		type FolderPriority,
		type WorkspaceChat,
		type WorkspacePage,
		isChatUnread,
		priorityKey,
		statusKey
	} from '$lib/utils/folders';
	import ChatParticipants from '$lib/components/common/ChatParticipants.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import FolderTags from './FolderTags.svelte';
	import FolderChatMenu from './FolderChatMenu.svelte';
	import FolderChatLink from './FolderChatLink.svelte';
	import Icon from '$lib/components/chat/FileNav/Icon.svelte';
	import FolderStatusControl from './FolderStatus.svelte';
	import FolderPriorityControl from './FolderPriority.svelte';
	import StatusIcon from './FolderStatusIcon.svelte';
	import PriorityIcon from './FolderPriorityIcon.svelte';
	import FolderStatusTime from './FolderStatusTime.svelte';
	import { formatDateDetails, formatShortDate } from '$lib/utils';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	type BoardGroup = {
		id: string;
		label: string;
		status?: FolderStatus;
		priority?: FolderPriority;
		dot?: string;
		spinner?: boolean;
		page?: WorkspacePage;
	};
	type Field = 'status' | 'priority';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');
	const canEdit = getContext<Readable<CanEditChat> | undefined>('folder-can-edit');

	export let columns: BoardGroup[] = [];
	/** Optional swimlanes; cards are placed by `rowOf`. */
	export let rows: BoardGroup[] | null = null;
	export let rowOf: (chat: WorkspaceChat) => string[] = () => [];
	/** What a drop into this cell sets: status and/or priority, or nothing. */
	export let dropTargets: (column: string, row: string | null) => [Field, string][] = (column) => [
		['status', column]
	];
	export let showPriority = true;
	export let onMore: (id: string) => Promise<void>;
	export let onMove: (chat: WorkspaceChat, status: FolderStatus) => Promise<void>;
	export let onPriority: (chat: WorkspaceChat, priority: FolderPriority) => Promise<void>;
	export let onDrop: (chat: WorkspaceChat, changes: [Field, string][]) => Promise<void>;
	export let onTagsChange: () => Promise<void>;
	export let onAddStatus: (() => void) | null = null;
	/** Saves a new column order; set only when columns are statuses. */
	export let onReorder: ((ids: string[]) => Promise<void>) | null = null;
	/** Swimlanes the user folded. */
	export let collapsed: Record<string, boolean> = {};
	export let onCollapse: (id: string) => void;
	export let saving = '';
	export let loading = false;
	export let loadingGroup = '';

	let dragged: WorkspaceChat | null = null;
	let over = '';

	// Status columns move by their header, live like the statuses modal.
	let moving = '';
	let order: string[] | null = null;
	$: shownColumns = order
		? order.flatMap((id) => columns.filter((column) => column.id === id))
		: columns;
	const movable = (column: BoardGroup) => !!onReorder && !!column.status;
	function moveColumn(event: DragEvent, overId: string) {
		if (!moving || !order) return false;
		event.preventDefault();
		const target = columns.find((column) => column.id === overId);
		if (overId === moving || !target || !movable(target)) return true;
		const next = order.filter((id) => id !== moving);
		next.splice(order.indexOf(overId), 0, moving);
		order = next;
		return true;
	}
	async function endMove(event: DragEvent) {
		const ids = order;
		moving = '';
		if (
			ids &&
			event.dataTransfer?.dropEffect !== 'none' &&
			ids.join() !== columns.map((column) => column.id).join()
		)
			await onReorder?.(ids);
		order = null;
	}

	// Inline rename, like the list rows.
	let renaming = '';
	let renameValue = '';
	let renameInput: HTMLInputElement;
	async function startRename(chat: WorkspaceChat) {
		renaming = chat.id;
		renameValue = chat.title;
		await tick();
		renameInput?.focus();
		renameInput?.select();
	}
	async function saveRename(chat: WorkspaceChat) {
		if (renaming !== chat.id) return;
		const title = renameValue.trim();
		renaming = '';
		if (!title || title === chat.title) return;
		try {
			await updateChatById(localStorage.token, chat.id, { title });
			setChatTitle(chat.id, title);
			if (chat.id === $chatId) chatTitle.set(title);
			await Promise.all([
				refreshChatList(localStorage.token, { refreshPinned: true }),
				onTagsChange()
			]);
		} catch (error) {
			toast.error(`${error}`);
		}
	}

	const cellKey = (column: string, row: string | null) => `${column}\u0000${row ?? ''}`;
	const valueOf = (chat: WorkspaceChat, field: Field): string =>
		field === 'status' ? statusKey(chat.status) : priorityKey(chat.priority);
	// The changes a drop here would make to this chat.
	const changesFor = (chat: WorkspaceChat, column: string, row: string | null) =>
		dropTargets(column, row).filter(([field, value]) => valueOf(chat, field) !== value);
	$: canDrop = (column: string, row: string | null) => dropTargets(column, row).length > 0;
	$: draggableBoard = columns.some((column) => canDrop(column.id, rows?.[0]?.id ?? null));

	function drop(column: string, row: string | null) {
		const changes = dragged ? changesFor(dragged, column, row) : [];
		if (dragged && changes.length && $canEdit?.(dragged)) void onDrop(dragged, changes);
		dragged = null;
		over = '';
	}

	const dropzone = (column: string, row: string | null) => ({
		dragover: (event: DragEvent) => {
			if (moveColumn(event, column) || !dragged || !canDrop(column, row)) return;
			event.preventDefault();
			over = cellKey(column, row);
			if (event.dataTransfer)
				event.dataTransfer.dropEffect = changesFor(dragged, column, row).length ? 'move' : 'none';
		},
		dragleave: (event: DragEvent) => {
			const target = event.currentTarget as HTMLElement;
			if (!target.contains(event.relatedTarget as Node | null)) over = '';
		},
		drop: (event: DragEvent) => {
			event.preventDefault();
			drop(column, row);
		}
	});

	const cellChats = (column: BoardGroup, row: BoardGroup) =>
		(column.page?.chats ?? []).filter((chat) => rowOf(chat).includes(row.id));
	const rowCount = (row: BoardGroup) =>
		new Set(columns.flatMap((column) => cellChats(column, row).map((chat) => chat.id))).size;

	const appLayout = getContext<AppLayoutContext | undefined>('appLayout');

	function open(event: MouseEvent, chat: WorkspaceChat) {
		if ((event.target as Element).closest('a, button, input, [role="menu"]')) return;
		if (window.getSelection()?.toString()) return;
		openFolderChat(chat, appLayout, event);
	}
</script>

{#snippet groupIcon(group: BoardGroup)}
	{#if group.status}
		<StatusIcon status={group.status} />
	{:else if group.priority}
		<PriorityIcon priority={group.priority} />
	{:else if group.spinner}
		<span class="flex size-3.5 shrink-0 items-center justify-center"
			><Spinner className="size-3" /></span
		>
	{:else if group.dot}
		<span class="flex size-3.5 shrink-0 items-center justify-center"
			><span class="size-2 rounded-full {group.dot}"></span></span
		>
	{/if}
{/snippet}

{#snippet columnHeader(column: BoardGroup)}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<header
		class="flex h-9 shrink-0 items-center gap-2 px-3 {movable(column)
			? 'cursor-grab active:cursor-grabbing'
			: ''}"
		draggable={movable(column) && !saving && !loading}
		on:dragstart={(event) => {
			moving = column.id;
			order = columns.map((item) => item.id);
			event.dataTransfer?.setData('text/plain', column.id);
			if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move';
		}}
		on:dragend={endMove}
	>
		{@render groupIcon(column)}
		<h3 class="min-w-0 truncate text-xs text-base-700 dark:text-base-200">
			{column.label}
		</h3>
		<span class="text-xs tabular-nums text-base-400 dark:text-base-500"
			>{column.page?.total ?? ''}</span
		>
	</header>
{/snippet}

{#snippet more(column: BoardGroup)}
	{#if column.page?.has_more}
		<button
			type="button"
			class="flex h-7 w-full items-center justify-center rounded-lg text-xs text-base-400 transition-colors hover:bg-base-100 hover:text-base-700 dark:text-base-500 dark:hover:bg-base-800/60 dark:hover:text-base-300"
			disabled={loading || !!loadingGroup}
			on:click={() => onMore(column.id)}
		>
			{loadingGroup === column.id
				? $i18n.t('Loading…')
				: $i18n.t('Show {{count}} more', {
						count: Math.max(0, (column.page?.total ?? 0) - (column.page?.chats.length ?? 0))
					})}
		</button>
	{/if}
{/snippet}

{#snippet card(chat: WorkspaceChat)}
	{@const unread = chat.id !== $chatId && !chat.active && isChatUnread(chat)}
	<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
	<article
		data-folder-item
		class="group cursor-pointer rounded-xl border border-base-1000/[0.06] bg-base-0 px-3 py-2 shadow-[0_1px_2px_rgba(0,0,0,0.03)] transition hover:border-base-1000/[0.09] dark:border-base-0/[0.06] dark:bg-base-900 dark:hover:border-base-0/[0.09] {saving ===
			chat.id || dragged?.id === chat.id
			? 'opacity-40'
			: ''}"
		draggable={draggableBoard && $canEdit?.(chat) && !saving && !loading && renaming !== chat.id}
		on:click={(event) => open(event, chat)}
		on:dragstart={(event) => {
			dragged = chat;
			event.dataTransfer?.setData('text/plain', chat.id);
			if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move';
		}}
		on:dragend={() => {
			dragged = null;
			over = '';
		}}
	>
		<div class="flex items-start gap-1.5">
			<!-- Status, its time, then priority, on the title's first line. -->
			<div class="-ml-0.5 flex shrink-0 items-center gap-0.5">
				<FolderStatusControl {chat} disabled={!!saving || loading} onChange={onMove} />
				{#if chat.status_since && chat.status}
					<span class="flex h-5 shrink-0 items-center"><FolderStatusTime {chat} /></span>
				{/if}
				{#if showPriority}
					<FolderPriorityControl {chat} disabled={!!saving || loading} onChange={onPriority} />
				{/if}
			</div>
			{#if chat.pending_approval || chat.active || unread}
				<!-- Centered on the title's first line; same distance from the icons as in the list. -->
				<span class="-ml-0.5 flex h-5 w-3 shrink-0 items-center justify-center">
					{#if chat.pending_approval}
						<span
							class="size-1.5 rounded-full bg-yellow-500"
							role="status"
							aria-label={$i18n.t('Waiting for approval')}
							title={$i18n.t('Waiting for approval')}
						></span>
					{:else if chat.active}
						<span role="status" aria-label={$i18n.t('Generating…')}
							><Spinner className="size-3" /></span
						>
					{:else}
						<span
							class="size-1.5 rounded-full bg-sky-500"
							role="status"
							aria-label={$i18n.t('Unread')}
							title={$i18n.t('Unread')}
						></span>
					{/if}
				</span>
			{/if}
			{#if renaming === chat.id}
				<input
					bind:this={renameInput}
					class="min-w-0 flex-1 bg-transparent text-[0.8125rem] leading-5 text-base-900 outline-none dark:text-base-0"
					aria-label={$i18n.t('Rename')}
					bind:value={renameValue}
					on:blur={() => saveRename(chat)}
					on:keydown={(event) => {
						if (event.isComposing || event.keyCode === 229) return;
						if (event.key === 'Enter') void saveRename(chat);
						else if (event.key === 'Escape') renaming = '';
					}}
				/>
			{:else}
				<FolderChatLink
					chatId={chat.id}
					title={chat.title}
					side="right"
					disabled={!!dragged}
					className="min-w-0 flex-1 line-clamp-2 text-[0.8125rem] leading-5 outline-none focus-visible:underline {unread
						? 'text-base-900 dark:text-base-0'
						: 'text-base-700 dark:text-base-200'}"
					onclick={(event) => openFolderChat(chat, appLayout, event)}
				/>
			{/if}
			{#if chat.automation_id}
				<span
					class="mt-1 flex shrink-0 text-base-400 dark:text-base-500"
					title={$i18n.t('Made by an automation')}
					aria-label={$i18n.t('Made by an automation')}><Icon name="clock" size={12} /></span
				>
			{/if}
		</div>

		{#if chat.search_snippet}
			<p
				class="mt-1 line-clamp-2 text-xs leading-4 text-base-500 dark:text-base-400 {showPriority
					? 'pl-11.5'
					: 'pl-6'}"
			>
				{chat.search_snippet}
			</p>
		{/if}

		<!-- Lines up with the title, past the status and priority icons. -->
		<div class="relative mt-2 flex min-h-5 items-center gap-2 {showPriority ? 'pl-11.5' : 'pl-6'}">
			<div class="flex min-w-0 flex-1">
				<FolderTags {chat} onChange={onTagsChange} />
			</div>
			<ChatParticipants
				participants={chat.participants ?? []}
				owner={{ id: chat.user_id, name: chat.owner_name ?? null }}
			/>
			<Tooltip
				as="span"
				className="flex shrink-0"
				placement="top-end"
				content={formatDateDetails(chat.updated_at, $i18n.language)}
			>
				<time
					class="w-14 text-right text-[0.6875rem] tabular-nums text-base-400 dark:text-base-500"
					datetime={new Date(chat.updated_at * 1000).toISOString()}
					>{formatShortDate(chat.updated_at, $i18n.language)}</time
				>
			</Tooltip>
			{#if $canEdit?.(chat)}
				<!-- Covers the date on hover, focus, or while open; touch always shows the menu. -->
				<div
					class="absolute inset-y-0 right-0 flex w-14 items-center justify-end bg-base-0 group-hover:opacity-100 group-focus-within:opacity-100 has-[[aria-expanded=true]]:opacity-100 dark:bg-base-900 [@media(hover:hover)]:opacity-0"
				>
					<FolderChatMenu {chat} onRename={() => startRename(chat)} onChange={onTagsChange} />
				</div>
			{/if}
		</div>
	</article>
{/snippet}

{#snippet emptyCell(column: string, row: string | null)}
	<div
		class="flex h-20 items-center justify-center rounded-xl border border-dashed text-xs text-base-400 transition-colors dark:text-base-500 {over ===
		cellKey(column, row)
			? 'border-base-300 dark:border-base-700'
			: 'border-base-200/70 dark:border-base-800'}"
	>
		{$i18n.t('No conversations')}
	</div>
{/snippet}

{#snippet addStatus()}
	{#if onAddStatus}
		<button
			type="button"
			class="flex h-9 w-36 shrink-0 items-center gap-1.5 rounded-2xl px-3 text-xs text-base-400 transition-colors hover:bg-base-50 hover:text-base-700 dark:text-base-500 dark:hover:bg-base-850/40 dark:hover:text-base-200"
			on:click={onAddStatus}
		>
			<Plus className="size-3" strokeWidth="2" />{$i18n.t('Add status')}
		</button>
	{/if}
{/snippet}

{#if !rows}
	<!-- Columns only: each column runs full height and scrolls on its own. -->
	<div
		class="scrollbar-hidden flex h-full min-h-0 gap-2 overflow-x-auto px-3 pt-1 pb-2"
		aria-label={$i18n.t('Conversation board')}
	>
		{#each shownColumns as column (column.id)}
			{@const chats = column.page?.chats ?? []}
			{@const zone = dropzone(column.id, null)}
			<section
				class="flex min-h-0 w-72 min-w-64 flex-1 flex-col rounded-2xl transition-colors {moving ===
				column.id
					? 'opacity-40'
					: ''} {over === cellKey(column.id, null)
					? 'bg-base-100 ring-1 ring-base-200 dark:bg-base-850 dark:ring-base-800'
					: 'bg-base-50/80 dark:bg-base-850/40'}"
				aria-label={column.label}
				on:dragover={zone.dragover}
				on:dragleave={zone.dragleave}
				on:drop={zone.drop}
			>
				{@render columnHeader(column)}
				<div
					class="scrollbar-hidden min-h-0 flex-1 space-y-1.5 overflow-y-auto px-1.5"
					style="padding-bottom: calc(var(--folder-composer-space, 0px) + 0.375rem)"
				>
					{#each chats as chat (chat.id)}
						{@render card(chat)}
					{/each}
					{#if !loading && !chats.length}
						{@render emptyCell(column.id, null)}
					{/if}
					{@render more(column)}
				</div>
			</section>
		{/each}
		{@render addStatus()}
	</div>
{:else}
	<!-- Swimlanes: the board scrolls as one; column headers stick to the top. -->
	<div
		class="scrollbar-hidden h-full min-h-0 overflow-auto px-3 pt-1"
		style="padding-bottom: calc(var(--folder-composer-space, 0px) + 0.5rem)"
		aria-label={$i18n.t('Conversation board')}
	>
		<div class="inline-flex min-w-full flex-col">
			<div
				class="sticky top-0 z-[2] flex gap-2 bg-base-0/80 pb-1 backdrop-blur-md dark:bg-base-900/80"
			>
				{#each shownColumns as column (column.id)}
					<div
						class="w-72 shrink-0 rounded-2xl bg-base-50/80 dark:bg-base-850/40 {moving === column.id
							? 'opacity-40'
							: ''}"
						role="group"
						aria-label={column.label}
						on:dragover={(event) => moveColumn(event, column.id)}
						on:drop|preventDefault
					>
						{@render columnHeader(column)}
					</div>
				{/each}
				{@render addStatus()}
			</div>

			{#each rows as row (row.id)}
				{@const count = rowCount(row)}
				{#if count}
					<div class="sticky left-0 z-[1] flex h-8 w-fit items-center gap-2 pr-3">
						<button
							type="button"
							class="flex size-5 items-center justify-center rounded-md text-base-400 hover:text-base-700 dark:text-base-500 dark:hover:text-base-200"
							aria-expanded={!collapsed[row.id]}
							aria-label={collapsed[row.id]
								? $i18n.t('Expand {{name}}', { name: row.label })
								: $i18n.t('Collapse {{name}}', { name: row.label })}
							on:click={() => onCollapse(row.id)}
						>
							<ChevronRight
								className="size-3 transition-transform {collapsed[row.id] ? '' : 'rotate-90'}"
								strokeWidth="2"
							/>
						</button>
						{@render groupIcon(row)}
						<span class="text-xs text-base-700 dark:text-base-200">{row.label}</span>
						<span class="text-xs tabular-nums text-base-400 dark:text-base-500">{count}</span>
					</div>

					{#if !collapsed[row.id]}
						<div class="flex gap-2 pb-2">
							{#each shownColumns as column (column.id)}
								{@const chats = cellChats(column, row)}
								{@const zone = dropzone(column.id, row.id)}
								<div
									role="group"
									aria-label={`${column.label} · ${row.label}`}
									class="w-72 shrink-0 space-y-1.5 rounded-2xl p-1.5 transition-colors {over ===
									cellKey(column.id, row.id)
										? 'bg-base-100 ring-1 ring-base-200 dark:bg-base-850 dark:ring-base-800'
										: 'bg-base-50/80 dark:bg-base-850/40'}"
									on:dragover={zone.dragover}
									on:dragleave={zone.dragleave}
									on:drop={zone.drop}
								>
									{#each chats as chat (chat.id)}
										{@render card(chat)}
									{/each}
									{#if !chats.length}
										<div class="h-10"></div>
									{/if}
								</div>
							{/each}
						</div>
					{/if}
				{/if}
			{/each}

			<div class="flex gap-2">
				{#each shownColumns as column (column.id)}
					<div class="w-72 shrink-0">{@render more(column)}</div>
				{/each}
			</div>
		</div>
	</div>
{/if}
