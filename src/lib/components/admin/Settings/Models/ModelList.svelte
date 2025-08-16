<script lang="ts">
	import Sortable from 'sortablejs';

	import { createEventDispatcher, getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { models } from '$lib/stores';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EllipsisVertical from '$lib/components/icons/EllipsisVertical.svelte';

	export let modelIds = [];

	let sortable = null;
	let modelListElement = null;

	const positionChangeHandler = () => {
		const modelList = Array.from(modelListElement.children).map((child) =>
			child.id.replace('model-item-', '')
		);

		modelIds = modelList;
	};

	$: if (modelIds) {
		init();
	}

	const init = () => {
		if (sortable) {
			sortable.destroy();
		}

		if (modelListElement) {
			sortable = new Sortable(modelListElement, {
				animation: 150,
				handle: '.model-item-handle',
				onUpdate: async (event) => {
					positionChangeHandler();
				}
			});
		}
	};
</script>

{#if modelIds.length > 0}
	<div class="flex flex-col -translate-x-1" bind:this={modelListElement}>
		{#each modelIds as modelId, modelIdx (`${modelId}-${modelIdx}`)}
			<div class=" flex gap-2 w-full justify-between items-center" id="model-item-{modelId}">
				<Tooltip content={modelId} placement="top-start">
					<div class="flex items-center gap-1">
						<EllipsisVertical className="size-4 cursor-move model-item-handle" />

						<div class=" text-sm flex-1 py-1 rounded-lg">
							{#if $models.find((model) => model.id === modelId)}
								{$models.find((model) => model.id === modelId).name}
							{:else}
								{modelId}
							{/if}
						</div>
					</div>
				</Tooltip>
			</div>
		{/each}
	</div>
{:else}
	<div class="text-gray-500 text-xs text-center py-2">
		{$i18n.t('No models found')}
	</div>
{/if}
