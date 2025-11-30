<script>
	import { toast } from 'svelte-sonner';

	import { createEventDispatcher, getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import { models } from '$lib/stores';
	import { deleteAllModels } from '$lib/apis/models';
	import { getModelsConfig, setModelsConfig } from '$lib/apis/configs';

	import Modal from '$lib/components/common/Modal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ModelList from './ModelList.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Minus from '$lib/components/icons/Minus.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import ModelSelector from './ModelSelector.svelte';
	import Model from '../Evaluations/Model.svelte';

	export let show = false;
	export let initHandler = () => {};

	let config = null;

	let selectedModelId = '';
	let defaultModelIds = [];

	let selectedPinnedModelId = '';
	let defaultPinnedModelIds = [];

	let modelIds = [];

	let sortKey = '';
	let sortOrder = '';

	let loading = false;
	let showResetModal = false;

	$: if (show) {
		init();
	}
	const init = async () => {
		config = await getModelsConfig(localStorage.token);

		if (config?.DEFAULT_MODELS) {
			defaultModelIds = (config?.DEFAULT_MODELS).split(',').filter((id) => id);
		} else {
			defaultModelIds = [];
		}

		if (config?.DEFAULT_PINNED_MODELS) {
			defaultPinnedModelIds = (config?.DEFAULT_PINNED_MODELS).split(',').filter((id) => id);
		} else {
			defaultPinnedModelIds = [];
		}

		const modelOrderList = config.MODEL_ORDER_LIST || [];
		const allModelIds = $models.map((model) => model.id);

		// Create a Set for quick lookup of ordered IDs
		const orderedSet = new Set(modelOrderList);

		modelIds = [
			// Add all IDs from MODEL_ORDER_LIST that exist in allModelIds
			...modelOrderList.filter((id) => orderedSet.has(id) && allModelIds.includes(id)),
			// Add remaining IDs not in MODEL_ORDER_LIST, sorted alphabetically
			...allModelIds.filter((id) => !orderedSet.has(id)).sort((a, b) => a.localeCompare(b))
		];

		sortKey = '';
		sortOrder = '';
	};
	const submitHandler = async () => {
		loading = true;

		const res = await setModelsConfig(localStorage.token, {
			DEFAULT_MODELS: defaultModelIds.join(','),
			DEFAULT_PINNED_MODELS: defaultPinnedModelIds.join(','),
			MODEL_ORDER_LIST: modelIds
		});

		if (res) {
			toast.success($i18n.t('Models configuration saved successfully'));
			initHandler();
			show = false;
		} else {
			toast.error($i18n.t('Failed to save models configuration'));
		}

		loading = false;
	};

	onMount(async () => {
		init();
	});
</script>

<ConfirmDialog
	title={$i18n.t('Reset All Models')}
	message={$i18n.t('This will delete all models including custom models and cannot be undone.')}
	bind:show={showResetModal}
	onConfirm={async () => {
		const res = deleteAllModels(localStorage.token);
		if (res) {
			toast.success($i18n.t('All models deleted successfully'));
			initHandler();
		}
	}}
/>

<Modal size="sm" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-100 px-5 pt-4 pb-2">
			<div class=" text-lg font-medium self-center font-primary">
				{$i18n.t('Settings')}
			</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-5 pb-4 md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				{#if config}
					<form
						class="flex flex-col w-full"
						on:submit|preventDefault={() => {
							submitHandler();
						}}
					>
						<div>
							<div class="flex flex-col w-full">
								<button
									class="mb-1 flex gap-2"
									type="button"
									on:click={() => {
										sortKey = 'model';

										if (sortOrder === 'asc') {
											sortOrder = 'desc';
										} else {
											sortOrder = 'asc';
										}

										modelIds = modelIds
											.filter((id) => id !== '')
											.sort((a, b) => {
												const nameA = $models.find((model) => model.id === a)?.name || a;
												const nameB = $models.find((model) => model.id === b)?.name || b;
												return sortOrder === 'desc'
													? nameA.localeCompare(nameB)
													: nameB.localeCompare(nameA);
											});
									}}
								>
									<div class="text-xs text-gray-500">{$i18n.t('Reorder Models')}</div>

									{#if sortKey === 'model'}
										<span class="font-normal self-center">
											{#if sortOrder === 'asc'}
												<ChevronUp className="size-3" />
											{:else}
												<ChevronDown className="size-3" />
											{/if}
										</span>
									{:else}
										<span class="invisible">
											<ChevronUp className="size-3" />
										</span>
									{/if}
								</button>

								<ModelList bind:modelIds />
							</div>
						</div>

						<hr class=" border-gray-100 dark:border-gray-700/10 my-2.5 w-full" />

						<ModelSelector
							title={$i18n.t('Default Models')}
							models={$models}
							bind:modelIds={defaultModelIds}
						/>

						<hr class=" border-gray-100 dark:border-gray-700/10 my-2.5 w-full" />

						<ModelSelector
							title={$i18n.t('Default Pinned Models')}
							models={$models}
							bind:modelIds={defaultPinnedModelIds}
						/>

						<div class="flex justify-between pt-3 text-sm font-medium gap-1.5">
							<Tooltip content={$i18n.t('This will delete all models including custom models')}>
								<button
									class="px-3.5 py-1.5 text-sm font-medium dark:bg-black dark:hover:bg-gray-950 dark:text-white bg-white text-black hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center"
									type="button"
									on:click={() => {
										showResetModal = true;
									}}
								>
									<!-- {$i18n.t('Delete All Models')} -->
									{$i18n.t('Reset All Models')}
								</button>
							</Tooltip>

							<button
								class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center {loading
									? ' cursor-not-allowed'
									: ''}"
								type="submit"
								disabled={loading}
							>
								{$i18n.t('Save')}

								{#if loading}
									<div class="ml-2 self-center">
										<Spinner />
									</div>
								{/if}
							</button>
						</div>
					</form>
				{:else}
					<div>
						<Spinner className="size-5" />
					</div>
				{/if}
			</div>
		</div>
	</div>
</Modal>
