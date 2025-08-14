<script>
	import { createEventDispatcher, getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import { models } from '$lib/stores';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Minus from '$lib/components/icons/Minus.svelte';
	import PencilSolid from '$lib/components/icons/PencilSolid.svelte';
	import { toast } from 'svelte-sonner';
	import AccessControl from '$lib/components/workspace/common/AccessControl.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';

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

	let profileImageUrl = `${WEBUI_BASE_URL}/favicon.png`;
	let description = '';

	let selectedModelId = '';
	let modelIds = [];
	let filterMode = 'include';

	let accessControl = {};

	let imageInputElement;
	let loading = false;
	let showDeleteConfirmDialog = false;

	const addModelHandler = () => {
		if (selectedModelId) {
			modelIds = [...modelIds, selectedModelId];
			selectedModelId = '';
		}
	};

	const submitHandler = () => {
		loading = true;

		if (!name || !id) {
			loading = false;
			toast.error($i18n.t('Name and ID are required, please fill them out'));
			return;
		}

		if (!edit) {
			if ($models.find((model) => model.name === name)) {
				loading = false;
				name = '';
				toast.error($i18n.t('Model name already exists, please choose a different one'));
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
		profileImageUrl = `${WEBUI_BASE_URL}/favicon.png`;
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
	<div>
		<div class=" flex justify-between dark:text-gray-100 px-5 pt-4 pb-2">
			<div class=" text-lg font-medium self-center font-primary">
				{#if edit}
					{$i18n.t('Edit Arena Model')}
				{:else}
					{$i18n.t('Add Arena Model')}
				{/if}
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

		<div class="flex flex-col md:flex-row w-full px-4 pb-4 md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div class="px-1">
						<div class="flex justify-center pb-3">
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
								class="relative rounded-full w-fit h-fit shrink-0"
								type="button"
								on:click={() => {
									imageInputElement.click();
								}}
							>
								<img
									src={profileImageUrl}
									class="size-16 rounded-full object-cover shrink-0"
									alt="Profile"
								/>

								<div
									class="absolute flex justify-center rounded-full bottom-0 left-0 right-0 top-0 h-full w-full overflow-hidden bg-gray-700 bg-fixed opacity-0 transition duration-300 ease-in-out hover:opacity-50"
								>
									<div class="my-auto text-white">
										<PencilSolid className="size-4" />
									</div>
								</div>
							</button>
						</div>
						<div class="flex gap-2">
							<div class="flex flex-col w-full">
								<div class=" mb-0.5 text-xs text-gray-500">{$i18n.t('Name')}</div>

								<div class="flex-1">
									<input
										class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
										type="text"
										bind:value={name}
										placeholder={$i18n.t('Model Name')}
										autocomplete="off"
										required
									/>
								</div>
							</div>

							<div class="flex flex-col w-full">
								<div class=" mb-0.5 text-xs text-gray-500">{$i18n.t('ID')}</div>

								<div class="flex-1">
									<input
										class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
										type="text"
										bind:value={id}
										placeholder={$i18n.t('Model ID')}
										autocomplete="off"
										required
										disabled={edit}
									/>
								</div>
							</div>
						</div>

						<div class="flex flex-col w-full mt-2">
							<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Description')}</div>

							<div class="flex-1">
								<input
									class="w-full text-sm bg-transparent placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
									type="text"
									bind:value={description}
									placeholder={$i18n.t('Enter description')}
									autocomplete="off"
								/>
							</div>
						</div>

						<hr class=" border-gray-100 dark:border-gray-700/10 my-2.5 w-full" />

						<div class="my-2 -mx-2">
							<div class="px-3 py-2 bg-gray-50 dark:bg-gray-950 rounded-lg">
								<AccessControl bind:accessControl />
							</div>
						</div>

						<hr class=" border-gray-100 dark:border-gray-700/10 my-2.5 w-full" />

						<div class="flex flex-col w-full">
							<div class="mb-1 flex justify-between">
								<div class="text-xs text-gray-500">{$i18n.t('Models')}</div>

								<div>
									<button
										class=" text-xs text-gray-500"
										type="button"
										on:click={() => {
											filterMode = filterMode === 'include' ? 'exclude' : 'include';
										}}
									>
										{#if filterMode === 'include'}
											{$i18n.t('Include')}
										{:else}
											{$i18n.t('Exclude')}
										{/if}
									</button>
								</div>
							</div>

							{#if modelIds.length > 0}
								<div class="flex flex-col">
									{#each modelIds as modelId, modelIdx}
										<div class=" flex gap-2 w-full justify-between items-center">
											<div class=" text-sm flex-1 py-1 rounded-lg">
												{$models.find((model) => model.id === modelId)?.name}
											</div>
											<div class="shrink-0">
												<button
													type="button"
													on:click={() => {
														modelIds = modelIds.filter((_, idx) => idx !== modelIdx);
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
									{$i18n.t('Leave empty to include all models or select specific models')}
								</div>
							{/if}
						</div>

						<hr class=" border-gray-100 dark:border-gray-700/10 my-2.5 w-full" />

						<div class="flex items-center">
							<select
								class="w-full py-1 text-sm rounded-lg bg-transparent {selectedModelId
									? ''
									: 'text-gray-500'} placeholder:text-gray-300 dark:placeholder:text-gray-700 outline-hidden"
								bind:value={selectedModelId}
							>
								<option value="">{$i18n.t('Select a model')}</option>
								{#each $models.filter((m) => m?.owned_by !== 'arena') as model}
									<option value={model.id} class="bg-gray-50 dark:bg-gray-700">{model.name}</option>
								{/each}
							</select>

							<div>
								<button
									type="button"
									on:click={() => {
										addModelHandler();
									}}
								>
									<Plus className="size-3.5" strokeWidth="2" />
								</button>
							</div>
						</div>
					</div>

					<div class="flex justify-end pt-3 text-sm font-medium gap-1.5">
						{#if edit}
							<button
								class="px-3.5 py-1.5 text-sm font-medium dark:bg-black dark:hover:bg-gray-950 dark:text-white bg-white text-black hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center"
								type="button"
								on:click={() => {
									showDeleteConfirmDialog = true;
								}}
							>
								{$i18n.t('Delete')}
							</button>
						{/if}

						<button
							class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-950 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center {loading
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
			</div>
		</div>
	</div>
</Modal>
