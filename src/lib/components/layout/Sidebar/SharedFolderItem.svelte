<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import { goto } from '$app/navigation';
	import { chatId, mobile, showSidebar } from '$lib/stores';
	import { getSharedFolderChats } from '$lib/apis/folders';

	import ChatItem from './ChatItem.svelte';
	import Collapsible from '../../common/Collapsible.svelte';
	import ChevronDown from '../../icons/ChevronDown.svelte';
	import ChevronRight from '../../icons/ChevronRight.svelte';
	import FolderOpen from '$lib/components/icons/FolderOpen.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	export let folder: any;
	export let allSharedFolders: any[] = [];
	export let className = '';

	let expanded = false;
	let chats: any[] = [];
	let loading = false;
	let loaded = false;

	$: children = allSharedFolders.filter((f) => f.parent_id === folder.id);
	$: permission = folder.permission || 'read';
	$: isWritable = permission === 'write';

	const toggleExpand = async () => {
		expanded = !expanded;
		if (expanded && !loaded) {
			await loadChats();
		}
	};

	const loadChats = async () => {
		loading = true;
		try {
			const res = await getSharedFolderChats(localStorage.token, folder.id);
			if (res) {
				chats = res.chats || [];
			}
		} catch (e) {
			console.error('Failed to load shared folder chats', e);
			chats = [];
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
			class="w-full py-1 flex items-center gap-1 text-xs text-left font-medium
				text-gray-600 dark:text-gray-400
				hover:text-gray-900 dark:hover:text-gray-200
				transition-colors duration-100 cursor-pointer"
			on:click={toggleExpand}
		>
			<div class="shrink-0">
				{#if expanded}
					<ChevronDown className="size-3" strokeWidth="2.5" />
				{:else}
					<ChevronRight className="size-3" strokeWidth="2.5" />
				{/if}
			</div>

			<FolderOpen className="size-3.5 shrink-0" strokeWidth="2" />

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
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="1.5"
						stroke="currentColor"
						class="size-3"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z"
						/>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
						/>
					</svg>
				</div>
			{/if}
		</button>
	</div>

	{#if expanded}
		<div class="pl-3">
			{#if loading}
				<div class="flex items-center gap-1.5 py-1 px-2 text-xs text-gray-400">
					<Spinner className="size-3" />
					<span>{$i18n.t('Loading...')}</span>
				</div>
			{:else}
				{#each chats as chat (chat.id)}
					<ChatItem
						id={chat.id}
						title={chat.title}
						createdAt={chat.created_at}
						updatedAt={chat.updated_at}
						ownerName={chat.owner_name}
						ownerUserId={chat.user_id}
						readonly={chat.readonly ?? !isWritable}
					/>
				{/each}

				{#each children as child (child.id)}
					<svelte:self folder={child} {allSharedFolders} />
				{/each}

				{#if chats.length === 0 && children.length === 0}
					<div class="text-[11px] text-gray-400 dark:text-gray-600 py-1 px-2">
						{$i18n.t('Empty')}
					</div>
				{/if}
			{/if}
		</div>
	{/if}
</div>
