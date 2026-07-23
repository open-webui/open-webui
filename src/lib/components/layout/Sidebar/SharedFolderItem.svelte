<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import type { Writable } from 'svelte/store';

	const i18n: Writable<any> = getContext('i18n');
	const dispatch = createEventDispatcher();

	import { goto } from '$app/navigation';
	import { chatId, mobile, showSidebar } from '$lib/stores';
	import { getSharedFolderChats } from '$lib/apis/folders';

	import ChatItem from './ChatItem.svelte';
	import Collapsible from '../../common/Collapsible.svelte';
	import ChevronDown from './icons/ChevronDown.svelte';
	import ChevronRight from './icons/ChevronRight.svelte';
	import Eye from './icons/Eye.svelte';
	import FolderIcon from './icons/Folder.svelte';

	export let folder: any;
	export let allSharedFolders: any[] = [];
	export let className = '';

	const SIDEBAR_CHATS_PAGE_SIZE = 10;
	let expanded = false;
	let chats: any[] = [];
	let loading = false;
	let loaded = false;
	let page = 1;
	let hasMoreChats = false;

	$: children = allSharedFolders.filter((f) => f.parent_id === folder.id);
	$: permission = folder.permission || 'read';
	$: isWritable = permission === 'write';

	const toggleExpand = async () => {
		expanded = !expanded;
		if (expanded && !loaded) {
			await loadChats();
		}
	};

	const loadChats = async (append = false) => {
		if (loading) {
			return;
		}

		loading = true;
		try {
			const nextPage = append ? page + 1 : 1;
			const res = await getSharedFolderChats(localStorage.token, folder.id, {
				page: nextPage
			});
			if (res) {
				const nextChats = res.chats || [];
				chats = append ? [...chats, ...nextChats] : nextChats;
				page = nextPage;
				hasMoreChats = res.has_more ?? nextChats.length === SIDEBAR_CHATS_PAGE_SIZE;
			}
		} catch (e) {
			console.error('Failed to load shared folder chats', e);
			chats = [];
			hasMoreChats = false;
		} finally {
			loading = false;
			loaded = true;
		}
	};
</script>

<div class={className}>
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div class="w-full group">
		<button
			class="w-full py-1 flex items-center gap-1 text-xs text-left font-normal
				text-gray-600 dark:text-gray-400
				hover:text-gray-800 dark:hover:text-gray-300
				transition-colors duration-100 cursor-pointer"
			on:click={toggleExpand}
		>
			<div class="shrink-0">
				{#if expanded}
					<ChevronDown className="size-3" strokeWidth="1.5" />
				{:else}
					<ChevronRight className="size-3" strokeWidth="1.5" />
				{/if}
			</div>

			<FolderIcon className="size-3.5 shrink-0" strokeWidth="1.5" />

			<div class="flex-1 truncate">
				{folder.name}
			</div>

			{#if folder.owner_name}
				<div class="shrink-0 text-[10px] text-gray-400 dark:text-gray-600 pr-1">
					{folder.owner_name}
				</div>
			{/if}

			{#if !isWritable}
				<div class="shrink-0 text-[10px] text-gray-400 dark:text-gray-600" title="Read only">
					<Eye className="size-3" />
				</div>
			{/if}
		</button>
	</div>

	{#if expanded}
		<div class="pl-3">
			{#if loading && !loaded}
				<div class="flex gap-1 px-2 py-1.5" aria-label="Loading">
					<span class="size-1 rounded-full bg-gray-400 animate-pulse dark:bg-gray-600"></span>
					<span
						class="size-1 rounded-full bg-gray-400 animate-pulse [animation-delay:150ms] dark:bg-gray-600"
					></span>
					<span
						class="size-1 rounded-full bg-gray-400 animate-pulse [animation-delay:300ms] dark:bg-gray-600"
					></span>
				</div>
			{:else}
				{#each chats as chat (chat.id)}
					<ChatItem
						id={chat.id}
						title={chat.title}
						createdAt={chat.created_at}
						updatedAt={chat.updated_at}
						active={chat.active ?? false}
						ownerName={chat.owner_name}
						ownerUserId={chat.user_id}
						readonly={chat.readonly ?? !isWritable}
					/>
				{/each}

				{#each children as child (child.id)}
					<svelte:self folder={child} {allSharedFolders} />
				{/each}

				{#if hasMoreChats}
					<button
						class="w-full px-2 py-0.5 text-left text-[11px] text-gray-400 transition hover:text-gray-700 disabled:cursor-not-allowed dark:text-gray-600 dark:hover:text-gray-300"
						disabled={loading}
						on:click={() => loadChats(true)}
					>
						{#if loading}
							<div class="flex gap-1 px-2 py-1.5" aria-label="Loading">
								<span class="size-1 rounded-full bg-gray-400 animate-pulse dark:bg-gray-600"></span>
								<span
									class="size-1 rounded-full bg-gray-400 animate-pulse [animation-delay:150ms] dark:bg-gray-600"
								></span>
								<span
									class="size-1 rounded-full bg-gray-400 animate-pulse [animation-delay:300ms] dark:bg-gray-600"
								></span>
							</div>
						{:else}
							{$i18n.t('Show more')}
						{/if}
					</button>
				{/if}

				{#if chats.length === 0 && children.length === 0 && !hasMoreChats}
					<div class="text-[11px] text-gray-400 dark:text-gray-600 py-1 px-2">
						{$i18n.t('Empty')}
					</div>
				{/if}
			{/if}
		</div>
	{/if}
</div>
