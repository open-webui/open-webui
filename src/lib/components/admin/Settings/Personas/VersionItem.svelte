<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import type { PromptVersion } from '$lib/apis/prompt-groups';

	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let version: PromptVersion;
	export let isCurrent: boolean;
	export let expanded: boolean = false;

	const formatDate = (isoString: string): string => {
		try {
			const date = new Date(isoString);
			const year = date.getFullYear();
			const month = String(date.getMonth() + 1).padStart(2, '0');
			const day = String(date.getDate()).padStart(2, '0');
			const hours = String(date.getHours()).padStart(2, '0');
			const minutes = String(date.getMinutes()).padStart(2, '0');
			return `${year}-${month}-${day} ${hours}:${minutes}`;
		} catch {
			return isoString;
		}
	};

	const truncateContent = (content: string, maxLength: number = 200): string => {
		if (content.length <= maxLength) return content;
		return content.slice(0, maxLength) + '...';
	};

	const handleRollback = () => {
		dispatch('rollback', version.version);
	};

	const toggleExpand = () => {
		dispatch('toggle', version.version);
	};
</script>

<div
	class="border-b last:border-b-0 dark:border-gray-700 p-4 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition"
>
	<!-- Header -->
	<div class="flex items-center justify-between mb-3">
		<div class="flex items-center gap-2">
			<span class="text-sm font-medium text-gray-900 dark:text-white">
				v{version.version}
			</span>
			{#if isCurrent}
				<span
					class="text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 font-medium"
				>
					현재 버전
				</span>
			{/if}
		</div>
		<div class="flex items-center gap-3">
			<span class="text-xs text-gray-500 dark:text-gray-400">
				{formatDate(version.updated_at || version.created_at)}
			</span>
			{#if !isCurrent}
				<button
					on:click={handleRollback}
					class="px-3 py-1.5 text-xs font-medium bg-amber-600 hover:bg-amber-700 text-white rounded-md transition"
				>
					복원
				</button>
			{/if}
		</div>
	</div>

	<!-- Content Preview/Full -->
	{#if !expanded}
		<p class="text-sm text-gray-600 dark:text-gray-300 whitespace-pre-wrap line-clamp-3 mb-2">
			{truncateContent(version.content)}
		</p>
	{:else}
		<textarea
			readonly
			value={version.content}
			class="w-full min-h-40 p-3 font-mono text-xs bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-md resize-y text-gray-800 dark:text-gray-200 mb-2"
		></textarea>
	{/if}

	<!-- Toggle Button -->
	{#if version.content.length > 200}
		<button
			on:click={toggleExpand}
			class="text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 font-medium"
		>
			{expanded ? '접기' : '더보기'}
		</button>
	{/if}
</div>
