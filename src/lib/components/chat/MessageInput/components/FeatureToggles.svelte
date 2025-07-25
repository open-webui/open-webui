<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import Photo from '$lib/components/icons/Photo.svelte';
	import CommandLine from '$lib/components/icons/CommandLine.svelte';
	import Wrench from '$lib/components/icons/Wrench.svelte';
	
	export let webSearchEnabled = false;
	export let imageGenerationEnabled = false;
	export let codeInterpreterEnabled = false;
	export let toolsEnabled = false;
	export let toolsCount = 0;
	
	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();
	
	function toggleWebSearch() {
		dispatch('toggle', { feature: 'webSearch', enabled: !webSearchEnabled });
	}
	
	function toggleImageGeneration() {
		dispatch('toggle', { feature: 'imageGeneration', enabled: !imageGenerationEnabled });
	}
	
	function toggleCodeInterpreter() {
		dispatch('toggle', { feature: 'codeInterpreter', enabled: !codeInterpreterEnabled });
	}
	
	function openToolsMenu() {
		dispatch('openTools');
	}
</script>

<div class="flex items-center gap-1">
	<!-- Web Search -->
	<Tooltip content={$i18n.t('Web Search')}>
		<button
			type="button"
			class="p-1.5 rounded-lg transition-colors
				{webSearchEnabled 
					? 'bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-400' 
					: 'text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800'}"
			on:click={toggleWebSearch}
		>
			<GlobeAlt class="w-4 h-4" />
		</button>
	</Tooltip>
	
	<!-- Image Generation -->
	<Tooltip content={$i18n.t('Image Generation')}>
		<button
			type="button"
			class="p-1.5 rounded-lg transition-colors
				{imageGenerationEnabled 
					? 'bg-purple-100 dark:bg-purple-900 text-purple-600 dark:text-purple-400' 
					: 'text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800'}"
			on:click={toggleImageGeneration}
		>
			<Photo class="w-4 h-4" />
		</button>
	</Tooltip>
	
	<!-- Code Interpreter -->
	<Tooltip content={$i18n.t('Code Interpreter')}>
		<button
			type="button"
			class="p-1.5 rounded-lg transition-colors
				{codeInterpreterEnabled 
					? 'bg-green-100 dark:bg-green-900 text-green-600 dark:text-green-400' 
					: 'text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800'}"
			on:click={toggleCodeInterpreter}
		>
			<CommandLine class="w-4 h-4" />
		</button>
	</Tooltip>
	
	<!-- Tools -->
	<Tooltip content={$i18n.t('Tools')}>
		<button
			type="button"
			class="p-1.5 rounded-lg transition-colors relative
				{toolsEnabled 
					? 'bg-orange-100 dark:bg-orange-900 text-orange-600 dark:text-orange-400' 
					: 'text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800'}"
			on:click={openToolsMenu}
		>
			<Wrench class="w-4 h-4" />
			{#if toolsCount > 0}
				<span class="absolute -top-1 -right-1 bg-orange-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">
					{toolsCount}
				</span>
			{/if}
		</button>
	</Tooltip>
</div>