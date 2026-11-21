<script lang="ts">
	import { getContext } from 'svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import EditPencilIcon from '$lib/components/layout/Sidebar/icons/EditPencil.svelte';
	import EmbeddedChatHistoryItem from './EmbeddedChatHistoryItem.svelte';
	import { getChatContext } from '$lib/components/chat/context';

	const { chatId } = getChatContext();

	const i18n = getContext('i18n');

	export let title = '';
	export let chats = [];
	export let canCreateNew = false;
	export let loading = false;

	export let onNewChat: (() => void | Promise<void>) | null = null;
	export let onSelectChat: ((chatId: string) => void | Promise<void>) | null = null;
	export let onDeleteChat: ((chatId: string) => void | Promise<void>) | null = null;

	let show = false;
	let optionsChatId = '';
	let deletingChatId = '';
</script>

<Dropdown
	bind:show
	align="start"
	sideOffset={6}
	closeOnOutsideClick={optionsChatId === ''}
	onOpenChange={(state) => {
		if (!state) optionsChatId = '';
	}}
>
	<button
		type="button"
		class="group flex min-w-0 items-center gap-1 text-[0.8125rem] font-normal text-base-600 transition hover:text-base-900 dark:text-base-300 dark:hover:text-base-0"
		aria-label={$i18n.t('Chat history')}
	>
		<span class="min-w-0 truncate">{title}</span>
		<ChevronRight
			className="size-3.5 shrink-0 text-base-400/70 opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100 dark:text-base-500/70"
			strokeWidth="2"
		/>
	</button>

	<div slot="content">
		<DropdownMenu className="min-w-56 max-w-72 max-h-80 overflow-y-auto scrollbar-hidden">
			{#if canCreateNew && !loading}
				<button
					type="button"
					class="text-left"
					on:click={async () => {
						show = false;
						await onNewChat?.();
					}}
				>
					<EditPencilIcon className="size-3.5" strokeWidth="1.5" />
					<span class="min-w-0 truncate">{$i18n.t('New chat')}</span>
				</button>
				<hr class="border-base-100/70 dark:border-base-800/60" />
			{/if}

			{#if chats.length > 0}
				{#each chats as item}
					<EmbeddedChatHistoryItem
						{item}
						title={item?.id === $chatId
							? title
							: item?.title || item?.chat?.title || $i18n.t('Chat')}
						selected={item.id === $chatId}
						deleting={deletingChatId === item.id}
						onSelect={async () => {
							show = false;
							await onSelectChat?.(item.id);
						}}
						onDelete={async (id) => {
							if (!id || deletingChatId) return;

							deletingChatId = id;
							optionsChatId = '';
							try {
								await onDeleteChat?.(id);
							} finally {
								deletingChatId = '';
							}
						}}
						onMenuOpenChange={(id, state) => {
							optionsChatId = state ? id : '';
						}}
					/>
				{/each}
			{:else}
				<div class="px-2 py-1.5 text-[0.8125rem] text-base-400 dark:text-base-500">
					{$i18n.t('No chat history')}
				</div>
			{/if}
		</DropdownMenu>
	</div>
</Dropdown>
