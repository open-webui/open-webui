<script lang="ts">
	import type { CheckStatus } from '$lib/stores/setup';

	export let label: string;
	export let status: CheckStatus = 'pending';
	export let error: string | undefined = undefined;
</script>

<div class="flex items-center gap-3 py-2 px-4">
	<!-- Status Icon -->
	<div class="flex-shrink-0 w-6 h-6">
		{#if status === 'pending'}
			<div class="w-5 h-5 rounded-full border-2 border-gray-300 dark:border-gray-600"></div>
		{:else if status === 'running'}
			<div class="w-5 h-5 relative">
				<svg class="animate-spin h-5 w-5 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
					<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
				</svg>
			</div>
		{:else if status === 'success'}
			<div class="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center">
				<svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path>
				</svg>
			</div>
		{:else if status === 'skipped'}
			<div class="w-5 h-5 rounded-full bg-gray-400 dark:bg-gray-600 flex items-center justify-center">
				<svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M9 5l7 7-7 7"></path>
				</svg>
			</div>
		{:else if status === 'error'}
			<div class="w-5 h-5 rounded-full bg-red-500 flex items-center justify-center">
				<svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M6 18L18 6M6 6l12 12"></path>
				</svg>
			</div>
		{/if}
	</div>

	<!-- Label and Error -->
	<div class="flex-1 min-w-0">
		<p class="text-sm font-medium text-gray-900 dark:text-gray-100">
			{label}
		</p>
		{#if error}
			<p class="text-xs text-red-600 dark:text-red-400 mt-1 truncate" title={error}>
				{error}
			</p>
		{/if}
	</div>

	<!-- Status Text -->
	<div class="flex-shrink-0">
		{#if status === 'running'}
			<span class="text-xs text-blue-500 dark:text-blue-400">Running...</span>
		{:else if status === 'success'}
			<span class="text-xs text-green-600 dark:text-green-400">Done</span>
		{:else if status === 'skipped'}
			<span class="text-xs text-gray-500 dark:text-gray-400">Skipped</span>
		{:else if status === 'error'}
			<span class="text-xs text-red-600 dark:text-red-400">Failed</span>
		{/if}
	</div>
</div>
