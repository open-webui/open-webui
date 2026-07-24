<script lang="ts">
	export let title = '';
	export let first = false;
	export let className = '';
</script>

<section class="w-full {first ? '' : 'mt-4'} {className}">
	{#if title}
		<h3 class="mb-2 flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400">
			{title}
			<slot name="suffix" />
		</h3>
	{/if}

	<div class="flex flex-col gap-2.5">
		<slot />
	</div>
</section>
