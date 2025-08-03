<script lang="ts">
	export let message: string = 'Loading...';
	export let size: 'sm' | 'md' | 'lg' = 'md';
	
	const sizeClasses = {
		sm: 'h-4 w-4',
		md: 'h-8 w-8',
		lg: 'h-12 w-12'
	};
</script>

<div class="flex items-center justify-center py-12">
	<div class="animate-spin rounded-full {sizeClasses[size]} border-b-2 border-gray-900 dark:border-white"></div>
	<span class="ml-2 text-gray-600 dark:text-gray-400">{message}</span>
</div>