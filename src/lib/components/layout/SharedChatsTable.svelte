<script lang="ts">
	import { getContext } from 'svelte';
	import dayjs from 'dayjs';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import calendar from 'dayjs/plugin/calendar';
	import ChevronUp from '../icons/ChevronUp.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';

	dayjs.extend(localizedFormat);
	dayjs.extend(calendar);

	const i18n = getContext('i18n');

	export let chatList: any[] = [];
	export let query = '';
	export let loading = false;
	export let page = 1;
	export let hasPrevPage = false;
	export let hasNextPage = false;

	export let orderBy = 'updated_at';
	export let direction = 'desc';
	export let selectedChatIds: Set<string> = new Set();

	export let onToggleSort: (key: string) => void = () => {};
	export let onToggleSelectAllPage: (checked: boolean) => void = () => {};
	export let onToggleSelectChat: (chatId: string, checked: boolean) => void = () => {};
	export let onPrevPage: () => void = () => {};
	export let onNextPage: () => void = () => {};
	export let onUnshareSingle: (chatId: string) => void = () => {};

	$: selectedOnPageCount = chatList.filter((chat) => selectedChatIds.has(chat.id)).length;
	$: allPageSelected = chatList.length > 0 && selectedOnPageCount === chatList.length;
	$: somePageSelected = selectedOnPageCount > 0 && !allPageSelected;
	let selectAllCheckboxEl: HTMLInputElement;
	$: if (selectAllCheckboxEl) {
		selectAllCheckboxEl.indeterminate = somePageSelected;
	}
	const getSortClass = (key: string) => (orderBy === key ? 'text-gray-900 dark:text-gray-50' : '');
</script>

<div class="w-full rounded-xl border border-gray-100 dark:border-gray-850 overflow-hidden">
	<div
		class="grid grid-cols-[auto_minmax(0,1fr)_9rem_9rem_4.5rem] items-center gap-3 px-4 py-3 text-xs font-medium border-b border-gray-100 dark:border-gray-850 bg-gray-50/50 dark:bg-gray-900/20"
	>
		<div class="self-center">
			<input
				bind:this={selectAllCheckboxEl}
				type="checkbox"
				checked={allPageSelected}
				aria-label={$i18n.t('Select all chats on current page')}
				on:change={(e) => onToggleSelectAllPage(e.currentTarget.checked)}
			/>
		</div>
		<button
			type="button"
			class="min-w-0 text-left flex items-center gap-1.5 select-none {getSortClass('title')}"
			on:click={() => onToggleSort('title')}
		>
			{$i18n.t('Title')}
			{#if orderBy === 'title'}
				{#if direction === 'asc'}
					<ChevronUp className="size-2" />
				{:else}
					<ChevronDown className="size-2" />
				{/if}
			{/if}
		</button>
		<button
			type="button"
			class="shrink-0 whitespace-nowrap text-right flex items-center justify-end gap-1.5 select-none {getSortClass('updated_at')}"
			on:click={() => onToggleSort('updated_at')}
		>
			{$i18n.t('Updated at')}
			{#if orderBy === 'updated_at'}
				{#if direction === 'asc'}
					<ChevronUp className="size-2" />
				{:else}
					<ChevronDown className="size-2" />
				{/if}
			{/if}
		</button>
		<button
			type="button"
			class="shrink-0 whitespace-nowrap text-right flex items-center justify-end gap-1.5 select-none {getSortClass('created_at')}"
			on:click={() => onToggleSort('created_at')}
		>
			{$i18n.t('Created at')}
			{#if orderBy === 'created_at'}
				{#if direction === 'asc'}
					<ChevronUp className="size-2" />
				{:else}
					<ChevronDown className="size-2" />
				{/if}
			{/if}
		</button>
		<div class="shrink-0 whitespace-nowrap text-right">{$i18n.t('Action')}</div>
	</div>

	<div class="max-h-[24rem] overflow-y-auto">
		{#if loading}
			<div class="py-10 text-center text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Loading...')}</div>
		{:else if chatList.length === 0}
			<div class="py-10 text-center text-sm text-gray-500 dark:text-gray-400">
				{#if query}
					{$i18n.t('No shared chats match your search.')}
				{:else}
					{$i18n.t('You have no shared conversations.')}
				{/if}
			</div>
		{:else}
			{#each chatList as chat (chat.id)}
				<div
					class="grid grid-cols-[auto_minmax(0,1fr)_9rem_9rem_4.5rem] items-center gap-3 px-4 py-3 text-sm border-b border-gray-50 dark:border-gray-850/70 last:border-b-0 hover:bg-gray-50/70 dark:hover:bg-gray-900/30 {selectedChatIds.has(chat.id)
						? 'bg-gray-50 dark:bg-gray-900/40'
						: ''}"
				>
					<div class="self-center">
						<input
							type="checkbox"
							checked={selectedChatIds.has(chat.id)}
							aria-label={$i18n.t('Select this chat')}
							on:change={(e) => onToggleSelectChat(chat.id, e.currentTarget.checked)}
						/>
					</div>
					<a class="min-w-0 self-center hover:underline" href="/c/{chat.id}">
						<div class="truncate">{chat.title || $i18n.t('Untitled')}</div>
					</a>
					<div class="text-xs text-right text-gray-500 dark:text-gray-400 self-center">
						{dayjs(chat.updated_at * 1000).format('LLL')}
					</div>
					<div class="text-xs text-right text-gray-500 dark:text-gray-400 self-center">
						{dayjs(chat.created_at * 1000).format('LLL')}
					</div>
					<div class="text-right self-center">
						<button class="text-xs px-2 py-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-850" on:click={() => onUnshareSingle(chat.id)}>
							{$i18n.t('Unshare')}
						</button>
					</div>
				</div>
			{/each}
		{/if}
	</div>

	<div class="flex items-center justify-between px-4 py-2.5 text-xs border-t border-gray-100 dark:border-gray-850 bg-gray-50/50 dark:bg-gray-900/20">
		<div class="text-gray-500 dark:text-gray-400">
			{#if $i18n.language === 'zh-CN'}
				第 {page} 页
			{:else}
				{$i18n.t('Page')} {page}
			{/if}
			| {$i18n.t('Selected on this page')}: {selectedOnPageCount}
		</div>
		<div class="flex items-center gap-2">
			<button
				class="px-2.5 py-1 rounded-md border border-gray-200 dark:border-gray-800 disabled:opacity-50"
				disabled={!hasPrevPage || loading}
				on:click={onPrevPage}
			>
				{$i18n.t('Previous')}
			</button>
			<button
				class="px-2.5 py-1 rounded-md border border-gray-200 dark:border-gray-800 disabled:opacity-50"
				disabled={!hasNextPage || loading}
				on:click={onNextPage}
			>
				{$i18n.t('Next')}
			</button>
		</div>
	</div>
</div>
