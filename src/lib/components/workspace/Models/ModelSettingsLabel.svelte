<script lang="ts">
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	export let label = '';
	export let description = '';
</script>

{#if description}
	<Tooltip
		as="span"
		className="inline-flex w-fit max-w-full"
		content={description}
		allowHTML={false}
	>
		<span
			class="cursor-help underline decoration-dotted decoration-gray-400/70 underline-offset-4 dark:decoration-gray-500"
			>{label}</span
		>
	</Tooltip>
{:else}
	<span>{label}</span>
{/if}
