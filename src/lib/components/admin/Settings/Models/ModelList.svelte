<script lang="ts">
	import Sortable from 'sortablejs';

	import { createEventDispatcher, getContext, onDestroy, onMount, tick } from 'svelte';
	const i18n = getContext('i18n');

	import { models } from '$lib/stores';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EllipsisVertical from '$lib/components/icons/EllipsisVertical.svelte';

	export let modelIds = [];

	let sortable = null;
	let modelListElement = null;

	const positionChangeHandler = () => {
		// Read new order from DOM
		const newOrder = Array.from(modelListElement.children).map((child) =>
			child.id.replace('model-item-', '')
		);

		// Revert SortableJS DOM manipulation so Svelte stays in control of the DOM
		if (sortable) {
			sortable.sort(
				modelIds.map((id) => `model-item-${id}`),
				true
			);
		}

		// Update reactive data — Svelte will re-render with the new order
		modelIds = newOrder;
	};

	const initSortable = () => {
		if (sortable) {
			sortable.destroy();
			sortable = null;
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

	onMount(() => {
		// Wait a tick for the {#if} block to render and bind modelListElement
		tick().then(() => {
			initSortable();
		});
	});

	onDestroy(() => {
		if (sortable) {
			sortable.destroy();
		}
	});
</script>

{#if modelIds.length > 0}
	<div class="flex flex-col -translate-x-1" bind:this={modelListElement}>
		{#each modelIds as modelId (modelId)}
			<div class=" flex gap-2 w-full justify-between items-center" id="model-item-{modelId}">
				<Tooltip content={modelId} placement="top-start">
					<div class="flex items-center gap-1">
						<EllipsisVertical className="size-4 cursor-move model-item-handle" />

						<div class=" text-sm flex-1 py-1 rounded-lg line-clamp-1">
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
