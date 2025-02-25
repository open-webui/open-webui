<script lang="ts">
	import Sortable from 'sortablejs';
  
	import { createEventDispatcher, getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');
  
	import { models } from '$lib/stores';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EllipsisVertical from '$lib/components/icons/EllipsisVertical.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
  
	export let modelIds = [];
  
	let sortable = null;
	let modelListElement = null;
  
	const positionChangeHandler = () => {
	  const modelList = Array.from(modelListElement.children).map((child) =>
		child.id.replace('model-item-', '')
	  );
  
	  modelIds = modelList;
	};
  
	let sortAsc = true;
  
	const sortModels = (event: MouseEvent) => {
	  event.preventDefault();
	  event.stopPropagation();
	  showSortConfirmation = true;
  };

  let showSortConfirmation = false;

  const handleSortConfirmation = (confirm: boolean) => {
    showSortConfirmation = false;
    if (confirm) {
	  sortAsc = !sortAsc;
	  modelIds = modelIds.filter(id => id !== '').sort((a, b) => {
		const nameA = $models.find((model) => model.id === a)?.name || a;
		const nameB = $models.find((model) => model.id === b)?.name || b;
		return sortAsc ? nameA.localeCompare(nameB) : nameB.localeCompare(nameA);
	  });
	}
  };
  
	onMount(() => {
	  sortable = Sortable.create(modelListElement, {
		animation: 150,
		handle: '.handle',
		onUpdate: async (event) => {
		  positionChangeHandler();
		}
	  });
	});
  </script>
  
  {#if modelIds.length > 0}
	<div class="flex flex-col -translate-x-1" bind:this={modelListElement}>
	  <div class="flex w-full justify-end mb-2">
		<button class="text-gray-500 text-xs rounded-lg py-1 px-2" on:click={sortModels}>
		  {sortAsc ? $i18n.t('Sort models Z-A') : $i18n.t('Sort models A-Z')}
		</button>
	  </div>
	  {#each modelIds.filter(id => id !== '') as modelId, modelIdx (modelId)}
		<div class="flex gap-2 w-full justify-between items-center" id="model-item-{modelId}">
		  <Tooltip content={modelId} placement="top-start">
			<div class="flex items-center gap-1">
			  <EllipsisVertical className="size-4 cursor-move handle" />
			  <div class="text-sm flex-1 py-1 rounded-lg">
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

  <ConfirmDialog
  title={$i18n.t('Sort models by name')}
  message={$i18n.t(`This will sort your models from ${sortAsc ? 'Z-A' : 'A-Z'}. Are you sure you want to do this?`)}
  bind:show={showSortConfirmation}
  onConfirm={() => handleSortConfirmation(true)}
  onCancel={() => handleSortConfirmation(false)}
/>
