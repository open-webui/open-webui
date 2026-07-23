<script lang="ts">
	export let title = '';
	export let first = false;
	export let className = '';
</script>

<section class="{first ? '' : 'mt-5'} {className}">
	{#if title}
		<h3 class="mb-2 text-xs text-gray-400 dark:text-gray-600">
			{title}
		</h3>
	{/if}

	<div class="flex flex-col gap-2.5">
		<slot />
	</div>
</section>
