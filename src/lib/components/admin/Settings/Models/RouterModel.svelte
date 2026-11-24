<script lang="ts">
	import { resolveLocalizedResource } from '$lib/utils/localizedContent';
	import { getContext, createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import RouterModelModal from './RouterModelModal.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { models } from '$lib/stores';
	export let model;
	export let onEdit: (model: object, accessGrants: object[]) => Promise<boolean> = async () => true;

	let showModel = false;
	export const open = () => (showModel = true);
</script>

<RouterModelModal
	bind:show={showModel}
	edit={true}
	{model}
	onSubmit={onEdit}
	on:delete={async () => {
		dispatch('delete');
	}}
/>

<button
	class="flex w-full min-w-0 items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs font-normal transition hover:bg-base-1000/5 focus-visible:outline focus-visible:outline-2 dark:hover:bg-base-0/5"
	type="button"
	on:click={() => {
		showModel = true;
	}}
>
	<img
		src={`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${model.id}&v=${$models.find((item) => item.id === model.id)?.info?.updated_at}`}
		alt=""
		class="size-4 shrink-0 rounded-full object-cover"
	/>
	<span class="truncate text-base-900 dark:text-base-100">
		{resolveLocalizedResource(model, $i18n.language)}
	</span>
	<span class="ml-auto shrink-0 truncate text-base-400 dark:text-base-600">{model.id}</span>
</button>
