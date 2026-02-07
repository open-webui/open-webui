<script lang="ts">
	export let title: string;
	export let value: string | number;
	export let icon: string | undefined = undefined;
</script>

<div class="stat-card p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
	<div class="flex items-start justify-between">
		<div class="flex-1">
			<h3 class="text-sm text-gray-500 dark:text-gray-400">
				{title}
			</h3>
			<p class="text-2xl font-bold text-gray-900 dark:text-white mt-2">
				{value}
			</p>
		</div>
		{#if icon}
			<div class="text-gray-400 dark:text-gray-500">
				{@html icon}
			</div>
		{/if}
	</div>
</div>
