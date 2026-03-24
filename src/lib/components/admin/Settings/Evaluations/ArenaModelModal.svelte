<script>
	import { createEventDispatcher, getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import Modal from '$lib/components/common/Modal.svelte';
	import { models } from '$lib/stores';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Minus from '$lib/components/icons/Minus.svelte';
	import PencilSolid from '$lib/components/icons/PencilSolid.svelte';
	import SelectDropdown from '$lib/components/common/SelectDropdown.svelte';
	import { toast } from 'svelte-sonner';
	import AccessControl from '$lib/components/workspace/common/AccessControl.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	export let show = false;
	export let edit = false;

	export let model = null;

	let name = '';
	let id = '';

	$: if (name) {
		generateId();
	}

	const generateId = () => {
		if (!edit) {
			id = name
				.toLowerCase()
				.replace(/[^a-z0-9]/g, '-')
				.replace(/-+/g, '-')
				.replace(/^-|-$/g, '');
		}
	};

	let profileImageUrl = '/favicon.png';
	let description = '';

	let selectedModelId = '';
	let modelIds = [];
	let filterMode = 'include';

	let accessControl = {};

	let imageInputElement;
	let loading = false;
	let showDeleteConfirmDialog = false;

	const addModelHandler = () => {
		if (selectedModelId && !modelIds.includes(selectedModelId)) {
			modelIds = [...modelIds, selectedModelId];
			selectedModelId = '';
		}
	};

	$: selectableModels = $models.filter((m) => !modelIds.includes(m.id));
	$: selectableModelOptions = [
		{ value: '', label: 'Select a model' },
		...selectableModels.map((m) => ({ value: m.id, label: m.name }))
	];

	const submitHandler = () => {
		loading = true;

		if (!name || !id) {
			loading = false;
			toast.error('Name and ID are required, please fill them out');
			return;
		}

		if (!edit) {
			if ($models.find((model) => model.name === name)) {
				loading = false;
				name = '';
				toast.error('Model name already exists, please choose a different one');
				return;
			}
		}

		const model = {
			id: id,
			name: name,
			meta: {
				profile_image_url: profileImageUrl,
				description: description || null,
				model_ids: modelIds.length > 0 ? modelIds : null,
				filter_mode: modelIds.length > 0 ? (filterMode ? filterMode : null) : null,
				access_control: accessControl
			}
		};

		dispatch('submit', model);
		loading = false;
		show = false;

		name = '';
		id = '';
		profileImageUrl = '/favicon.png';
		description = '';
		modelIds = [];
		selectedModelId = '';
	};

	const initModel = () => {
		if (model) {
			name = model.name;
			id = model.id;
			profileImageUrl = model.meta.profile_image_url;
			description = model.meta.description;
			modelIds = model.meta.model_ids || [];
			filterMode = model.meta?.filter_mode ?? 'include';
			accessControl = 'access_control' in model.meta ? model.meta.access_control : {};
		}
	};

	$: if (show) {
		initModel();
	}

	onMount(() => {
		initModel();
	});
</script>

<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	on:confirm={() => {
		dispatch('delete', model);
		show = false;
	}}
/>

<Modal size="sm" bind:show>
	<div class="max-h-[85vh] overflow-hidden rounded-xl bg-white dark:bg-gray-950">
		<!-- Header -->
		<div class="flex justify-between items-center px-4 sm:px-6 pt-4 sm:pt-5 pb-3 sm:pb-4 border-b border-gray-200 dark:border-gray-800 bg-gray-50/70 dark:bg-gray-900/40">
			<h2 class="text-xl font-bold text-gray-900 dark:text-gray-100">
				{#if edit}
					{$i18n.t('Edit Arena Model')}
				{:else}
					{$i18n.t('Add Arena Model')}
				{/if}
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
		<div class="flex flex-col md:flex-row w-full px-4 sm:px-6 py-4 sm:py-5 dark:text-gray-200 overflow-y-auto max-h-[calc(85vh-72px)]">
			<div class="flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full space-y-5"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<!-- Profile Image Section -->
					<div class="flex flex-col items-center gap-3 p-4 bg-gray-50 dark:bg-gray-900/50 rounded-xl">
						<input
							bind:this={imageInputElement}
							type="file"
							hidden
							accept="image/*"
							on:change={(e) => {
								const files = e.target.files ?? [];
								let reader = new FileReader();
								reader.onload = (event) => {
									let originalImageUrl = `${event.target.result}`;

									const img = new Image();
									img.src = originalImageUrl;

									img.onload = function () {
										const canvas = document.createElement('canvas');
										const ctx = canvas.getContext('2d');

										// Calculate the aspect ratio of the image
										const aspectRatio = img.width / img.height;

										// Calculate the new width and height to fit within 250x250
										let newWidth, newHeight;
										if (aspectRatio > 1) {
											newWidth = 250 * aspectRatio;
											newHeight = 250;
										} else {
											newWidth = 250;
											newHeight = 250 / aspectRatio;
										}

										// Set the canvas size
										canvas.width = 250;
										canvas.height = 250;

										// Calculate the position to center the image
										const offsetX = (250 - newWidth) / 2;
										const offsetY = (250 - newHeight) / 2;

										// Draw the image on the canvas
										ctx.drawImage(img, offsetX, offsetY, newWidth, newHeight);

										// Get the base64 representation of the compressed image
										const compressedSrc = canvas.toDataURL('image/jpeg');

										// Display the compressed image
										profileImageUrl = compressedSrc;

										e.target.files = null;
									};
								};

								if (
									files.length > 0 &&
									['image/gif', 'image/webp', 'image/jpeg', 'image/png'].includes(
										files[0]['type']
									)
								) {
									reader.readAsDataURL(files[0]);
								}
							}}
						/>

						<button
							class="relative group"
							type="button"
							on:click={() => {
								imageInputElement.click();
							}}
						>
							<div class="relative w-20 h-20 rounded-full overflow-hidden ring-4 ring-gray-200 dark:ring-gray-700 transition-all duration-200 group-hover:ring-blue-500">
								<img
									src={profileImageUrl}
									class="w-full h-full object-cover"
									alt="Profile"
								/>

								<div
									class="absolute inset-0 flex items-center justify-center bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity duration-200"
								>
									<PencilSolid className="size-5 text-white" />
								</div>
							</div>
						</button>
						<p class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Click to change image')}</p>
					</div>

					<!-- Name and ID Section -->
					<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
						<div class="space-y-2">
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
								{$i18n.t('Name')}
								<span class="text-red-500">*</span>
							</label>
							<input
								class="w-full px-3 py-2.5 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg placeholder:text-gray-400 dark:placeholder:text-gray-500 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all duration-200"
								type="text"
								bind:value={name}
								placeholder={$i18n.t('Model Name')}
								autocomplete="off"
								required
							/>
						</div>

						<div class="space-y-2">
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
								{$i18n.t('ID')}
								<span class="text-red-500">*</span>
							</label>
							<input
								class="w-full px-3 py-2.5 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg placeholder:text-gray-400 dark:placeholder:text-gray-500 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
								type="text"
								bind:value={id}
								placeholder={$i18n.t('Model ID')}
								autocomplete="off"
								required
								disabled={edit}
							/>
						</div>
					</div>

					<!-- Description Section -->
					<div class="space-y-2">
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
							{$i18n.t('Description')}
						</label>
						<input
							class="w-full px-3 py-2.5 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg placeholder:text-gray-400 dark:placeholder:text-gray-500 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all duration-200"
							type="text"
							bind:value={description}
							placeholder={$i18n.t('Enter description')}
							autocomplete="off"
						/>
					</div>

					<!-- Access Control Section -->
					<div class="space-y-2">
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
							{$i18n.t('Access Control')}
						</label>
						<div class="p-4 bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-gray-200 dark:border-gray-800">
							<AccessControl bind:accessControl />
						</div>
					</div>

					<!-- Models Section -->
					<div class="space-y-3">
						<div class="flex justify-between items-center">
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
								{$i18n.t('Models')}
							</label>
							<div class="inline-flex rounded-lg border border-gray-300 dark:border-gray-700 overflow-hidden">
								<button
									class="px-3 py-1.5 text-xs font-medium transition-all duration-200 {filterMode === 'include'
										? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
										: 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400'}"
									type="button"
									on:click={() => {
										filterMode = 'include';
									}}
								>
									{$i18n.t('Include')}
								</button>
								<button
									class="px-3 py-1.5 text-xs font-medium border-l border-gray-300 dark:border-gray-700 transition-all duration-200 {filterMode === 'exclude'
										? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
										: 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400'}"
									type="button"
									on:click={() => {
										filterMode = 'exclude';
									}}
								>
									{$i18n.t('Exclude')}
								</button>
							</div>
						</div>

						<!-- Models List -->
						<div class="min-h-[100px] p-3 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg">
							{#if modelIds.length > 0}
								<div class="space-y-2">
									{#each modelIds as modelId, modelIdx}
										<div class="flex items-center justify-between p-2.5 bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-gray-200 dark:border-gray-700 group hover:border-gray-300 dark:hover:border-gray-600 transition-colors duration-200">
											<span class="text-sm text-gray-900 dark:text-gray-100 font-medium">
												{$models.find((model) => model.id === modelId)?.name}
											</span>
											<button
												class="p-1.5 rounded-lg text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors duration-200"
												type="button"
												on:click={() => {
													modelIds = modelIds.filter((_, idx) => idx !== modelIdx);
												}}
											>
												<Minus strokeWidth="2" className="size-4" />
											</button>
										</div>
									{/each}
								</div>
							{:else}
								<div class="flex flex-col items-center justify-center py-6">
									<svg class="w-12 h-12 text-gray-300 dark:text-gray-700 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
									</svg>
									<p class="text-xs text-gray-500 dark:text-gray-400 text-center max-w-xs">
										{$i18n.t('Leave empty to include all models or select specific models')}
									</p>
								</div>
							{/if}
						</div>

						<!-- Add Model Section -->
						<div class="flex gap-2">
							<div class="flex-1">
								<SelectDropdown
									value={selectedModelId}
									options={selectableModelOptions}
									on:change={(e) => {
										selectedModelId = e.detail.value;
									}}
								/>
							</div>

							<button
								class="flex-shrink-0 p-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
								type="button"
								disabled={!selectedModelId || modelIds.includes(selectedModelId)}
								on:click={() => {
									addModelHandler();
								}}
							>
								<Plus className="size-5" strokeWidth="2" />
							</button>
						</div>
					</div>

					<!-- Action Buttons -->
					<div class="flex justify-end gap-2 pt-2 border-t border-gray-200 dark:border-gray-800">
						{#if edit}
							<button
								class="px-4 py-2.5 text-sm font-medium bg-white dark:bg-gray-800 text-red-600 dark:text-red-400 border border-red-300 dark:border-red-700 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all duration-200 rounded-lg"
								type="button"
								on:click={() => {
									showDeleteConfirmDialog = true;
								}}
							>
								{$i18n.t('Delete')}
							</button>
						{/if}

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
			</div>
		</div>
	</div>
</Modal>