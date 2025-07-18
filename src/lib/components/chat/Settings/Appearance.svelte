<script lang="ts">
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { settings } from '$lib/stores';
	
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');
	
	export let saveSettings: Function;
	
	// Background pattern settings
	let backgroundPattern = 'none';
	let backgroundOpacity = 50;
	
	onMount(() => {
		// Load background pattern settings
		backgroundPattern = $settings.backgroundPattern || 'none';
		backgroundOpacity = $settings.backgroundOpacity || 50;
	});
	
	const saveHandler = () => {
		saveSettings({
			backgroundPattern: backgroundPattern,
			backgroundOpacity: backgroundOpacity
		});
		dispatch('save');
	};
</script>

<form
	id="tab-appearance"
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={() => {
		saveHandler();
	}}
>
	<div class="space-y-3 overflow-y-scroll max-h-[28rem] lg:max-h-full">
		<div class="space-y-6">
			<!-- Background Pattern Section -->
			<div>
				<div class="mb-4">
					<h3 class="text-lg font-medium text-gray-900 dark:text-gray-100">{$i18n.t('Background Patterns')}</h3>
					<p class="text-sm text-gray-600 dark:text-gray-400">Add subtle patterns to your chat background</p>
				</div>
				
				<div class="space-y-4">
					<!-- Background Pattern Selector -->
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
							{$i18n.t('Pattern Type')}
						</label>
						<select
							bind:value={backgroundPattern}
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
						>
							<option value="none">{$i18n.t('None')}</option>
							<option value="dots">{$i18n.t('Dots')}</option>
							<option value="grid">{$i18n.t('Grid')}</option>
							<option value="diagonal">{$i18n.t('Diagonal')}</option>
						</select>
					</div>
					
					<!-- Background Pattern Opacity -->
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
							{$i18n.t('Pattern Opacity')}: {backgroundOpacity}%
						</label>
						<input
							type="range"
							min="0"
							max="100"
							bind:value={backgroundOpacity}
							class="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
						/>
					</div>
					
					<!-- Pattern Preview -->
					{#if backgroundPattern !== 'none'}
						<div class="mt-4">
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								{$i18n.t('Pattern Preview')}
							</label>
							<div 
								class="w-full h-20 border border-gray-300 dark:border-gray-600 rounded-md background-pattern-{backgroundPattern}"
								style="opacity: {backgroundOpacity / 100}"
							></div>
						</div>
					{/if}
				</div>
			</div>
		</div>
	</div>
	
	<!-- Save Button -->
	<div class="flex justify-end text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>