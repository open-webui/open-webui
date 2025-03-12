<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { models, settings } from '$lib/stores';
	import { updateUserSettings } from '$lib/apis/users';

	export let selectedModels = [''];

	// Custom models obey have the convention of using only characters
	// This excludes stock models.
	// This can later be changed to testing for a marker tag in info.meta.tags
	const onlyCustomModels = ({ id }) => /^[a-z]+$/.test(id);

	$: modelsUi = $models
		.filter(onlyCustomModels)
		.map((model) => ({
			id: model.id,
			modelDisplayName: model.name,
		}));

	const save = async () => {
		settings.set({ ...$settings, models: selectedModels });
		await updateUserSettings(localStorage.token, { ui: $settings });
	}

	const select = (id) => {
		selectedModels = [id];
		save();
	}
</script>

<div class="flex flex-row items-start gap-3">
	{#each modelsUi as { id, modelDisplayName }}
		<button
			data-model-id={id}
			on:click={() => select(id)}
			class="px-4 py-1 border-2 border-sky-900 bg-white-500 hover:bg-sky-800 text-black hover:text-white transition rounded-3xl"
		>
			{modelDisplayName}
		</button>
	{/each}
</div>
