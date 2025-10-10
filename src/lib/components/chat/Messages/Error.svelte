<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import Info from '$lib/components/icons/Info.svelte';

	const dispatch = createEventDispatcher();

	export let content = '';
	export let canRetry = false;
</script>

<div class="flex my-2 gap-2.5 border px-4 py-3 border-red-600/10 bg-red-600/10 rounded-lg">
	<div class=" self-start mt-0.5">
		<Info className="size-5 text-red-700 dark:text-red-400" />
	</div>

	<div class="flex-1 self-center text-sm">
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

	{#if canRetry}
		<div class="self-center">
			<button
				class="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-sm rounded-md transition-colors"
				on:click={() => dispatch('retry')}
			>
				Retry
			</button>
		</div>
	{/if}
</div>
