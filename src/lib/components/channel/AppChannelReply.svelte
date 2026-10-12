<script lang="ts">
	import { createEventDispatcher, onDestroy, onMount } from 'svelte';
	import { getAppOperationById, createAppInteraction } from '$lib/apis/apps';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	export let appId: string;
	export let channelId: string;
	export let reply: any;
	export let source: any = null;
	const dispatch = createEventDispatcher();
	let busy = false,
		error = '';
	let timer: ReturnType<typeof setTimeout>;
	let disposed = false;
	let pollDelay = 1000;

	async function action(actionId: string) {
		busy = true;
		error = '';
		try {
			const result = await createAppInteraction(localStorage.token, appId, {
				message_id: source.id,
				action_id: actionId
			});
			if (result.visibility !== 'channel' || result.type === 'error') {
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
	async function poll() {
		if (disposed || reply?.type !== 'deferred') return;
		if (!document.hidden) {
			try {
				const result = await getAppOperationById(
					localStorage.token,
					appId,
					reply.operation_id,
					reply.receipt
				);
				if (disposed) return;
				reply = result;
			} catch (e) {
				error = String(e);
				return;
			}
		}
		pollDelay = Math.min(pollDelay + 1000, 5000);
		timer = setTimeout(poll, pollDelay);
	}
	function download() {
		const url = URL.createObjectURL(
			new Blob([reply.content], { type: 'text/markdown;charset=utf-8' })
		);
		const link = document.createElement('a');
		link.href = url;
		link.download = reply.filename;
		link.click();
		URL.revokeObjectURL(url);
	}
	onMount(() => {
		if (reply?.type === 'deferred') timer = setTimeout(poll, 1000);
	});
	onDestroy(() => {
		disposed = true;
		clearTimeout(timer);
	});
</script>

<div class="space-y-3 text-sm" aria-busy={busy}>
	{#if reply?.title}<h3 class="font-medium">{reply.title}</h3>{/if}
	{#if reply?.content}<Markdown content={reply.content} allowEmbeds={false} />{/if}
	{#if reply?.type === 'error'}<p role="alert">
			The app could not complete this operation.
		</p>{/if}
	{#if error}<p role="alert" class="text-red-600">{error}</p>{/if}
	{#if reply?.type === 'deferred'}<p role="status" class="text-gray-500">Working…</p>{/if}
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
