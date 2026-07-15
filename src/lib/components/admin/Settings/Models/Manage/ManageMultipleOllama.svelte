<script>
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import ManageOllama from './ManageOllama.svelte';
	import SettingsSelect from '$lib/components/common/SettingsSelect.svelte';

	export let ollamaConfig = null;

	let selectedUrlIdx = 0;
</script>

{#if ollamaConfig}
	<div class="flex-1 mb-2.5 pr-1.5 rounded-lg bg-gray-50 dark:text-gray-300 dark:bg-gray-850">
		<SettingsSelect
			bind:value={selectedUrlIdx}
			placeholder={$i18n.t('Select an Ollama instance')}
			className="w-full"
			selectClassName="text-sm"
		>
			{#each ollamaConfig.OLLAMA_BASE_URLS as url, idx}
				<option value={idx}>{url}</option>
			{/each}
		</SettingsSelect>
	</div>

	<div>
		<ManageOllama urlIdx={selectedUrlIdx} />
	</div>
{/if}
