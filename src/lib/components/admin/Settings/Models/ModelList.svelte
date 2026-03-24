<script lang="ts">
	import Sortable from 'sortablejs';

	import { createEventDispatcher, getContext, onMount, onDestroy, tick } from 'svelte';
	const i18n = getContext('i18n');

	import { models } from '$lib/stores';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EllipsisVertical from '$lib/components/icons/EllipsisVertical.svelte';

	export let modelIds = [];

	let sortable = null;
	let modelListElement = null;

	const positionChangeHandler = (event) => {
		const { oldIndex, newIndex, item } = event;

		// Revert SortableJS's DOM manipulation so Svelte doesn't get out of sync.
		// Svelte expects the DOM to match its virtual DOM before it applies state updates.
		const parent = item.parentNode;
		const target = parent.children[oldIndex < newIndex ? oldIndex : oldIndex + 1];
		parent.insertBefore(item, target);

		// Now apply the logical state update, letting Svelte handle the real DOM move.
		const updatedIds = [...modelIds];
		const [movedId] = updatedIds.splice(oldIndex, 1);
		updatedIds.splice(newIndex, 0, movedId);
		modelIds = updatedIds;
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
				onUpdate: (event) => {
					positionChangeHandler(event);
				}
			});
		}
	};

	$: if (modelIds && modelListElement) {
		tick().then(() => {
			initSortable();
		});
	}

	onMount(() => {
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
