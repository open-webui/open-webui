<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import type { Model } from '$lib/stores';
	import { models } from '$lib/stores';
	
	export let selectedModels: string[] = [''];
	export let atSelectedModel: Model | undefined = undefined;
	export let showLabel = false;
	
	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();
	
	$: availableModels = $models.filter(m => m.owned_by !== 'arena');
	$: selectedModel = atSelectedModel || availableModels.find(m => m.id === selectedModels[0]);
	
	function handleModelChange(event: Event) {
		const select = event.target as HTMLSelectElement;
		const modelId = select.value;
		
		if (modelId === '') {
			dispatch('modelChange', { models: [''], atModel: undefined });
			return;
		}
		
		const model = availableModels.find(m => m.id === modelId);
		if (model) {
			dispatch('modelChange', { 
				models: [modelId], 
				atModel: atSelectedModel ? model : undefined 
			});
		}
	}
	
	function clearAtModel() {
		dispatch('modelChange', { models: selectedModels, atModel: undefined });
	}
</script>

<div class="flex items-center gap-2">
	{#if showLabel}
		<label for="model-select" class="text-sm font-medium text-gray-700 dark:text-gray-300">
			{$i18n.t('Model')}:
		</label>
	{/if}
	
	<div class="relative">
		<select
			id="model-select"
			class="pr-8 pl-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 
				   bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
				   focus:ring-2 focus:ring-blue-500 focus:border-transparent
				   cursor-pointer appearance-none"
			value={selectedModel?.id || ''}
			on:change={handleModelChange}
		>
			<option value="">{$i18n.t('Select a model')}</option>
			
			{#each availableModels as model}
				<option value={model.id}>
					{model.name}
					{#if model.info?.meta?.profile_image_url}
						🔹
					{/if}
				</option>
			{/each}
		</select>
		
		<div class="absolute inset-y-0 right-0 flex items-center pr-2 pointer-events-none">
			<svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
			</svg>
		</div>
	</div>
	
	{#if atSelectedModel}
		<button
			type="button"
			class="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
			on:click={clearAtModel}
		>
			{$i18n.t('Clear @ selection')}
		</button>
	{/if}
</div>

<style>
	select {
		background-image: none;
	}
</style>