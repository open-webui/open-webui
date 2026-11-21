<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import AppEmbed from './AppEmbed.svelte';
	import type { Embed } from '$lib/apis/apps';
	import { createAppInteraction } from '$lib/apis/apps';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	export let appId: string;
	export let channelId: string;
	export let reply: {
		type?: string;
		title?: string;
		content?: string;
		filename?: string;
		embeds?: Embed[];
		actions?: { action_id?: string; url?: string; label: string }[];
	};
	export let source: { id: string; user?: { name?: string } } | null = null;
	const dispatch = createEventDispatcher();
	let busy = false,
		error = '';

	async function action(actionId: string) {
		if (!source) return;
		busy = true;
		error = '';
		try {
			const result = await createAppInteraction(localStorage.token, appId, {
				message_id: source.id,
				action_id: actionId
			});
			if (result.type !== 'ack' && (result.visibility !== 'channel' || result.type === 'error')) {
				dispatch('reply', {
					app_id: appId,
					app_name: source.user?.name,
					channel_id: channelId,
					message_id: source.id,
					reply: result
				});
			}
		} catch (e) {
			error = String(e);
		} finally {
			busy = false;
		}
	}
	function download() {
		const url = URL.createObjectURL(
			new Blob([reply.content ?? ''], { type: 'text/markdown;charset=utf-8' })
		);
		const link = document.createElement('a');
		link.href = url;
		link.download = reply.filename ?? 'report.md';
		link.click();
		URL.revokeObjectURL(url);
	}
</script>

<div
	class="space-y-3 text-sm [&_h1]:text-sm [&_h2]:text-sm [&_h3]:text-sm [&_h4]:text-sm [&_h5]:text-sm [&_h6]:text-sm"
	aria-busy={busy}
>
	{#if reply?.title}<h3 class="font-medium">{reply.title}</h3>{/if}
	{#if reply?.content}<Markdown content={reply.content} allowEmbeds={false} />{/if}
	{#each reply.embeds ?? [] as embed}<AppEmbed {embed} />{/each}
	{#if reply?.type === 'error' && !reply?.content}<p role="alert">
			The app could not complete this operation.
		</p>{/if}
	{#if error}<p role="alert" class="text-red-600">{error}</p>{/if}
	{#if reply?.type === 'download'}<button
			class="focus-ring flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-base-900 px-2.5 text-xs font-normal text-base-0 transition hover:bg-base-1000 disabled:opacity-60 dark:bg-base-100 dark:text-base-900 dark:hover:bg-base-0"
			on:click={download}>Download {reply.filename}</button
		>{/if}
	{#if reply?.actions?.length}
		<div class="flex flex-wrap items-center gap-1.5">
			{#each reply.actions as item, index}
				{#if item.url}
					<a
						href={item.url}
						target="_blank"
						rel="noopener noreferrer"
						class="focus-ring inline-flex min-h-7 max-w-full items-center rounded-lg border border-base-200 px-2.5 text-xs hover:bg-base-100 dark:border-base-0/8 dark:hover:bg-base-850"
						>{item.label}</a
					>
				{:else if item.action_id}
					<button
						type="button"
						disabled={busy}
						class="focus-ring flex h-7 max-w-full shrink-0 items-center justify-center gap-1.5 rounded-lg px-2.5 text-xs font-normal transition disabled:cursor-not-allowed disabled:opacity-60 {index ===
						0
							? 'bg-base-900 text-base-0 hover:bg-base-1000 dark:bg-base-100 dark:text-base-900 dark:hover:bg-base-0'
							: 'hover:bg-base-100 dark:hover:bg-base-850'}"
						on:click={() => item.action_id && action(item.action_id)}>{item.label}</button
					>
				{/if}
			{/each}
		</div>
	{/if}
</div>
