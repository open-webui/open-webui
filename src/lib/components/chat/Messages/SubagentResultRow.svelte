<script lang="ts">
	import { getContext } from 'svelte';
	import type { Readable } from 'svelte/store';

	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';

	type SubagentResult = {
		delegation_id?: string;
		delegation_ids?: string[];
		subagent_chat_id?: string;
		subagent_chat_ids?: string[];
	};

	const i18n = getContext<Readable<{ t: (value: string) => string }>>('i18n');

	export let content: string;
	export let result: SubagentResult;

	let expanded = false;
	$: delegationIds = Array.isArray(result.delegation_ids) ? result.delegation_ids : [];
	$: delegationLabel =
		result.delegation_id ?? (delegationIds.length > 1 ? `${delegationIds.length} tasks` : '');
	$: summary = (() => {
		const line = content
			.split('\n')
			.map((value) => value.trim())
			.find((value) => value && !value.startsWith('['));
		if (!line) return delegationLabel;
		return line.length > 96 ? `${line.slice(0, 96)}...` : line;
	})();
</script>

<div class="w-full min-w-0 pb-1">
	<button
		type="button"
		class="w-full min-w-0 flex items-center gap-2 text-left text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
		aria-expanded={expanded}
		on:click={() => (expanded = !expanded)}
	>
		<span class="w-1.5 h-1.5 rounded-full bg-gray-300 dark:bg-gray-600 shrink-0"></span>
		<span class="text-[0.75rem] font-normal shrink-0">
			{$i18n.t('Background sub-agent finished')}
		</span>
		{#if summary}
			<span class="text-[0.75rem] truncate min-w-0 flex-1">{summary}</span>
		{/if}
		{#if delegationLabel}
			<span
				class="hidden sm:inline text-[0.6875rem] font-mono text-gray-400 dark:text-gray-600 shrink-0"
			>
				{delegationLabel}
			</span>
		{/if}
		<ChevronDown
			className="size-3 text-gray-400 dark:text-gray-600 shrink-0 transition-transform duration-150 {expanded
				? 'rotate-180'
				: ''}"
		/>
	</button>
	{#if expanded}
		<div
			class="mt-2 ml-3 border-l border-gray-100 dark:border-white/8 pl-3 text-[0.78125rem] leading-relaxed text-gray-600 dark:text-gray-400 whitespace-pre-wrap break-words"
		>
			{content}
		</div>
	{/if}
</div>
