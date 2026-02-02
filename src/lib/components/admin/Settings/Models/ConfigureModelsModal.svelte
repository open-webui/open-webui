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
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';

	export let show = false;
	export let initHandler = () => {};

	let config = null;

	let selectedModelId = '';
	let defaultModelIds = [];
	let modelIds = [];

	let sortKey = '';
	let sortOrder = '';

	let loading = false;
	let showResetModal = false;

	$: if (show) {
		init();
	}

	$: if (selectedModelId) {
		onModelSelect();
	}

	const onModelSelect = () => {
		if (selectedModelId === '') {
			return;
		}

		if (defaultModelIds.includes(selectedModelId)) {
			selectedModelId = '';
			return;
		}

		defaultModelIds = [...defaultModelIds, selectedModelId];
		selectedModelId = '';
	};

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

		sortKey = '';
		sortOrder = '';
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
		<!-- Header -->
		<div class="flex justify-between items-center px-6 pt-5 pb-4 border-b border-gray-200 dark:border-gray-800">
			<h2 class="text-xl font-bold text-gray-900 dark:text-gray-100">
				{$i18n.t('Settings')}
			</h2>
			<button
				class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors duration-200"
				on:click={() => {
					show = false;
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5 text-gray-500 dark:text-gray-400"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>

		<!-- Content -->
		<div class="flex flex-col md:flex-row w-full px-6 py-5 dark:text-gray-200">
			<div class="flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				{#if config}
					<form
						class="flex flex-col w-full space-y-5"
						on:submit|preventDefault={() => {
							submitHandler();
						}}
					>
						<!-- Reorder Models Section -->
						<div class="space-y-3">
							<div class="flex items-center justify-between">
								<label class="text-sm font-medium text-gray-700 dark:text-gray-300">
									{$i18n.t('Reorder Models')}
								</label>
								<button
									class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors duration-200"
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
									<span>{sortKey === 'model' && sortOrder === 'asc' ? 'A-Z' : 'Z-A'}</span>
									{#if sortKey === 'model'}
										{#if sortOrder === 'asc'}
											<ChevronUp className="size-3.5" />
										{:else}
											<ChevronDown className="size-3.5" />
										{/if}
									{:else}
										<ChevronUp className="size-3.5 opacity-30" />
									{/if}
								</button>
							</div>

							<div class="p-3 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg">
								<ModelList bind:modelIds />
							</div>
						</div>

						<!-- Default Models Section -->
						<div class="space-y-3">
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
								{$i18n.t('Default Models')}
							</label>

							<!-- Select Dropdown -->
							<select
								class="w-full px-3 py-2.5 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg {selectedModelId
									? 'text-gray-900 dark:text-gray-100'
									: 'text-gray-500 dark:text-gray-400'} focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all duration-200"
								bind:value={selectedModelId}
							>
								<option value="">{$i18n.t('Select a model')}</option>
								{#each $models as model}
									<option value={model.id} class="bg-white dark:bg-gray-800">{model.name}</option>
								{/each}
							</select>

							<!-- Selected Models List -->
							<div class="min-h-[80px] p-3 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg">
								{#if defaultModelIds.length > 0}
									<div class="space-y-2">
										{#each defaultModelIds as modelId, modelIdx}
											<div class="flex items-center justify-between p-2.5 bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-gray-200 dark:border-gray-700 group hover:border-gray-300 dark:hover:border-gray-600 transition-colors duration-200">
												<span class="text-sm text-gray-900 dark:text-gray-100 font-medium flex-1">
													{$models.find((model) => model.id === modelId)?.name}
												</span>
												<button
													class="p-1.5 rounded-lg text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors duration-200"
													type="button"
													on:click={() => {
														defaultModelIds = defaultModelIds.filter(
															(_, idx) => idx !== modelIdx
														);
													}}
												>
													<Minus strokeWidth="2" className="size-4" />
												</button>
											</div>
										{/each}
									</div>
								{:else}
									<div class="flex flex-col items-center justify-center py-4">
										<svg class="w-10 h-10 text-gray-300 dark:text-gray-700 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
										</svg>
										<p class="text-xs text-gray-500 dark:text-gray-400">
											{$i18n.t('No models selected')}
										</p>
									</div>
								{/if}
							</div>
						</div>

						<!-- Action Buttons -->
						<div class="flex justify-between gap-2 pt-2 border-t border-gray-200 dark:border-gray-800">
							<Tooltip content={$i18n.t('This will delete all models including custom models')}>
								<button
									class="px-4 py-2.5 text-sm font-medium bg-white dark:bg-gray-800 text-red-600 dark:text-red-400 border border-red-300 dark:border-red-700 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all duration-200 rounded-lg"
									type="button"
									on:click={() => {
										showResetModal = true;
									}}
								>
									{$i18n.t('Reset All Models')}
								</button>
							</Tooltip>

							<button
								class="px-5 py-2.5 text-sm font-semibold bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white transition-all duration-200 rounded-lg shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
								type="submit"
								disabled={loading}
							>
								<span>{$i18n.t('Save')}</span>

								{#if loading}
									<svg
										class="w-4 h-4 animate-spin"
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
								{/if}
							</button>
						</div>
					</form>
				{:else}
					<div class="flex flex-col items-center justify-center py-8 gap-3">
						<Spinner className="size-8" />
						<p class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Loading configuration...')}</p>
					</div>
				{/if}
			</div>
		</div>
	</div>
</Modal>