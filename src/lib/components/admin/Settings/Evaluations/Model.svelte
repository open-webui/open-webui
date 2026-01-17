<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import ArenaModelModal from './ArenaModelModal.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	export let model;

	let showModel = false;
</script>

<ArenaModelModal
	bind:show={showModel}
	edit={true}
	{model}
	on:submit={async (e) => {
		dispatch('edit', e.detail);
	}}
	on:delete={async () => {
		dispatch('delete');
	}}
/>

<div
	class="bg-gray-50 dark:bg-gray-850 rounded-lg p-4 flex flex-col justify-between border border-gray-100 dark:border-gray-800"
>
	<div>
		<div class="flex items-center justify-between mb-3">
			<div class="flex items-center gap-2">
				<img
					src={`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${model.id}`}
					alt={model.name}
					class="size-5 rounded-full object-cover shrink-0 opacity-70"
				/>
				<div class="text-xs font-medium text-gray-500">
					{$i18n.t('Arena Model')}
				</div>
			</div>
			<button
				class="p-1 bg-transparent hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
				type="button"
				on:click={() => {
					showModel = true;
				}}
			>
				<Cog6 className="w-4 h-4" />
			</button>
		</div>

		<button
			class="w-full text-left"
			on:click={() => {
				showModel = true;
			}}
			type="button"
		>
			<div class="text-sm font-medium text-gray-700 dark:text-gray-200 hover:text-blue-600 dark:hover:text-blue-400 transition">
				{model.name}
			</div>
			{#if model?.meta?.description || model.id}
				<div class="text-xs text-gray-500 mt-1 line-clamp-2">
					{model?.meta?.description ?? model.id}
				</div>
			{/if}
		</button>
	</div>
</div>
