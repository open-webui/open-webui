<script>
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import ManageOllama from './ManageOllama.svelte';
	import SettingsSelect from '$lib/components/common/SettingsSelect.svelte';

	export let ollamaConfig = null;

	let selectedUrlIdx = 0;
</script>

{#if ollamaConfig}
	<div class=" mb-2 text-sm font-normal">{$i18n.t('Ollama')}</div>

	<div class="flex-1 mb-2.5">
		<SettingsSelect
			bind:value={selectedUrlIdx}
			className="w-full"
			placeholder={$i18n.t('Select an Ollama instance')}
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
