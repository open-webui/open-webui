<script>
	import { toast } from 'svelte-sonner';

	import { createEventDispatcher, getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import { models } from '$lib/stores';
	import { deleteAllModels } from '$lib/apis/models';

	import Modal from '$lib/components/common/Modal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ModelList from './ModelList.svelte';
	import { getModelsConfig, setModelsConfig } from '$lib/apis/configs';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Minus from '$lib/components/icons/Minus.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';

	export let show = false;
	export let initHandler = () => {};

	let config = null;

	let selectedModelId = '';
	let defaultModelIds = [];
	let modelIds = [];

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
	};
	const submitHandler = async () => {
		loading = true;

		const res = await setModelsConfig(localStorage.token, {
			DEFAULT_MODELS: defaultModelIds.join(','),
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
				{$i18n.t('Configure Models')}
			</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
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
								<div class="mb-1 flex justify-between">
									<div class="text-xs text-gray-500">{$i18n.t('Reorder Models')}</div>
								</div>

								<ModelList bind:modelIds />
							</div>
						</div>

						<hr class=" border-gray-100 dark:border-gray-700/10 my-2.5 w-full" />

						<div>
							<div class="flex flex-col w-full">
								<div class="mb-1 flex justify-between">
									<div class="text-xs text-gray-500">{$i18n.t('Default Models')}</div>
								</div>

								{#if defaultModelIds.length > 0}
									<div class="flex flex-col">
										{#each defaultModelIds as modelId, modelIdx}
											<div class=" flex gap-2 w-full justify-between items-center">
												<div class=" text-sm flex-1 py-1 rounded-lg">
													{$models.find((model) => model.id === modelId)?.name}
												</div>
												<div class="flex-shrink-0">
													<button
														type="button"
														on:click={() => {
															defaultModelIds = defaultModelIds.filter(
																(_, idx) => idx !== modelIdx
															);
														}}
													>
														<Minus strokeWidth="2" className="size-3.5" />
													</button>
												</div>
											</div>
										{/each}
									</div>
								{:else}
									<div class="text-gray-500 text-xs text-center py-2">
										{$i18n.t('No models selected')}
									</div>
								{/if}

								<hr class=" border-gray-100 dark:border-gray-700/10 my-2.5 w-full" />

								<div class="flex items-center">
									<select
										class="w-full py-1 text-sm rounded-lg bg-transparent {selectedModelId
											? ''
											: 'text-gray-500'} placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-none"
										bind:value={selectedModelId}
									>
										<option value="">{$i18n.t('Select a model')}</option>
										{#each $models as model}
											<option value={model.id} class="bg-gray-50 dark:bg-gray-700"
												>{model.name}</option
											>
										{/each}
									</select>

									<div>
										<button
											type="button"
											on:click={() => {
												if (selectedModelId === '') {
													return;
												}

												if (defaultModelIds.includes(selectedModelId)) {
													return;
												}

												defaultModelIds = [...defaultModelIds, selectedModelId];
												selectedModelId = '';
											}}
										>
											<Plus className="size-3.5" strokeWidth="2" />
										</button>
									</div>
								</div>
							</div>
						</div>

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
										<svg
											class=" w-4 h-4"
											viewBox="0 0 24 24"
											fill="currentColor"
											xmlns="http://www.w3.org/2000/svg"
											><style>
												.spinner_ajPY {
													transform-origin: center;
													animation: spinner_AtaB 0.75s infinite linear;
												}
												@keyframes spinner_AtaB {
													100% {
														transform: rotate(360deg);
													}
												}
											</style><path
												d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z"
												opacity=".25"
											/><path
												d="M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z"
												class="spinner_ajPY"
											/></svg
										>
									</div>
								{/if}
							</button>
						</div>
					</form>
				{:else}
					<div>
						<Spinner />
					</div>
				{/if}
			</div>
		</div>
	</div>
</Modal>
