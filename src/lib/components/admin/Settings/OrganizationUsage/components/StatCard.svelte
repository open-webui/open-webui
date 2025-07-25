<script>
	export let title = '';
	export let value = '';
	export let subtext = '';
	export let icon = null;
	export let isLive = false;
	export let iconBgColor = 'bg-blue-100 dark:bg-blue-900';
	export let iconColor = 'text-blue-600 dark:text-blue-400';
</script>

<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
	<div class="flex items-center justify-between">
		<div>
			<p class="text-sm font-medium text-gray-600 dark:text-gray-400">{title}</p>
			<p class="text-2xl font-semibold text-gray-900 dark:text-white">
				{value}
			</p>
			{#if subtext}
				<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{subtext}</p>
			{/if}
			{#if isLive}
				<div class="flex items-center text-xs text-green-600 mt-1">
					<div class="w-2 h-2 bg-green-500 rounded-full mr-1 animate-pulse"></div>
					Live
				</div>
			{/if}
		</div>
		{#if icon}
			<div class="flex-shrink-0">
				<div class="w-8 h-8 {iconBgColor} rounded-lg flex items-center justify-center">
					<svg class="w-4 h-4 {iconColor}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						{@html icon}
					</svg>
				</div>
			</div>
		{/if}
	</div>
</div>