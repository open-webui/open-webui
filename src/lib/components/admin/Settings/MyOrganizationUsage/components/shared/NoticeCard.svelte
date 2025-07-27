<script lang="ts">
	export let type: 'info' | 'warning' | 'error' | 'success' = 'info';
	export let title: string;
	export let showIcon: boolean = true;
	
	const typeClasses = {
		info: 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20',
		warning: 'text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20',
		error: 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20',
		success: 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20'
	};
	
	const iconPaths = {
		info: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
		warning: 'M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z',
		error: 'M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
		success: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z'
	};
</script>

<div class="mb-4 text-xs {typeClasses[type]} flex items-center justify-between p-3 rounded-lg">
	<div class="flex items-center">
		{#if showIcon}
			<svg class="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
				<path fill-rule="evenodd" d={iconPaths[type]} clip-rule="evenodd"></path>
			</svg>
		{/if}
		<span>
			<strong>{title}</strong>
			<slot />
		</span>
	</div>
	<slot name="actions" />
</div>