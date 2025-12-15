<script>
	import Sortable from 'sortablejs';

	import { onDestroy, onMount, tick } from 'svelte';

	import { chatId, config, mobile, models, settings, showSidebar } from '$lib/stores';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { updateUserSettings } from '$lib/apis/users';
	import PinnedModelItem from './PinnedModelItem.svelte';

	export let selectedChatId = null;
	export let shiftKey = false;

	let pinnedModels = [];

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

	let unsubscribeSettings;

	onMount(async () => {
		pinnedModels = $settings?.pinnedModels ?? [];

		if (pinnedModels.length === 0 && $config?.default_pinned_models) {
			const defaultPinnedModels = ($config?.default_pinned_models).split(',').filter((id) => id);
			pinnedModels = defaultPinnedModels.filter((id) => $models.find((model) => model.id === id));

			settings.set({ ...$settings, pinnedModels });
			await updateUserSettings(localStorage.token, { ui: $settings });
		}

		unsubscribeSettings = settings.subscribe((value) => {
			pinnedModels = value?.pinnedModels ?? [];
		});

		await tick();
		initPinnedModelsSortable();
	});

	onDestroy(() => {
		if (unsubscribeSettings) {
			unsubscribeSettings();
		}
	});
</script>

<div class="mt-0.5 pb-1.5" id="pinned-models-list">
	{#each pinnedModels as modelId (modelId)}
		{@const model = $models.find((model) => model.id === modelId)}
		{#if model}
			<PinnedModelItem
				{model}
				{shiftKey}
				onClick={() => {
					selectedChatId = null;
					chatId.set('');
					if ($mobile) {
						showSidebar.set(false);
					}
				}}
				onUnpin={($settings?.pinnedModels ?? []).includes(modelId)
					? () => {
							const pinnedModels = $settings.pinnedModels.filter((id) => id !== modelId);
							settings.set({ ...$settings, pinnedModels });
							updateUserSettings(localStorage.token, { ui: $settings });
						}
					: null}
			/>
		{/if}
	{/each}
</div>
