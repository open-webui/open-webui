<script lang="ts">
	import { getContext } from 'svelte';

	import { models } from '$lib/stores';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Search from '$lib/components/icons/Search.svelte';

	const i18n = getContext('i18n');

	export let model_id = '';

	export let side: 'top' | 'bottom' = 'top';
	export let align: 'start' | 'end' = 'start';

	/** Optional callback when selection changes */
	export let onChange: () => void = () => {};

	let showDropdown = false;
	let modelSearch = '';

	$: modelLabel = model_id
		? $models.find((m) => m.id === model_id)?.name || model_id
		: $i18n.t('Select model');

	$: filteredModels = (
		modelSearch
			? $models.filter(
					(m) =>
						m.name.toLowerCase().includes(modelSearch.toLowerCase()) ||
						m.id.toLowerCase().includes(modelSearch.toLowerCase())
				)
			: $models
	).filter((m) => !(m?.info?.meta?.hidden ?? false));
</script>

<Dropdown bind:show={showDropdown} {side} {align}>
	<button
		type="button"
		class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-2xl text-xs transition
			text-gray-600 dark:text-gray-400 hover:bg-black/5 dark:hover:bg-white/5"
	>
		<svg
			xmlns="http://www.w3.org/2000/svg"
			fill="none"
			viewBox="0 0 24 24"
			stroke-width="1.5"
			stroke="currentColor"
			class="size-3.5 shrink-0"
		>
			<path
				stroke-linecap="round"
				stroke-linejoin="round"
				d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z"
			/>
		</svg>
		<span class="whitespace-nowrap max-w-32 truncate">{modelLabel}</span>
		<svg
			xmlns="http://www.w3.org/2000/svg"
			fill="none"
			viewBox="0 0 24 24"
			stroke-width="2"
			stroke="currentColor"
			class="size-2.5"
		>
			<path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
		</svg>
	</button>

	<div
		slot="content"
		class="rounded-xl shadow-lg border border-gray-200 dark:border-gray-800 flex flex-col bg-white dark:bg-gray-850 w-72 p-0.5"
	>
		<div class="flex items-center gap-1.5 px-2 py-1">
			<Search className="size-3.5" strokeWidth="2.5" />
			<input
				bind:value={modelSearch}
				class="w-full text-[13px] bg-transparent outline-hidden"
				placeholder={$i18n.t('Search a model')}
				autocomplete="off"
				on:click={(e) => e.stopPropagation()}
			/>
		</div>

		<div class="overflow-y-auto scrollbar-thin max-h-60">
			<div class="px-2 text-[11px] text-gray-500 py-0.5">
				{$i18n.t('Models')}
			</div>

			{#each filteredModels as model (model.id)}
				<button
					class="h-[1.6875rem] px-2 rounded-xl w-full text-left text-[13px] {model_id === model.id
						? 'bg-gray-50 dark:bg-gray-800'
						: ''}"
					type="button"
					on:click={() => {
						model_id = model.id;
						showDropdown = false;
						modelSearch = '';
						onChange();
					}}
				>
					<div class="flex text-black dark:text-gray-100 line-clamp-1">
						<img
							src={`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${encodeURIComponent(model.id)}`}
							alt={model?.name ?? model.id}
							class="rounded-full size-5 items-center mr-2"
							loading="lazy"
							on:error={(e) => {
								e.currentTarget.src = '/favicon.png';
							}}
						/>
						<div class="truncate">
							{model.name}
						</div>
					</div>
				</button>
			{:else}
				<div class="block px-2 py-1.5 text-[13px] text-gray-700 dark:text-gray-100">
					{$i18n.t('No results found')}
				</div>
			{/each}
		</div>
	</div>
</Dropdown>
