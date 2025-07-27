<script lang="ts">
	export let title: string;
	export let value: string;
	export let subtitle: string;
	export let iconColor: string = 'blue';
	export let iconPath: string;
	
	const colorClasses = {
		blue: 'bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-400',
		green: 'bg-green-100 dark:bg-green-900 text-green-600 dark:text-green-400',
		purple: 'bg-purple-100 dark:bg-purple-900 text-purple-600 dark:text-purple-400'
	};
</script>

<div class="bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
	<div class="flex items-center justify-between">
		<div>
			<p class="text-sm font-medium text-gray-600 dark:text-gray-400">{title}</p>
			<p class="text-2xl font-semibold text-gray-900 dark:text-white">
				{value}
			</p>
			<p class="text-xs text-gray-500 mt-1">{subtitle}</p>
		</div>
		<div class="flex-shrink-0">
			<div class="w-8 h-8 {colorClasses[iconColor]} rounded-lg flex items-center justify-center">
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={iconPath}></path>
				</svg>
			</div>
		</div>
	</div>
</div>