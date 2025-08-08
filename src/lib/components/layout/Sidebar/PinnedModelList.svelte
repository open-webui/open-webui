<script>
	import Sortable from 'sortablejs';

	import { onMount } from 'svelte';

	import { chatId, mobile, models, settings, showSidebar } from '$lib/stores';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { updateUserSettings } from '$lib/apis/users';

	export let selectedChatId = null;

	const initPinnedModelsSortable = () => {
		const pinnedModelsList = document.getElementById('pinned-models-list');
		if (pinnedModelsList && !$mobile) {
			new Sortable(pinnedModelsList, {
				animation: 150,
				onUpdate: async (event) => {
					const modelId = event.item.dataset.id;
					const newIndex = event.newIndex;

					const pinnedModels = $settings.pinnedModels;
					const oldIndex = pinnedModels.indexOf(modelId);

					pinnedModels.splice(oldIndex, 1);
					pinnedModels.splice(newIndex, 0, modelId);

					settings.set({ ...$settings, pinnedModels: pinnedModels });
					await updateUserSettings(localStorage.token, { ui: $settings });
				}
			});
		}
	};

	onMount(() => {
		initPinnedModelsSortable();
	});
</script>

<div class="mt-0.5 pb-1.5" id="pinned-models-list">
	{#each $settings.pinnedModels as modelId (modelId)}
		{@const model = $models.find((model) => model.id === modelId)}
		{#if model}
			<div
				class="px-[7px] flex justify-center text-gray-800 dark:text-gray-200 cursor-grab"
				data-id={modelId}
			>
				<a
					class="grow flex items-center space-x-2.5 rounded-lg px-2 py-[7px] hover:bg-gray-100 dark:hover:bg-gray-900 transition"
					href="/?model={modelId}"
					on:click={() => {
						selectedChatId = null;
						chatId.set('');

						if ($mobile) {
							showSidebar.set(false);
						}
					}}
					draggable="false"
				>
					<div class="self-center shrink-0">
						<img
							crossorigin="anonymous"
							src={model?.info?.meta?.profile_image_url ?? `${WEBUI_BASE_URL}/static/favicon.png`}
							class=" size-5 rounded-full -translate-x-[0.5px]"
							alt="logo"
						/>
					</div>

					<div class="flex self-center translate-y-[0.5px]">
						<div class=" self-center text-sm font-primary line-clamp-1">
							{model?.name ?? modelId}
						</div>
					</div>
				</a>
			</div>
		{/if}
	{/each}
</div>
