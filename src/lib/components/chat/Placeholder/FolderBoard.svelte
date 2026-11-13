<script lang="ts">
	import { getContext } from 'svelte';
	import { chatId } from '$lib/stores';
	import type { AppLayoutContext } from '$lib/types';
	import { openFolderChat } from './folderChat';
	import {
		type FolderStatus,
		type WorkspaceChat,
		type WorkspacePage,
		isChatUnread,
		statusKey
	} from '$lib/utils/folders';
	import ChatParticipants from '$lib/components/common/ChatParticipants.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import FolderTags from './FolderTags.svelte';
	import FolderStatusControl from './FolderStatus.svelte';
	import StatusIcon from './FolderStatusIcon.svelte';
	import FolderStatusTime from './FolderStatusTime.svelte';
	import { formatDateDetails, formatShortDate } from '$lib/utils';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	type BoardGroup = {
		id: string;
		label: string;
		status?: FolderStatus;
		dot?: string;
		spinner?: boolean;
		page?: WorkspacePage;
	};

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');

	export let columns: BoardGroup[] = [];
	/** Optional swimlanes; cards are placed by `rowOf`. */
	export let rows: BoardGroup[] | null = null;
	export let rowOf: (chat: WorkspaceChat) => string[] = () => [];
	/** The status a drop into this cell sets, or null when the cell isn't a status. */
	export let dropStatus: (column: string, row: string | null) => FolderStatus | null = (column) =>
		column;
	export let onMore: (id: string) => Promise<void>;
	export let onMove: (chat: WorkspaceChat, status: FolderStatus) => Promise<void>;
	export let onTagsChange: () => Promise<void>;
	export let onAddStatus: (() => void) | null = null;
	export let saving = '';
	export let loading = false;
	export let loadingGroup = '';

	let dragged: WorkspaceChat | null = null;
	let over = '';
	let collapsed: Record<string, boolean> = {};

	const cellKey = (column: string, row: string | null) => `${column}\u0000${row ?? ''}`;
	$: canDrop = (column: string, row: string | null) => dropStatus(column, row) != null;
	$: draggableBoard = columns.some((column) => canDrop(column.id, rows?.[0]?.id ?? null));

	function drop(column: string, row: string | null) {
		const status = dropStatus(column, row);
		if (dragged && status && dragged.can_edit_status && statusKey(dragged.status) !== status)
			void onMove(dragged, status);
		dragged = null;
		over = '';
	}

	const dropzone = (column: string, row: string | null) => ({
		dragover: (event: DragEvent) => {
			if (!dragged || !canDrop(column, row)) return;
			event.preventDefault();
			over = cellKey(column, row);
			if (event.dataTransfer)
				event.dataTransfer.dropEffect =
					statusKey(dragged.status) === dropStatus(column, row) ? 'none' : 'move';
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
	<header class="flex h-9 shrink-0 items-center gap-2 px-3">
		{@render groupIcon(column)}
		<h3 class="min-w-0 truncate text-xs text-gray-700 dark:text-gray-200">
			{column.label}
		</h3>
		<span class="text-xs tabular-nums text-gray-400 dark:text-gray-500"
			>{column.page?.total ?? ''}</span
		>
	</header>
{/snippet}

{#snippet more(column: BoardGroup)}
	{#if column.page?.has_more}
		<button
			type="button"
			class="flex h-7 w-full items-center justify-center rounded-lg text-xs text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-700 dark:text-gray-500 dark:hover:bg-gray-800/60 dark:hover:text-gray-300"
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
		class="group cursor-pointer rounded-xl border border-black/[0.06] bg-white px-3 py-2 shadow-[0_1px_2px_rgba(0,0,0,0.03)] transition hover:border-black/[0.09] dark:border-white/[0.06] dark:bg-gray-900 dark:hover:border-white/[0.09] {saving ===
			chat.id || dragged?.id === chat.id
			? 'opacity-40'
			: ''}"
		draggable={draggableBoard && chat.can_edit_status && !saving && !loading}
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
			<div class="-ml-0.5 shrink-0">
				<FolderStatusControl {chat} disabled={!!saving || loading} onChange={onMove} />
			</div>
			<!-- Time in status, on the title's first line. -->
			{#if chat.status_since && chat.status}
				<span class="-ml-1 flex h-5 shrink-0 items-center"><FolderStatusTime {chat} /></span>
			{/if}
			{#if chat.pending_approval || chat.active || unread}
				<!-- Centered on the title's first line, like the list's marker slot. -->
				<span class="flex h-5 w-3 shrink-0 items-center justify-center">
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
			<a
				class="min-w-0 flex-1 line-clamp-2 text-[0.8125rem] leading-5 outline-none focus-visible:underline {unread
					? 'text-gray-900 dark:text-white'
					: 'text-gray-700 dark:text-gray-200'}"
				href={`/c/${chat.id}`}
				draggable="false"
				title={chat.title}
				on:click={(event) => openFolderChat(chat, appLayout, event)}>{chat.title}</a
			>
		</div>

		{#if chat.search_snippet}
			<p class="mt-1 line-clamp-2 pl-6 text-xs leading-4 text-gray-500 dark:text-gray-400">
				{chat.search_snippet}
			</p>
		{/if}

		<div class="mt-2 flex min-h-5 items-center gap-2 pl-6">
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
					class="shrink-0 text-[0.6875rem] tabular-nums text-gray-400 dark:text-gray-500"
					datetime={new Date(chat.updated_at * 1000).toISOString()}
					>{formatShortDate(chat.updated_at, $i18n.language)}</time
				>
			</Tooltip>
		</div>
	</article>
{/snippet}

{#snippet emptyCell(column: string, row: string | null)}
	<div
		class="flex h-20 items-center justify-center rounded-xl border border-dashed text-xs text-gray-400 transition-colors dark:text-gray-500 {over ===
		cellKey(column, row)
			? 'border-gray-300 dark:border-gray-700'
			: 'border-gray-200/70 dark:border-gray-800'}"
	>
		{$i18n.t('No conversations')}
	</div>
{/snippet}

{#snippet addStatus()}
	{#if onAddStatus}
		<button
			type="button"
			class="flex h-9 w-36 shrink-0 items-center gap-1.5 rounded-2xl px-3 text-xs text-gray-400 transition-colors hover:bg-gray-50 hover:text-gray-700 dark:text-gray-500 dark:hover:bg-gray-850/40 dark:hover:text-gray-200"
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
		{#each columns as column (column.id)}
			{@const chats = column.page?.chats ?? []}
			{@const zone = dropzone(column.id, null)}
			<section
				class="flex min-h-0 w-72 min-w-64 flex-1 flex-col rounded-2xl transition-colors {over ===
				cellKey(column.id, null)
					? 'bg-gray-100 ring-1 ring-gray-200 dark:bg-gray-850 dark:ring-gray-800'
					: 'bg-gray-50/80 dark:bg-gray-850/40'}"
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
			<div class="sticky top-0 z-[2] flex gap-2 bg-white pb-1 dark:bg-gray-900">
				{#each columns as column (column.id)}
					<div class="w-72 shrink-0 rounded-2xl bg-gray-50/80 dark:bg-gray-850/40">
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
							class="flex size-5 items-center justify-center rounded-md text-gray-400 hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-200"
							aria-expanded={!collapsed[row.id]}
							aria-label={collapsed[row.id]
								? $i18n.t('Expand {{name}}', { name: row.label })
								: $i18n.t('Collapse {{name}}', { name: row.label })}
							on:click={() => (collapsed = { ...collapsed, [row.id]: !collapsed[row.id] })}
						>
							<ChevronRight
								className="size-3 transition-transform {collapsed[row.id] ? '' : 'rotate-90'}"
								strokeWidth="2"
							/>
						</button>
						{@render groupIcon(row)}
						<span class="text-xs text-gray-700 dark:text-gray-200">{row.label}</span>
						<span class="text-xs tabular-nums text-gray-400 dark:text-gray-500">{count}</span>
					</div>

					{#if !collapsed[row.id]}
						<div class="flex gap-2 pb-2">
							{#each columns as column (column.id)}
								{@const chats = cellChats(column, row)}
								{@const zone = dropzone(column.id, row.id)}
								<div
									role="group"
									aria-label={`${column.label} · ${row.label}`}
									class="w-72 shrink-0 space-y-1.5 rounded-2xl p-1.5 transition-colors {over ===
									cellKey(column.id, row.id)
										? 'bg-gray-100 ring-1 ring-gray-200 dark:bg-gray-850 dark:ring-gray-800'
										: 'bg-gray-50/80 dark:bg-gray-850/40'}"
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
				{#each columns as column (column.id)}
					<div class="w-72 shrink-0">{@render more(column)}</div>
				{/each}
			</div>
		</div>
	</div>
{/if}
