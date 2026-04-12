<script lang="ts">
	import Info from '$lib/components/icons/Info.svelte';

	export let content = '';
	export let onRetryWithoutProvider: (() => void) | null = null;
	let showRaw = false;
</script>

<div class="flex flex-col my-2 gap-2.5 border px-4 py-3 border-red-600/10 bg-red-600/10 rounded-lg">
	<div class="flex gap-2.5">
		<div class=" self-start mt-0.5">
			<Info className="size-5 text-red-700 dark:text-red-400" />
		</div>

		<div class=" self-center text-sm">
			{#if typeof content === 'string'}
				{content}
			{:else if typeof content === 'object' && content !== null}
				{#if content?.error && content?.error?.message}
					{content.error.message}
				{:else if content?.detail}
					{content.detail}
				{:else if content?.message}
					{content.message}
				{:else}
					{JSON.stringify(content)}
				{/if}
			{:else}
				{JSON.stringify(content)}
			{/if}
		</div>
	</div>

	<div class="flex items-center gap-2 ml-auto">
		{#if onRetryWithoutProvider}
			<button
				class="text-xs px-3 py-1.5 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition font-medium text-gray-700 dark:text-gray-300"
				on:click={onRetryWithoutProvider}
			>
				Retry without provider restrictions
			</button>
		{/if}
		<button
			class="text-xs text-red-700 dark:text-red-400 underline"
			on:click={() => (showRaw = !showRaw)}
		>
			{showRaw ? 'Hide' : 'Show'} Raw
		</button>
	</div>

	{#if showRaw}
		<pre
			class="text-xs text-red-700 dark:text-red-400 whitespace-pre-wrap break-words mt-2 p-2 bg-red-600/5 rounded-sm">
			{JSON.stringify(content, null, 2)}
		</pre>
	{/if}
</div>
