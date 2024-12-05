<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { models, user } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';

	const dispatch = createEventDispatcher();
	import { getModels } from '$lib/apis';
	import { getConfig, updateConfig } from '$lib/apis/evaluations';

	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Model from './Evaluations/Model.svelte';
	import ArenaModelModal from './Evaluations/ArenaModelModal.svelte';

	const i18n = getContext('i18n');

	let config = null;
	let showAddModel = false;

	const submitHandler = async () => {
		config = await updateConfig(localStorage.token, config).catch((err) => {
			toast.error(err);
			return null;
		});

		if (config) {
			toast.success('Settings saved successfully');
			models.set(await getModels(localStorage.token));
		}
	};

	const addModelHandler = async (model) => {
		config.EVALUATION_ARENA_MODELS.push(model);
		config.EVALUATION_ARENA_MODELS = [...config.EVALUATION_ARENA_MODELS];

		await submitHandler();
		models.set(await getModels(localStorage.token));
	};

	const editModelHandler = async (model, modelIdx) => {
		config.EVALUATION_ARENA_MODELS[modelIdx] = model;
		config.EVALUATION_ARENA_MODELS = [...config.EVALUATION_ARENA_MODELS];

		await submitHandler();
		models.set(await getModels(localStorage.token));
	};

	const deleteModelHandler = async (modelIdx) => {
		config.EVALUATION_ARENA_MODELS = config.EVALUATION_ARENA_MODELS.filter(
			(m, mIdx) => mIdx !== modelIdx
		);

		await submitHandler();
		models.set(await getModels(localStorage.token));
	};

	onMount(async () => {
		if ($user.role === 'admin') {
			config = await getConfig(localStorage.token).catch((err) => {
				toast.error(err);
				return null;
			});
		}
	});
</script>

<ArenaModelModal
	bind:show={showAddModel}
	on:submit={async (e) => {
		addModelHandler(e.detail);
	}}
/>

<form
	class="flex flex-col h-full justify-between text-sm"
	on:submit|preventDefault={() => {
		submitHandler();
		dispatch('save');
	}}
>
	<div class="overflow-y-scroll scrollbar-hidden h-full">
		{#if config !== null}
			<div class="">
				<div class="text-sm font-medium mb-2">{$i18n.t('General Settings')}</div>

				<div class=" mb-2">
					<div class="flex justify-between items-center text-xs">
						<div class=" text-xs font-medium">{$i18n.t('Arena Models')}</div>

						<Tooltip content={$i18n.t(`Message rating should be enabled to use this feature`)}>
							<Switch bind:state={config.ENABLE_EVALUATION_ARENA_MODELS} />
						</Tooltip>
					</div>
				</div>

				{#if config.ENABLE_EVALUATION_ARENA_MODELS}
					<hr class=" border-gray-50 dark:border-gray-700/10 my-2" />

					<div class="flex justify-between items-center mb-2">
						<div class="text-sm font-medium">{$i18n.t('Manage Arena Models')}</div>

						<div>
							<Tooltip content={$i18n.t('Add Arena Model')}>
								<button
									class="p-1"
									type="button"
									on:click={() => {
										showAddModel = true;
									}}
								>
									<Plus />
								</button>
							</Tooltip>
						</div>
					</div>

					<div class="flex flex-col gap-2">
						{#if (config?.EVALUATION_ARENA_MODELS ?? []).length > 0}
							{#each config.EVALUATION_ARENA_MODELS as model, index}
								<Model
									{model}
									on:edit={(e) => {
										editModelHandler(e.detail, index);
									}}
									on:delete={(e) => {
										deleteModelHandler(index);
									}}
								/>
							{/each}
						{:else}
							<div class=" text-center text-xs text-gray-500">
								{$i18n.t(
									`Using the default arena model with all models. Click the plus button to add custom models.`
								)}
							</div>
						{/if}
					</div>
				{/if}
			</div>
		{:else}
			<div class="flex h-full justify-center">
				<div class="my-auto">
					<Spinner className="size-6" />
				</div>
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
