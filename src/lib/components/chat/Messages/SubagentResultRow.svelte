<script lang="ts">
	import { getContext } from 'svelte';
	import type { Readable } from 'svelte/store';
	import type { AppLayoutContext } from '$lib/types';

	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Markdown from './Markdown.svelte';

	const i18n = getContext<Readable<{ t: (value: string) => string }>>('i18n');
	const appLayout = getContext<AppLayoutContext | undefined>('appLayout');

	export let content: string;

	let expanded: Record<number, boolean> = {};

	// The report written by subagents.py; several that finished together share one message.
	$: reports = content
		.split(/^\[ASYNC SUBAGENT COMPLETE - .*\]$/m)
		.filter((report) => report.trim())
		.map((report) => {
			const [head, ...result] = report.split('--- RESULT ---');
			const field = (pattern: RegExp) => head.match(pattern)?.[1]?.trim() ?? '';
			return {
				title: field(/^Title: (.*)\nOriginal task: /m) || field(/^Original task: (.*)$/m),
				chatId: field(/^Subagent chat: (.*)$/m),
				status: field(/^Status: (\S+)/m),
				duration: field(/Duration: (\S+)/),
				result: (result.length ? result.join('--- RESULT ---') : head).trim()
			};
		});

	const label = (status: string) =>
		({
			completed: $i18n.t('Sub-agent finished'),
			interrupted: $i18n.t('Sub-agent stopped')
		})[status] ?? $i18n.t('Sub-agent failed');
</script>

<div class="w-full min-w-0 text-[0.90625rem]">
	{#each reports as report, index}
		<button
			type="button"
			class="group flex max-w-full min-w-0 items-center gap-1.5 py-0.5 text-left text-base-500 transition hover:text-base-700 dark:hover:text-base-300"
			aria-expanded={!!expanded[index]}
			on:click={() => (expanded[index] = !expanded[index])}
		>
			<span dir="auto" class="min-w-0 truncate">{label(report.status)} · {report.title}</span>
			<span class="shrink-0 text-xs tabular-nums">{report.duration}</span>
			<ChevronDown
				strokeWidth="3.5"
				className="size-3 shrink-0 transition {expanded[index]
					? 'rotate-180'
					: 'opacity-0 group-hover:opacity-100 group-focus-visible:opacity-100'}"
			/>
		</button>
		{#if expanded[index]}
			<div
				class="my-1 border-l border-base-100 pl-2.5 text-base-500 dark:border-base-800 dark:text-base-400"
			>
				<div class="markdown-prose-xs max-w-none break-words">
					<Markdown
						id={`subagent-${report.chatId}`}
						content={report.result}
						allowHtml={false}
						allowEmbeds={false}
					/>
				</div>
				{#if report.chatId && appLayout?.openPageTab}
					<button
						type="button"
						class="mt-1 text-xs text-base-400 transition hover:text-base-600 dark:text-base-600 dark:hover:text-base-400"
						on:click={() =>
							appLayout?.openPageTab?.({ href: `/c/${report.chatId}`, label: report.title })}
					>
						{$i18n.t('Open thread')}
					</button>
				{/if}
			</div>
		{/if}
	{/each}
</div>
