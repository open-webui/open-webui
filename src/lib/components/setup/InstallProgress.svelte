<script lang="ts">
	export let label: string;
	export let progress: number = 0; // 0-100
	export let message: string | undefined = undefined;

	$: progressClamped = Math.min(100, Math.max(0, progress));
</script>

<div class="px-4 py-3">
	<div class="flex items-center justify-between mb-2">
		<span class="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</span>
		<span class="text-sm text-gray-600 dark:text-gray-400">{Math.round(progressClamped)}%</span>
	</div>

	<!-- Progress Bar -->
	<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 overflow-hidden">
		<div
			class="bg-blue-600 dark:bg-blue-500 h-2.5 rounded-full transition-all duration-300 ease-out"
			style="width: {progressClamped}%"
		></div>
	</div>

	<!-- Optional Message -->
	{#if message}
		<p class="text-xs text-gray-500 dark:text-gray-400 mt-2">
			{message}
		</p>
	{/if}
</div>
