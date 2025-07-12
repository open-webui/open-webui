<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import XMark from '$lib/components/icons/XMark.svelte';
	import { models } from '$lib/stores';

	export let show = false;
	export let selectedModelId = '';
</script>

<div class="flex items-center mb-1.5 pt-1.5">
	<div class=" -translate-x-1.5 flex items-center">
		<button
			class="p-0.5 bg-transparent transition rounded-lg"
			on:click={() => {
				show = !show;
			}}
		>
			<XMark className="size-5" strokeWidth="2.5" />
		</button>
	</div>

	<div class=" font-medium text-base flex items-center gap-1">
		<div>
			{$i18n.t('Settings')}
		</div>
	</div>
</div>

<div class="mt-1">
	<div>
		<div class=" text-xs font-medium mb-1">Model</div>

		<div class="w-full">
			<select class="w-full bg-transparent text-sm outline-hidden" bind:value={selectedModelId}>
				<option value="" class="bg-gray-50 dark:bg-gray-700" disabled>
					{$i18n.t('Select a model')}
				</option>
				{#each $models.filter((model) => !(model?.info?.meta?.hidden ?? false)) as model}
					<option value={model.id} class="bg-gray-50 dark:bg-gray-700">{model.name}</option>
				{/each}
			</select>
		</div>
	</div>
</div>
