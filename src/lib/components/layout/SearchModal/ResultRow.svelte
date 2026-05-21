<script lang="ts">
	import { getContext } from 'svelte';
	import dayjs from '$lib/dayjs';
	import { sanitizeMarkSnippet } from '$lib/utils';
	import ArchiveBox from '$lib/components/icons/ArchiveBox.svelte';
	import type { ChatSearchHit } from '$lib/apis/chats';

	const i18n = getContext('i18n');

	export let hit: ChatSearchHit;
	export let selected: boolean = false;

	$: snippetHtml = sanitizeMarkSnippet(hit.snippet);
	$: roleLabel =
		hit.matched_role === 'user'
			? $i18n.t('You')
			: hit.matched_role === 'assistant'
				? $i18n.t('Assistant')
				: '';
</script>

<a
	class="w-full flex flex-col rounded-xl px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-850 {selected
		? 'bg-gray-50 dark:bg-gray-850'
		: ''}"
	href="/c/{hit.id}"
	draggable="false"
	on:click
	on:mouseenter
	data-arrow-selected={selected ? 'true' : undefined}
>
	<div class="flex items-center justify-between gap-3">
		<div class="text-sm font-medium text-gray-900 dark:text-gray-100 line-clamp-1 flex-1">
			{hit.title || $i18n.t('New Chat')}
		</div>
		<div class="shrink-0 text-xs text-gray-500 dark:text-gray-400">
			{dayjs(hit.updated_at * 1000).fromNow()}
		</div>
	</div>

	{#if snippetHtml}
		<div class="text-xs text-gray-600 dark:text-gray-400 mt-0.5 line-clamp-2">
			{#if roleLabel}
				<span class="font-medium text-gray-500 dark:text-gray-500">{roleLabel}:</span>
			{/if}
			{@html snippetHtml}
		</div>
	{/if}

	<div class="flex items-center gap-2 mt-1 text-[10px] text-gray-500 dark:text-gray-500">
		{#if hit.match_count > 1}
			<span class="px-1.5 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800">
				{hit.match_count} {$i18n.t('matches')}
			</span>
		{/if}
		{#if hit.archived}
			<span class="px-1.5 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center gap-1">
				<ArchiveBox className="size-2.5" strokeWidth="2" />
				{$i18n.t('Archived')}
			</span>
		{/if}
		{#if hit.pinned}
			<span class="px-1.5 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800">📌</span>
		{/if}
	</div>
</a>
