<script>
	import Sortable from 'sortablejs';

	import { onMount, tick } from 'svelte';

	import {
		chatId,
		mobile,
		models,
		pinnedModels,
		settings,
		showSidebar,
		visiblePinnedModels
	} from '$lib/stores';
	import { updateUserSettings } from '$lib/apis/users';
	import PinnedModelItem from './PinnedModelItem.svelte';

	export let selectedChatId = null;
	export let shiftKey = false;

	const initPinnedModelsSortable = () => {
		const pinnedModelsList = document.getElementById('pinned-models-list');
		if (pinnedModelsList && !$mobile) {
			new Sortable(pinnedModelsList, {
				animation: 150,
				setData: function (dataTransfer, dragEl) {
					dataTransfer.setData(
						'text/plain',
						JSON.stringify({
							type: 'model',
							id: dragEl.dataset.id
						})
					);
				},
				onUpdate: async (event) => {
					const reorderedIds = [...$visiblePinnedModels];
					const [movedId] = reorderedIds.splice(event.oldIndex, 1);
					reorderedIds.splice(event.newIndex, 0, movedId);

					// Keep pins for models the user cannot see
					settings.set({
						...$settings,
						pinnedModels: [
							...reorderedIds,
							...$pinnedModels.filter((id) => !$visiblePinnedModels.includes(id))
						]
					});
					await updateUserSettings(localStorage.token, { ui: $settings });
				}
			});
		}
	};

	onMount(async () => {
		await tick();
		initPinnedModelsSortable();
	});
</script>

<div class="mt-0.5 pb-1.5" id="pinned-models-list">
	{#each $visiblePinnedModels as modelId (modelId)}
		<PinnedModelItem
			model={$models.find((model) => model.id === modelId)}
			{shiftKey}
			onClick={() => {
				selectedChatId = null;
				chatId.set('');
				if ($mobile) {
					showSidebar.set(false);
				}
			}}
			onUnpin={() => {
				settings.set({
					...$settings,
					pinnedModels: $pinnedModels.filter((id) => id !== modelId)
				});
				updateUserSettings(localStorage.token, { ui: $settings });
			}}
		/>
	{/each}
</div>
