<script lang="ts">
	import { getContext, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { chatId, chatTitle } from '$lib/stores';
	import { updateChatById } from '$lib/apis/chats';
	import { refreshChatList } from '$lib/stores/chatList';
	import { updateFolderChatLists } from '$lib/stores/folderStates';
	import type { AppLayoutContext } from '$lib/types';
	import { openFolderChat } from './folderChat';
	import {
		type FolderStatus,
		type WorkspaceChat,
		type WorkspacePage,
		isChatUnread
	} from '$lib/utils/folders';
	import ChatParticipants from '$lib/components/common/ChatParticipants.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import FolderTags from './FolderTags.svelte';
	import FolderChatMenu from './FolderChatMenu.svelte';
	import FolderChatLink from './FolderChatLink.svelte';
	import Icon from '$lib/components/chat/FileNav/Icon.svelte';
	import FolderStatusControl from './FolderStatus.svelte';
	import StatusIcon from './FolderStatusIcon.svelte';
	import FolderStatusTime from './FolderStatusTime.svelte';
	import { formatDateDetails, formatShortDate } from '$lib/utils';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');

	export let groups: {
		id: string;
		label: string;
		status?: FolderStatus;
		dot?: string;
		spinner?: boolean;
		page?: WorkspacePage;
	}[] = [];
	export let saving = '';
	export let loading = false;
	export let loadingGroup = '';
	export let onMore: (id: string) => Promise<void>;
	export let onMove: (chat: WorkspaceChat, status: FolderStatus) => Promise<void>;
	export let onTagsChange: () => Promise<void>;

	let collapsed: Record<string, boolean> = {};
	let menuOpen: Record<string, boolean> = {};

	// Inline rename, like the sidebar chat item.
	let renaming = '';
	let renameValue = '';
	async function startRename(chat: WorkspaceChat) {
		renaming = chat.id;
		renameValue = chat.title;
		await tick();
		const input = container?.querySelector<HTMLInputElement>('[data-rename-input]');
		input?.focus();
		input?.select();
	}
	async function saveRename(chat: WorkspaceChat) {
		if (renaming !== chat.id) return;
		const title = renameValue.trim();
		renaming = '';
		if (!title || title === chat.title) return;
		try {
			await updateChatById(localStorage.token, chat.id, { title });
			updateFolderChatLists({ id: chat.id, title });
			if (chat.id === $chatId) chatTitle.set(title);
			await Promise.all([
				refreshChatList(localStorage.token, { refreshPinned: true }),
				onTagsChange()
			]);
		} catch (error) {
			toast.error(`${error}`);
		}
	}
	let container: HTMLDivElement;

	const appLayout = getContext<AppLayoutContext | undefined>('appLayout');
	$: showStatusTime = groups.some((group) =>
		group.page?.chats.some((chat) => chat.status_since && chat.status)
	);

	function open(event: MouseEvent, chat: WorkspaceChat) {
		if ((event.target as Element).closest('a, button, input, [role="menu"]')) return;
		if (window.getSelection()?.toString()) return;
		openFolderChat(chat, appLayout, event);
	}

	// j/k and arrow keys move between rows, like Linear.
	function navigate(event: KeyboardEvent) {
		const keys: Record<string, number> = { ArrowDown: 1, j: 1, ArrowUp: -1, k: -1 };
		const step = keys[event.key];
		if (!step || event.metaKey || event.ctrlKey || event.altKey) return;
		const target = event.target as HTMLElement;
		if (!target.matches('[data-row-link]')) return;
		const links = [...container.querySelectorAll<HTMLElement>('[data-row-link]')];
		const next = links[links.indexOf(target) + step];
		if (!next) return;
		event.preventDefault();
		next.focus();
		next.scrollIntoView({ block: 'nearest' });
	}

	// Ungrouped lists page in as the end of the list scrolls into view.
	function sentinel(node: HTMLElement, id: string) {
		let current = id;
		const observer = new IntersectionObserver(
			(entries) => {
				if (entries.some((entry) => entry.isIntersecting) && !loading && !loadingGroup)
					void onMore(current);
			},
			{ root: container, rootMargin: '240px' }
		);
		observer.observe(node);
		return {
			update(next: string) {
				current = next;
			},
			destroy() {
				observer.disconnect();
			}
		};
	}
</script>

<!-- svelte-ignore a11y-no-static-element-interactions -->
<div
	bind:this={container}
	class="folder-list scrollbar-hidden h-full min-h-0 min-w-0 overflow-y-auto px-3 @container"
	style="padding-bottom: calc(var(--folder-composer-space, 0px) + 1.5rem)"
	on:keydown={navigate}
>
	{#each groups as group (group.id)}
		{@const chats = group.page?.chats ?? []}
		{#if group.label}
			<!-- An opaque strip behind the header hides rows above it and behind its rounded corners. -->
			<div class="sticky top-0 z-[1] mt-1 bg-white pt-0.5 first:mt-0 dark:bg-gray-900">
				<div class="group-header flex h-8 items-center gap-2 rounded-xl pl-2 pr-3">
					<button
						type="button"
						class="flex size-5 items-center justify-center rounded-md text-gray-400 hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-200"
						aria-expanded={!collapsed[group.id]}
						aria-label={collapsed[group.id]
							? $i18n.t('Expand {{name}}', { name: group.label })
							: $i18n.t('Collapse {{name}}', { name: group.label })}
						on:click={() => (collapsed = { ...collapsed, [group.id]: !collapsed[group.id] })}
					>
						<ChevronRight
							className="size-3 transition-transform {collapsed[group.id] ? '' : 'rotate-90'}"
							strokeWidth="2"
						/>
					</button>
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
					<h3 class="text-xs text-gray-700 dark:text-gray-200">
						{group.label}
					</h3>
					<span class="text-xs tabular-nums text-gray-400 dark:text-gray-500"
						>{group.page?.total ?? ''}</span
					>
				</div>
			</div>
		{/if}

		{#if !collapsed[group.id]}
			<ul class="py-0.5" aria-label={group.label || undefined}>
				{#each chats as chat (chat.id)}
					{@const unread = chat.id !== $chatId && !chat.active && isChatUnread(chat)}
					<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
					<li
						data-folder-item
						class="group flex cursor-pointer items-center gap-1.5 rounded-xl px-3 py-1.5 transition-colors hover:bg-gray-50 focus-within:bg-gray-50 dark:hover:bg-gray-850/50 dark:focus-within:bg-gray-850/50 {saving ===
						chat.id
							? 'opacity-60'
							: ''}"
						on:click={(event) => open(event, chat)}
					>
						<div class="flex shrink-0 items-center gap-2">
							<FolderStatusControl {chat} disabled={!!saving || loading} onChange={onMove} />
							{#if showStatusTime}
								<!-- Time in status; fixed width keeps titles aligned across rows. -->
								<span class="-ml-1 flex w-6 shrink-0"><FolderStatusTime {chat} /></span>
							{/if}
							<!-- Same marker as the sidebar chat item; takes no space when absent. -->
							{#if chat.pending_approval || chat.active || unread}
								<span class="flex size-3 shrink-0 items-center justify-center">
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
									{:else if unread}
										<span
											class="size-1.5 rounded-full bg-sky-500"
											role="status"
											aria-label={$i18n.t('Unread')}
											title={$i18n.t('Unread')}
										></span>
									{/if}
								</span>
							{/if}
						</div>

						<div class="flex min-w-0 flex-1 items-center gap-2">
							{#if renaming === chat.id}
								<input
									data-rename-input
									class="min-w-0 flex-1 bg-transparent text-[0.8125rem] leading-5 text-gray-900 outline-none dark:text-white"
									aria-label={$i18n.t('Rename')}
									bind:value={renameValue}
									on:blur={() => saveRename(chat)}
									on:keydown={(event) => {
										if (event.isComposing || event.keyCode === 229) return;
										if (event.key === 'Enter') {
											event.preventDefault();
											void saveRename(chat);
										} else if (event.key === 'Escape') {
											event.preventDefault();
											renaming = '';
										}
									}}
								/>
							{:else}
								<FolderChatLink
									rowLink
									chatId={chat.id}
									title={chat.title}
									disabled={!!menuOpen[chat.id]}
									className="min-w-0 shrink truncate rounded text-[0.8125rem] leading-5 outline-none focus-visible:underline {unread
										? 'text-gray-900 dark:text-white'
										: 'text-gray-700 dark:text-gray-200'}"
									onclick={(event) => openFolderChat(chat, appLayout, event)}
								/>
							{/if}
							{#if chat.automation_id}
								<span
									class="flex shrink-0 text-gray-400 dark:text-gray-500"
									title={$i18n.t('Made by an automation')}
									aria-label={$i18n.t('Made by an automation')}
									><Icon name="clock" size={12} /></span
								>
							{/if}
							{#if chat.search_snippet}
								<span
									class="hidden min-w-0 flex-1 truncate text-xs text-gray-400 @lg:block dark:text-gray-500"
									>{chat.search_snippet}</span
								>
							{/if}
						</div>

						<div class="ml-2 flex shrink-0 items-center gap-3">
							<div class="hidden @md:flex">
								<FolderTags {chat} onChange={onTagsChange} />
							</div>
							<div class="hidden @sm:flex">
								<ChatParticipants
									participants={chat.participants ?? []}
									owner={{ id: chat.user_id, name: chat.owner_name ?? null }}
								/>
							</div>
							<!-- The menu takes the date's place on hover, so nothing shifts. -->
							<div
								class="date-slot relative flex w-14 shrink-0 items-center justify-end"
								class:open={menuOpen[chat.id]}
							>
								<Tooltip
									as="span"
									className="row-date flex shrink-0"
									placement="top-end"
									content={formatDateDetails(chat.updated_at, $i18n.language)}
								>
									<time
										class="w-14 text-right text-[0.6875rem] tabular-nums text-gray-400 dark:text-gray-500"
										datetime={new Date(chat.updated_at * 1000).toISOString()}
										>{formatShortDate(chat.updated_at, $i18n.language)}</time
									>
								</Tooltip>
								<div class="chat-menu absolute inset-y-0 right-0 flex items-center">
									<FolderChatMenu
										{chat}
										bind:open={menuOpen[chat.id]}
										onRename={() => startRename(chat)}
										onChange={onTagsChange}
									/>
								</div>
							</div>
						</div>
					</li>
				{/each}
			</ul>

			{#if group.page?.has_more}
				{#if group.label}
					<button
						type="button"
						class="flex w-full items-center rounded-xl py-1.5 pl-9.5 text-xs text-gray-400 transition-colors hover:bg-gray-50 hover:text-gray-700 disabled:pointer-events-none dark:text-gray-500 dark:hover:bg-gray-850/50 dark:hover:text-gray-300"
						disabled={loading || !!loadingGroup}
						on:click={() => onMore(group.id)}
					>
						{loadingGroup === group.id
							? $i18n.t('Loading…')
							: $i18n.t('Show {{count}} more', {
									count: Math.max(0, (group.page?.total ?? 0) - chats.length)
								})}
					</button>
				{:else}
					<div use:sentinel={group.id} class="flex h-10 items-center justify-center">
						{#if loadingGroup === group.id}<Spinner className="size-3.5" />{/if}
					</div>
				{/if}
			{/if}
		{/if}
	{/each}
</div>

<style>
	/* A soft, opaque band: the old tint mixed into the page background, so rows never show through. */
	.group-header {
		background: color-mix(in oklab, var(--color-gray-50) 60%, var(--color-white));
	}
	:global(.dark) .group-header {
		background: color-mix(in oklab, var(--color-gray-850) 30%, var(--color-gray-900));
	}

	/* The menu replaces the date on hover, focus, or while open; touch shows the menu. */
	@media (hover: hover) {
		.date-slot:not(.open) .chat-menu {
			opacity: 0;
			pointer-events: none;
		}
		:global([data-folder-item]:hover) .date-slot .chat-menu,
		:global([data-folder-item]:focus-within) .date-slot .chat-menu {
			opacity: 1;
			pointer-events: auto;
		}
		.date-slot.open :global(.row-date),
		:global([data-folder-item]:hover) .date-slot :global(.row-date),
		:global([data-folder-item]:focus-within) .date-slot :global(.row-date) {
			opacity: 0;
		}
	}
	@media (hover: none) {
		.date-slot :global(.row-date) {
			opacity: 0;
		}
	}
</style>
