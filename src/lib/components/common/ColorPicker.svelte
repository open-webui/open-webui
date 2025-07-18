<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	
	const dispatch = createEventDispatcher();
	
	export let value: string = '#3b82f6';
	export let label: string = 'Color';
	export let presetColors: string[] = [
		'#3b82f6', // Blue
		'#8b5cf6', // Purple
		'#06b6d4', // Cyan
		'#10b981', // Green
		'#f59e0b', // Amber
		'#ef4444', // Red
		'#6b7280', // Gray
		'#1f2937', // Dark Gray
		'#ec4899', // Pink
		'#84cc16', // Lime
		'#f97316', // Orange
		'#8b5cf6'  // Violet
	];
	
	let showPicker = false;
	
	const handleColorChange = (color: string) => {
		value = color;
		dispatch('change', color);
		showPicker = false;
	};
	
	const handleCustomColorChange = (event: Event) => {
		const target = event.target as HTMLInputElement;
		handleColorChange(target.value);
	};
</script>

<div class="color-picker-container">
	<div class="flex items-center justify-between">
		<span class="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</span>
		<div class="relative">
			<button
				class="w-8 h-8 rounded-full border-2 border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-primary transition-all duration-200 hover:scale-110"
				style="background-color: {value}"
				on:click={() => showPicker = !showPicker}
				aria-label="Open color picker"
			>
			</button>
			
			{#if showPicker}
				<div class="absolute top-10 right-0 z-50 p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg min-w-64">
					<div class="space-y-4">
						<!-- Preset Colors -->
						<div>
							<h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Preset Colors</h4>
							<div class="grid grid-cols-6 gap-2">
								{#each presetColors as color}
									<button
										class="w-8 h-8 rounded-full border-2 transition-all duration-200 hover:scale-110 focus:outline-none focus:ring-2 focus:ring-primary"
										class:border-gray-300={color !== value}
										class:dark:border-gray-600={color !== value}
										class:border-primary={color === value}
										class:ring-2={color === value}
										class:ring-primary={color === value}
										style="background-color: {color}"
										on:click={() => handleColorChange(color)}
										aria-label="Select color {color}"
									>
									</button>
								{/each}
							</div>
						</div>
						
						<!-- Custom Color Input -->
						<div>
							<h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Custom Color</h4>
							<div class="flex items-center space-x-2">
								<input
									type="color"
									{value}
									on:change={handleCustomColorChange}
									class="w-12 h-8 rounded border border-gray-300 dark:border-gray-600 cursor-pointer"
								/>
								<input
									type="text"
									{value}
									on:input={handleCustomColorChange}
									class="flex-1 px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary"
									placeholder="#3b82f6"
								/>
							</div>
						</div>
						
						<!-- Close Button -->
						<div class="flex justify-end">
							<button
								class="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
								on:click={() => showPicker = false}
							>
								Done
							</button>
						</div>
					</div>
				</div>
			{/if}
		</div>
	</div>
</div>

<style>
	.color-picker-container {
		position: relative;
	}
</style>