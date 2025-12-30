<script lang="ts">
	import { getContext } from 'svelte';
	import { models } from '$lib/stores';

	const i18n = getContext('i18n');
	const LUXOR_MODEL_ID = 'luxor:latest';

	export let selectedModels = [''];

	$: if (selectedModels.length !== 1 || selectedModels[0] !== LUXOR_MODEL_ID) {
		selectedModels = [LUXOR_MODEL_ID];
	}

	$: luxorModel = $models.find((model) => model.id === LUXOR_MODEL_ID);
	$: luxorLabel = luxorModel?.name ?? $i18n.t('Luxor');
</script>

<div class="flex flex-col w-full items-start self-start">
	<div class="flex w-full max-w-fit">
		<div class="flex items-center text-lg font-primary text-gray-800 dark:text-gray-100">
			{luxorLabel}
		</div>
	</div>
</div>
