<script lang="ts">
	export let used = 0;
	export let total = 0;
	export let resetDate = '';

	$: percentage = total > 0 ? Math.round((used / total) * 100) : 0;
	$: daysLeft = resetDate
		? Math.max(
				0,
				Math.ceil((new Date(resetDate).getTime() - Date.now()) / (1000 * 60 * 60 * 24))
			)
		: 0;
</script>

<div class="p-5 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
	<h3 class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">Uso de tokens</h3>

	<div class="flex items-end justify-between mb-2">
		<span class="text-2xl font-bold text-gray-900 dark:text-white">
			{used.toLocaleString()}
		</span>
		<span class="text-sm text-gray-500 dark:text-gray-400">
			de {total.toLocaleString()}
		</span>
	</div>

	<!-- Progress bar -->
	<div class="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden mb-2">
		<div
			class="h-full rounded-full transition-all duration-500 {percentage > 90
				? 'bg-red-500'
				: percentage > 70
					? 'bg-yellow-500'
					: 'bg-claw-500'}"
			style="width: {percentage}%"
		/>
	</div>

	<div class="flex justify-between text-xs text-gray-500 dark:text-gray-400">
		<span>{percentage}% usado</span>
		{#if daysLeft > 0}
			<span>Se renueva en {daysLeft} dias</span>
		{/if}
	</div>
</div>
