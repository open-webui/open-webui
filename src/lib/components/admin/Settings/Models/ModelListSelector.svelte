<script>
	import { getContext } from 'svelte';
	import { models } from '$lib/stores';
	import Minus from '$lib/components/icons/Minus.svelte';

	const i18n = getContext('i18n');

	export let title = '';
	export let selectedModelIds = [];
	export let selectedId = '';
</script>

<div>
	<div class="flex flex-col w-full">
		<div class="mb-1 flex justify-between">
			<div class="text-xs text-gray-500">{$i18n.t(title)}</div>
		</div>

		<div class="flex items-center -mr-1">
			<select
				class="w-full py-1 text-sm rounded-lg bg-transparent {selectedId
					? ''
					: 'text-gray-500'} placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
				bind:value={selectedId}
			>
				<option value="">{$i18n.t('Select a model')}</option>
				{#each $models as model}
					<option value={model.id} class="bg-gray-50 dark:bg-gray-700">{model.name}</option>
				{/each}
			</select>
		</div>

		{#if selectedModelIds.length > 0}
			<div class="flex flex-col">
				{#each selectedModelIds as modelId, modelIdx}
					<div class=" flex gap-2 w-full justify-between items-center">
						<div class=" text-sm flex-1 py-1 rounded-lg">
							{$models.find((model) => model.id === modelId)?.name}
						</div>
						<div class="shrink-0">
							<button
								type="button"
								on:click={() => {
									selectedModelIds = selectedModelIds.filter((_, idx) => idx !== modelIdx);
								}}
							>
								<Minus strokeWidth="2" className="size-3.5" />
							</button>
						</div>
					</div>
				{/each}
			</div>
		{:else}
			<div class="text-gray-500 text-xs text-center py-2">
				{$i18n.t('No models selected')}
			</div>
		{/if}
	</div>
</div>
