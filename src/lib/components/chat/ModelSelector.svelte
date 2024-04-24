<script lang="ts">
	import { Collapsible } from 'bits-ui';

	import { setDefaultModels } from '$lib/apis/configs';
	import { models, showSettings, settings, user } from '$lib/stores';
	import { onMount, tick, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Selector from './ModelSelector/Selector.svelte';
	import Tooltip from '../common/Tooltip.svelte';

	const i18n = getContext('i18n');

	type Model = {
		name: string;
		paused: boolean;
	};

	export let selectedModels = [''];
	export let renderedModels: Model[] = [{ name: '', paused: false }];

	const updatePreferences = (preferences: string[]) => {
		if (
			preferences.join(',') ===
			renderedModels
				.filter((models) => !models.paused)
				.map((it) => it.name)
				.join(',')
		) {
			return;
		}

		const newRenderedModels = preferences.map((model) => ({
			name: model,
			paused: renderedModels.find((it) => it.name === model)?.paused ?? false
		}));
		if (JSON.stringify(newRenderedModels) !== JSON.stringify(renderedModels)) {
			renderedModels = newRenderedModels;
		}
	};

	const setRenderedModels = (models: Model[]) => {
		renderedModels = models;

		if (
			models
				.filter((model) => !model.paused)
				.map((model) => model.name)
				.join(',') !== selectedModels.join(',')
		) {
			selectedModels = models.filter((model) => !model.paused).map((model) => model.name);
		}
	};

	$: updatePreferences(selectedModels);

	export let disabled = false;

	const saveDefaultModel = async () => {
		const hasEmptyModel = renderedModels.filter((it) => it.name === '');
		if (hasEmptyModel.length) {
			toast.error($i18n.t('Choose a model before saving...'));
			return;
		}
		settings.set({ ...$settings, models: renderedModels.map((model) => model.name) });
		localStorage.setItem('settings', JSON.stringify($settings));

		if ($user.role === 'admin') {
			console.log('setting default models globally');
			await setDefaultModels(
				localStorage.token,
				renderedModels.map((model) => model.name).join(',')
			);
		}
		toast.success($i18n.t('Default model updated'));
	};

	const togglePause = (model: Model) => {
		model.paused = !model.paused;
		setRenderedModels(renderedModels);
	};

	$: if (renderedModels.length > 0 && $models.length > 0) {
		setRenderedModels(
			renderedModels.map((model) => ({
				name: $models.map((m) => m.id).includes(model.name) ? model.name : '',
				paused: model.paused
			}))
		);
	}
</script>

<div class="flex flex-col mt-0.5 w-full">
	{#each renderedModels as renderedModel, renderedModelIdx}
		<div class="flex w-full">
			<div class="overflow-hidden w-full">
				<div class="mr-0.5 max-w-full">
					<Selector
						placeholder={$i18n.t('Select a model')}
						items={$models
							.filter((model) => model.name !== 'hr')
							.map((model) => ({
								value: model.id,
								label: model.name,
								info: model
							}))}
						bind:value={renderedModel.name}
					/>
				</div>
			</div>

			{#if renderedModelIdx === 0}
				<div class="  self-center mr-2 disabled:text-gray-600 disabled:hover:text-gray-600">
					<Tooltip content="Add Model">
						<button
							class=" "
							{disabled}
							on:click={() => {
								setRenderedModels([...renderedModels, { name: '', paused: false }]);
							}}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="w-4 h-4"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="M12 6v12m6-6H6" />
							</svg>
						</button>
					</Tooltip>
				</div>
			{:else}
				<div class="  self-center disabled:text-gray-600 disabled:hover:text-gray-600 mr-2">
					<Tooltip content="Remove Model">
						<button
							{disabled}
							on:click={() => {
								renderedModels.splice(renderedModelIdx, 1);
								setRenderedModels(renderedModels);
							}}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="w-4 h-4"
							>
								<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 12h-15" />
							</svg>
						</button>
					</Tooltip>
				</div>
			{/if}
			<div class=" self-center disabled:text-gray-600 disabled:hover:text-gray-600 mr-2">
				<Tooltip
					content={typeof renderedModel && renderedModel.paused ? 'Resume Model' : 'Pause Model'}
				>
					<button class=" " on:click={() => togglePause(renderedModel)} {disabled}>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="w-4 h-4"
						>
							{#if renderedModel.paused}
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M8.5 6.5l9 5.5-9 5.5V6.5z"
								/>
							{:else}
								<path stroke-linecap="round" stroke-linejoin="round" d="M 9 6 v 12 m 6 -12 v 12" />
							{/if}
						</svg>
					</button>
				</Tooltip>
			</div>
		</div>
	{/each}
</div>

<div class="text-left mt-0.5 ml-1 text-[0.7rem] text-gray-500">
	<button on:click={saveDefaultModel}> {$i18n.t('Set as default')}</button>
</div>
