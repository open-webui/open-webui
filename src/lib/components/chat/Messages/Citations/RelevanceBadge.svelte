<script lang="ts">
	export let distance: number | null | undefined;
	export let showPercentage = false;

	function calculatePercentage(distance: number | null | undefined) {
		if (typeof distance !== 'number') return null;
		if (distance < 0) return 0;
		if (distance > 1) return 100;
		return Math.round(distance * 10000) / 100;
	}

	function getRelevanceColor(percentage: number) {
		if (percentage >= 80)
			return 'bg-green-200 dark:bg-green-800 text-green-800 dark:text-green-200';
		if (percentage >= 60)
			return 'bg-yellow-200 dark:bg-yellow-800 text-yellow-800 dark:text-yellow-200';
		if (percentage >= 40)
			return 'bg-orange-200 dark:bg-orange-800 text-orange-800 dark:text-orange-200';
		return 'bg-red-200 dark:bg-red-800 text-red-800 dark:text-red-200';
	}
</script>

{#if showPercentage}
	{@const percentage = calculatePercentage(distance)}

	{#if typeof percentage === 'number'}
		<span class={`px-1 rounded-sm font-normal ${getRelevanceColor(percentage)}`}>
			{percentage.toFixed(2)}%
		</span>
	{/if}
{:else if typeof distance === 'number'}
	<span class="text-base-500 dark:text-base-500">
		({distance.toFixed(4)})
	</span>
{/if}
