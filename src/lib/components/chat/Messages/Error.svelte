<script lang="ts">
	import Info from '$lib/components/icons/Info.svelte';

	export let content = '';
</script>

<div class="flex my-2 gap-2.5 border px-4 py-3 border-red-600/10 bg-red-600/10 rounded-lg">
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
