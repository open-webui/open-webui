<script lang="ts">
	import { getContext, onDestroy } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	const i18n: Writable<i18nType> = getContext('i18n');

	import { page } from '$app/stores';
	import { mobile, showSidebar, chatId } from '$lib/stores';
	import { getChatListBySpaceId } from '$lib/apis/chats';

	import Emoji from '$lib/components/common/Emoji.svelte';
	import ChatItem from './ChatItem.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	export let className = '';
	export let space: {
		id: string;
		name: string;
		slug: string;
		emoji: string | null;
		description: string | null;
	};
	export let variant: 'private' | 'shared' | 'pinned' | 'bookmarked' = 'private';
	export let shiftKey = false;

	let expanded = false;
	let pinned = false;
	let spaceChats: Array<{ id: string; title: string; unread?: boolean }> = [];
	let loading = false;
	let loaded = false;
	let hoverTimeout: ReturnType<typeof setTimeout> | null = null;

	$: isActive = $page.url.pathname === `/spaces/${space.slug}`;

	async function loadChats() {
		if (loaded || loading) return;
		loading = true;
		try {
			const result = await getChatListBySpaceId(localStorage.token, space.id);
			spaceChats = result || [];
			loaded = true;
		} catch (err) {
			console.error('Failed to load space chats:', err);
			spaceChats = [];
		}
		loading = false;
	}

	function handleMouseEnter() {
		if ($mobile) return;
		hoverTimeout = setTimeout(async () => {
			if (!expanded) {
				await loadChats();
				expanded = true;
			}
		}, 300);
	}

	function handleMouseLeave() {
		if (hoverTimeout) {
			clearTimeout(hoverTimeout);
			hoverTimeout = null;
		}
		if (!pinned && !$mobile) {
			expanded = false;
		}
	}

	function togglePin(e: MouseEvent) {
		e.preventDefault();
		e.stopPropagation();
		if ($mobile) {
			loadChats();
			expanded = !expanded;
			pinned = expanded;
		} else {
			pinned = !pinned;
			if (pinned && !expanded) {
				loadChats();
				expanded = true;
			} else if (!pinned) {
				expanded = false;
			}
		}
	}

	function navigateToSpace() {
		if ($mobile) {
			showSidebar.set(false);
		}
	}

	onDestroy(() => {
		if (hoverTimeout) clearTimeout(hoverTimeout);
	});
</script>

<div
	class="w-full {className}"
	on:mouseenter={handleMouseEnter}
	on:mouseleave={handleMouseLeave}
	role="treeitem"
	aria-selected="false"
	tabindex="0"
	aria-expanded={expanded}
>
	<div
		id="sidebar-space-item-{space.id}"
		class="w-full rounded-lg flex relative group hover:bg-gray-100 dark:hover:bg-gray-800 {isActive
			? 'bg-gray-100 dark:bg-gray-800'
			: ''} px-2 py-1.5 dark:text-gray-300 text-gray-700 cursor-pointer select-none"
	>
		<button
			class="flex items-center justify-center size-5 shrink-0 mr-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
			on:click={togglePin}
			title={pinned ? $i18n.t('Unpin') : $i18n.t('Pin open')}
		>
			{#if loading}
				<Spinner className="size-3" />
			{:else}
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 16 16"
					fill="currentColor"
					class="size-3 transition-transform duration-200 {expanded ? 'rotate-90' : ''} {pinned
						? 'text-accent-500 dark:text-accent-400'
						: ''}"
				>
					<path
						fill-rule="evenodd"
						d="M6.22 4.22a.75.75 0 0 1 1.06 0l3.25 3.25a.75.75 0 0 1 0 1.06l-3.25 3.25a.75.75 0 0 1-1.06-1.06L8.94 8 6.22 5.28a.75.75 0 0 1 0-1.06Z"
						clip-rule="evenodd"
					/>
				</svg>
			{/if}
		</button>

		<a
			class="flex-1 flex items-center gap-2"
			href="/spaces/{space.slug}"
			on:click={navigateToSpace}
			draggable="false"
		>
			<div class="relative flex items-center justify-center size-5 shrink-0">
				{#if space.emoji}
					<Emoji shortCode={space.emoji} className="size-4" />
				{:else}
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="1.5"
						stroke="currentColor"
						class="size-4 {variant === 'shared'
							? 'text-accent-500 dark:text-accent-400'
							: variant === 'pinned'
								? 'text-accent-500 dark:text-accent-400'
								: variant === 'bookmarked'
									? 'text-amber-500 dark:text-amber-400'
									: 'text-gray-400 dark:text-gray-500'}"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75h15A2.25 2.25 0 0 1 21.75 12v.75m-8.69-6.44-2.12-2.12a1.5 1.5 0 0 0-1.061-.44H4.5A2.25 2.25 0 0 0 2.25 6v12a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9a2.25 2.25 0 0 0-2.25-2.25h-5.379a1.5 1.5 0 0 1-1.06-.44Z"
						/>
					</svg>
				{/if}
				{#if variant === 'shared'}
					<div
						class="absolute -bottom-0.5 -right-0.5 size-2.5 rounded-full bg-accent-500 dark:bg-accent-400 flex items-center justify-center"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="size-1.5 text-white"
						>
							<path
								d="M8 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM12.735 14c.618 0 1.093-.561.872-1.139a6.002 6.002 0 0 0-11.215 0c-.22.578.254 1.139.872 1.139h9.47Z"
							/>
						</svg>
					</div>
				{/if}
			</div>

			<div class="flex-1 text-sm truncate">
				{space.name}
			</div>
		</a>
	</div>

	<!-- Nested Chats (when expanded) -->
	{#if expanded}
		<div class="ml-4 mt-0.5 space-y-0.5 border-l border-gray-200 dark:border-gray-700 pl-2">
			{#if spaceChats.length > 0}
				{#each spaceChats as chat (chat.id)}
					<ChatItem
						id={chat.id}
						title={chat.title}
						selected={$chatId === chat.id}
						unread={chat.unread ?? false}
						{shiftKey}
					/>
				{/each}
			{:else if loaded}
				<div class="px-2 py-1.5 text-xs text-gray-400 dark:text-gray-500 italic">
					{$i18n.t('No chats in this space')}
				</div>
			{/if}
		</div>
	{/if}
</div>
