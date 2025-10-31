<script>
	import Sortable from 'sortablejs';

	import { onMount, tick } from 'svelte';

	import { chatId, mobile, models, settings, showSidebar, config } from '$lib/stores';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { updateUserSettings } from '$lib/apis/users';
	import PinnedModelItem from './PinnedModelItem.svelte';

	export let selectedChatId = null;
	export let shiftKey = false;

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

					settings.set({ ...$settings, pinnedModels: pinnedModels, pinnedModelsCustomized: true });
					await updateUserSettings(localStorage.token, { ui: $settings });
				}
			});
		}
	};

	const initDefaultPinnedModels = async () => {
		console.log('[PinnedModels] initDefaultPinnedModels called');
		console.log('[PinnedModels] $config:', $config);
		console.log('[PinnedModels] $models:', $models);
		console.log('[PinnedModels] $settings:', $settings);

		// Wait for all dependencies to be ready
		if (!$config) {
			console.log('[PinnedModels] Config not ready, skipping');
			return;
		}

		if (!$models || $models.length === 0) {
			console.log('[PinnedModels] Models not ready, skipping');
			return;
		}

		console.log('[PinnedModels] default_pinned_models from config:', $config?.default_pinned_models);
		console.log('[PinnedModels] pinnedModelsCustomized:', $settings?.pinnedModelsCustomized);
		console.log('[PinnedModels] current pinnedModels:', $settings?.pinnedModels);
	
		// Check if user has customized their pinned models
		if ($settings?.pinnedModelsCustomized) {
			console.log('[PinnedModels] User has customized, skipping defaults');
			return;
		}

		// Apply default pinned models from admin config if user hasn't customized
		if ($config?.default_pinned_models) {
			const defaultPinnedModelIds = $config.default_pinned_models.split(',').filter((id) => id);
			console.log('[PinnedModels] Parsed default model IDs:', defaultPinnedModelIds);

			const availableModelIds = $models.map((m) => m.id);
			console.log('[PinnedModels] Available model IDs:', availableModelIds);

			const validPinnedModels = defaultPinnedModelIds.filter((id) => availableModelIds.includes(id));
			console.log('[PinnedModels] Valid pinned models:', validPinnedModels);

			// Only update if different from current pinned models
			const currentPinnedModels = $settings.pinnedModels ?? [];
			console.log('[PinnedModels] Current pinned models:', currentPinnedModels);
			console.log('[PinnedModels] Are they different?', JSON.stringify(validPinnedModels) !== JSON.stringify(currentPinnedModels));

			if (JSON.stringify(validPinnedModels) !== JSON.stringify(currentPinnedModels)) {
				console.log('[PinnedModels] ✅ Applying default pinned models:', validPinnedModels);
				settings.set({ ...$settings, pinnedModels: validPinnedModels });
				// Persist to backend so it's saved
				await updateUserSettings(localStorage.token, { ui: $settings });
				console.log('[PinnedModels] ✅ Default pinned models saved to backend');
			} else {
				console.log('[PinnedModels] No changes needed, models already match');
			}
		} else {
			console.log('[PinnedModels] No default_pinned_models configured in admin settings');
		}
	};

	onMount(async () => {
		await tick();
		await initDefaultPinnedModels();
		initPinnedModelsSortable();
	});

	// Re-run when config, models, or settings change
	$: if ($config && $models && $models.length > 0 && $settings) {
		initDefaultPinnedModels();
	}
</script>

<div class="mt-0.5 pb-1.5" id="pinned-models-list">
	{#each $settings.pinnedModels as modelId (modelId)}
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
				onUnpin={() => {
					const pinnedModels = $settings.pinnedModels.filter((id) => id !== modelId);
					settings.set({ ...$settings, pinnedModels, pinnedModelsCustomized: true });
					updateUserSettings(localStorage.token, { ui: $settings });
				}}
			/>
		{/if}
	{/each}
</div>
