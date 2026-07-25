<script>
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import ManageOllama from './ManageOllama.svelte';
	import SettingsSelect from '$lib/components/common/SettingsSelect.svelte';

	export let ollamaConfig = null;

	let selectedUrlIdx = 0;

	// Matches the backend's resolve_api_config(): index key first, legacy URL key second.
	const isEnabled = (apiConfigs, idx, url) =>
		(apiConfigs?.[`${idx}`] ?? apiConfigs?.[url])?.enable ?? true;

	// Keep the original index of every connection: the backend addresses them by their
	// position in OLLAMA_BASE_URLS, so filtering must not renumber them.
	$: instances = (ollamaConfig?.OLLAMA_BASE_URLS ?? [])
		.map((url, idx) => ({ url, idx }))
		.filter(({ url, idx }) => isEnabled(ollamaConfig?.OLLAMA_API_CONFIGS, idx, url));

	$: if (instances.length > 0 && !instances.some(({ idx }) => idx === selectedUrlIdx)) {
		selectedUrlIdx = instances[0].idx;
	}
</script>

{#if ollamaConfig}
	{#if instances.length > 1}
		<div class=" mb-2 text-sm font-normal">{$i18n.t('Ollama')}</div>

		<div class="flex-1 mb-2.5 rounded-lg bg-gray-50 dark:text-gray-300 dark:bg-gray-850">
			<SettingsSelect
				bind:value={selectedUrlIdx}
				className="w-full"
				placeholder={$i18n.t('Select an Ollama instance')}
				selectClassName="text-sm"
			>
				{#each instances as { url, idx }}
					<option value={idx}>{url}</option>
				{/each}
			</SettingsSelect>
		</div>
	{/if}

	<div>
		<ManageOllama urlIdx={selectedUrlIdx} />
	</div>
{/if}
