<script lang="ts">
	import { getContext } from 'svelte';

	import SettingsSelect from '$lib/components/common/SettingsSelect.svelte';
	import ManageProviderModels from './ManageProviderModels.svelte';

	const i18n: any = getContext('i18n');

	export let connections: { idx: number; url: string; provider?: string }[] = [];

	let selectedUrlIdx = `${connections[0]?.idx ?? 0}`;

	const getProviderLabel = (provider = '') => {
		if (provider === 'lmstudio') return $i18n.t('LM Studio');
		if (provider === 'llama.cpp') return $i18n.t('llama.cpp');
		return provider;
	};

	const providerSupportsDelete = (provider = '') => provider === 'llama.cpp';

	$: if (
		connections.length > 0 &&
		!connections.some((connection) => `${connection.idx}` === selectedUrlIdx)
	) {
		selectedUrlIdx = `${connections[0].idx}`;
	}
	$: selectedConnection =
		connections.find((connection) => `${connection.idx}` === selectedUrlIdx) ?? connections[0];
</script>

{#if connections.length > 0}
	<div class="mb-2 text-sm font-normal">{$i18n.t('Model providers')}</div>

	<div class="mb-2.5 flex-1">
		<SettingsSelect
			bind:value={selectedUrlIdx}
			className="w-full"
			placeholder={$i18n.t('Select an instance')}
		>
			{#each connections as connection}
				<option value={`${connection.idx}`}>
					{getProviderLabel(connection.provider)} - {connection.url}
				</option>
			{/each}
		</SettingsSelect>
	</div>

	<div>
		<ManageProviderModels
			urlIdx={Number(selectedUrlIdx)}
			provider={selectedConnection?.provider ?? ''}
			providerLabel={getProviderLabel(selectedConnection?.provider)}
			supportsDelete={providerSupportsDelete(selectedConnection?.provider)}
		/>
	</div>
{/if}
