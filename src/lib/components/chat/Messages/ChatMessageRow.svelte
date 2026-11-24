<script lang="ts">
	import { getContext } from 'svelte';
	import type { AppLayoutContext } from '$lib/types';

	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Markdown from './Markdown.svelte';

	const i18n = getContext<any>('i18n');
	const appLayout = getContext<AppLayoutContext | undefined>('appLayout');

	export let content: string;

	let expanded: Record<number, boolean> = {};

	// Written by send_message; several read together share one message.
	$: messages = [
		...content.matchAll(
			/^<message from="([^"]*)" title="([^"]*)">\n([\s\S]*?)\n<\/message>(?=\n\n<message |$(?![\s\S]))/gm
		)
	].map(([, chatId, title, text]) => ({ chatId, title, text }));
</script>

<div class="w-full min-w-0 text-[0.90625rem]">
	{#each messages as message, index}
		<button
			type="button"
			class="group flex max-w-full min-w-0 items-center gap-1.5 py-0.5 text-left text-base-500 transition hover:text-base-700 dark:hover:text-base-300"
			aria-expanded={!!expanded[index]}
			on:click={() => (expanded[index] = !expanded[index])}
		>
			<span dir="auto" class="min-w-0 truncate">{message.title} · {message.text}</span>
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
						id={`message-${message.chatId}-${index}`}
						content={message.text}
						allowHtml={false}
						allowEmbeds={false}
					/>
				</div>
				{#if appLayout?.openPageTab}
					<button
						type="button"
						class="mt-1 text-xs text-base-400 transition hover:text-base-600 dark:text-base-600 dark:hover:text-base-400"
						on:click={() =>
							appLayout?.openPageTab?.({ href: `/c/${message.chatId}`, label: message.title })}
					>
						{$i18n.t('Open thread')}
					</button>
				{/if}
			</div>
		{/if}
	{/each}
</div>
