<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { createAppInteraction } from '$lib/apis/apps';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	export let appId: string;
	export let channelId: string;
	export let reply: {
		type?: string;
		title?: string;
		content?: string;
		filename?: string;
		actions?: { action_id: string; label: string }[];
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

<div class="space-y-3 text-sm" aria-busy={busy}>
	{#if reply?.title}<h3 class="font-medium">{reply.title}</h3>{/if}
	{#if reply?.content}<Markdown content={reply.content} allowEmbeds={false} />{/if}
	{#if reply?.type === 'error'}<p role="alert">The app could not complete this operation.</p>{/if}
	{#if error}<p role="alert" class="text-red-600">{error}</p>{/if}
	{#if reply?.type === 'download'}<button
			class="focus-ring flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-gray-900 px-2.5 text-xs font-normal text-white transition hover:bg-black disabled:opacity-60 dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white"
			on:click={download}>Download {reply.filename}</button
		>{/if}
	{#if reply?.actions?.length}
		<div class="flex flex-wrap items-center gap-1.5">
			{#each reply.actions as item, index}
				<button
					type="button"
					disabled={busy}
					class="focus-ring flex h-7 max-w-full shrink-0 items-center justify-center gap-1.5 rounded-lg px-2.5 text-xs font-normal transition disabled:cursor-not-allowed disabled:opacity-60 {index ===
					0
						? 'bg-gray-900 text-white hover:bg-black dark:bg-gray-100 dark:text-gray-900 dark:hover:bg-white'
						: 'hover:bg-gray-100 dark:hover:bg-gray-850'}"
					on:click={() => action(item.action_id)}>{item.label}</button
				>
			{/each}
		</div>
	{/if}
</div>
