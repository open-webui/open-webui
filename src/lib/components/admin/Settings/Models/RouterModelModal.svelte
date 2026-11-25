<script>
	import { createEventDispatcher, getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import { baseModels, models } from '$lib/stores';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Minus from '$lib/components/icons/Minus.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Photo from '$lib/components/icons/Photo.svelte';
	import { toast } from 'svelte-sonner';
	import AccessControlModal from '$lib/components/workspace/common/AccessControlModal.svelte';
	import AccessButton from '$lib/components/common/AccessButton.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import LanguageModeSelect from '$lib/components/common/LanguageModeSelect.svelte';
	import LocalizedField from '$lib/components/common/LocalizedField.svelte';
	import ModelSettingsSection from '$lib/components/workspace/Models/ModelSettingsSection.svelte';

	export let show = false;
	export let edit = false;

	export let model = null;
	/** @type {(model: object, accessGrants: object[]) => Promise<boolean>} */
	export let onSubmit = async () => true;

	let name = '';
	let locale = '';
	let translations = {};
	let originalMeta = {};
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

	// LICENSE covers this Open WebUI fallback logo.
	// Do not alter, remove, obscure, or replace it except as LICENSE permits:
	// https://docs.openwebui.com/license.
	let profileImageUrl = `${WEBUI_BASE_URL}/favicon.png`;
	let description = '';

	const DEFAULT_DECISIONS = {
		api_base_url: 'https://api.openai.com/v1',
		api_key: '',
		model: 'gpt-6-luna',
		threshold: 0.5,
		prompt: ''
	};

	let patternRoutes = [];
	let conditionRoutes = [];
	let defaultRoutes = [];
	let strategy = 'first';
	let decisions = { ...DEFAULT_DECISIONS };

	let accessGrants = [];
	let showAccessControlModal = false;
	let defaultOpen = false;

	$: targetModels = ($models ?? []).filter((m) => m?.owned_by !== 'router');

	const countSummary = (routes) => (routes.length > 0 ? `${routes.length}` : $i18n.t('None'));
	$: defaultSummary =
		defaultRoutes.length === 0
			? $i18n.t('None')
			: defaultRoutes.length === 1
				? (targetModels.find((m) => m.id === defaultRoutes[0].model_id)?.name ??
					defaultRoutes[0].model_id)
				: `${strategy === 'random' ? $i18n.t('Random') : $i18n.t('First')} · ${defaultRoutes.length}`;

	let imageInputElement;
	let loading = false;
	let showDeleteConfirmDialog = false;

	const moveItem = (items, idx, offset) => {
		const next = [...items];
		[next[idx], next[idx + offset]] = [next[idx + offset], next[idx]];
		return next;
	};

	const initRoutes = (routes = []) => {
		patternRoutes = routes
			.filter((route) => route.pattern)
			.map((route) => ({ model_id: route.model_id, pattern: route.pattern }));
		conditionRoutes = routes
			.filter((route) => route.condition)
			.map((route) => ({ model_id: route.model_id, condition: route.condition }));
		defaultRoutes = routes
			.filter((route) => !(route.pattern || route.condition))
			.map((route) => ({ model_id: route.model_id }));
	};

	const submitHandler = async () => {
		loading = true;

		if (!name || !id) {
			loading = false;
			toast.error($i18n.t('Name and ID are required, please fill them out'));
			return;
		}

		if (!edit) {
			if ($baseModels.find((model) => model.name === name)) {
				loading = false;
				toast.error($i18n.t('Model name already exists, please choose a different one'));
				return;
			}
		}

		const conditions = conditionRoutes.filter((route) => route.model_id && route.condition.trim());
		const routes = [
			...patternRoutes
				.filter((route) => route.model_id && route.pattern.trim())
				.map((route) => ({ model_id: route.model_id, pattern: route.pattern })),
			...conditions.map((route) => ({
				model_id: route.model_id,
				condition: route.condition.trim()
			})),
			...defaultRoutes
				.filter((route) => route.model_id)
				.map((route) => ({ model_id: route.model_id }))
		];

		if (routes.length === 0) {
			loading = false;
			toast.error($i18n.t('Add at least one route.'));
			return;
		}

		const model = {
			id: id,
			name: name,
			meta: {
				...originalMeta,
				i18n: translations,
				profile_image_url: profileImageUrl,
				description: description || null,
				routes,
				strategy
			},
			config: conditions.length > 0 ? { decisions } : {}
		};

		try {
			if ((await onSubmit(model, accessGrants)) === false) return;
		} catch (error) {
			toast.error(String(error));
			return;
		} finally {
			loading = false;
		}
		show = false;

		name = '';
		id = '';
		// LICENSE covers this Open WebUI fallback logo.
		// Do not alter, remove, obscure, or replace it except as LICENSE permits:
		// https://docs.openwebui.com/license.
		profileImageUrl = `${WEBUI_BASE_URL}/favicon.png`;
		description = '';
		initRoutes();
		strategy = 'first';
		decisions = { ...DEFAULT_DECISIONS };
	};

	const initModel = () => {
		locale = '';
		// Access is saved on the model row, not in router settings.
		originalMeta = Object.fromEntries(
			Object.entries(structuredClone(model?.meta ?? {})).filter(([key]) => key !== 'access_grants')
		);
		// New router models need a default route, so start with it open.
		defaultOpen = !model;
		translations = structuredClone(model?.meta?.i18n ?? {});
		if (!model) {
			name = '';
			id = '';
			description = '';
			initRoutes();
			strategy = 'first';
			decisions = { ...DEFAULT_DECISIONS };
			accessGrants = [];
		}
		if (model) {
			name = model.name;
			id = model.id;
			profileImageUrl = model.meta.profile_image_url;
			description = model.meta.description;
			initRoutes(model.meta?.routes ?? []);
			strategy = model.meta?.strategy ?? 'first';
			decisions = { ...DEFAULT_DECISIONS, ...(model.config?.decisions ?? {}) };
			accessGrants =
				/** @type {any} */ (($models ?? []).find((m) => m.id === model.id))?.info?.access_grants ??
				[];
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

<AccessControlModal bind:show={showAccessControlModal} bind:accessGrants accessRoles={['read']} />

<Modal
	ariaLabel={edit
		? $i18n.t('settings.admin.models.routerModels.edit.label')
		: $i18n.t('settings.admin.models.routerModels.add.label')}
	size="sm"
	bind:show
>
	<div>
		<div class=" flex justify-between dark:text-base-100 px-4 pt-3 pb-2">
			<div class="text-sm font-medium self-center">
				{#if edit}
					{$i18n.t('settings.admin.models.routerModels.edit.label')}
				{:else}
					{$i18n.t('settings.admin.models.routerModels.add.label')}
				{/if}
			</div>
			<div class="flex items-center gap-2">
				<LanguageModeSelect
					bind:value={locale}
					translatedLocales={Object.keys(translations)}
					className="w-fit"
				/>
				<AccessButton on:click={() => (showAccessControlModal = true)} />
				<button
					aria-label={$i18n.t('Close')}
					class="self-center"
					on:click={() => {
						show = false;
					}}
				>
					<XMark className={'size-4'} />
				</button>
			</div>
		</div>

		<div class="flex flex-col md:flex-row w-full px-4 pb-4 md:space-x-4 dark:text-base-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div>
						<div class="flex items-center gap-3.5">
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
											const compressedSrc = canvas.toDataURL('image/webp', 0.8);

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
							<!-- LICENSE covers this Open WebUI fallback logo.
							Do not alter, remove, obscure, or replace it except as LICENSE permits:
							https://docs.openwebui.com/license. -->
							<div class="group relative size-12 shrink-0">
								<button
									class="group relative flex size-full items-center overflow-hidden rounded-xl {profileImageUrl !==
									`${WEBUI_BASE_URL}/favicon.png`
										? 'bg-transparent'
										: 'bg-base-50 dark:bg-base-850'} ring-1 ring-base-200/70 transition hover:ring-base-300 dark:ring-base-0/10 dark:hover:ring-base-0/20"
									type="button"
									aria-label={$i18n.t('Upload profile image')}
									on:click={() => {
										imageInputElement.click();
									}}
								>
									<img
										src={profileImageUrl}
										alt={$i18n.t('model profile')}
										class="size-full object-cover"
									/>

									<div
										class="absolute bottom-0 right-0 z-10 opacity-0 transition group-hover:opacity-100 group-focus-within:opacity-100"
									>
										<div class="m-1">
											<div
												class="rounded-full bg-base-900 p-1 text-base-0 shadow-sm transition dark:bg-base-0 dark:text-base-1000"
											>
												<Photo className="size-3" />
											</div>
										</div>
									</div>

									<div
										class="absolute inset-0 bg-base-0 opacity-0 transition group-hover:opacity-20 dark:bg-base-1000"
									></div>
								</button>

								{#if profileImageUrl && profileImageUrl !== `${WEBUI_BASE_URL}/favicon.png`}
									<button
										class="absolute left-1/2 top-full mt-1 -translate-x-1/2 text-[0.5rem] leading-none text-base-400 opacity-0 transition group-hover:opacity-60 hover:text-base-500 hover:opacity-100 group-focus-within:opacity-60 dark:text-base-600 dark:hover:text-base-400"
										on:click={() => {
											profileImageUrl = `${WEBUI_BASE_URL}/favicon.png`;
										}}
										type="button"
									>
										{$i18n.t('Reset')}</button
									>
								{/if}
							</div>

							<div class="min-w-0 w-full flex-1">
								<div class="flex min-w-0 items-start gap-2">
									<LocalizedField
										bind:value={name}
										bind:translations
										{locale}
										field="name"
										placeholder={$i18n.t('Model Name')}
										className="w-full bg-transparent text-sm text-base-900 outline-hidden placeholder:text-base-300 dark:text-base-0 dark:placeholder:text-base-700"
										required
									/>
								</div>
								<input
									class="block w-full bg-transparent py-0.5 text-xs text-base-500 outline-hidden placeholder:text-base-300 dark:text-base-500 dark:placeholder:text-base-700"
									type="text"
									bind:value={id}
									placeholder={$i18n.t('Model ID')}
									aria-label={$i18n.t('Model ID')}
									autocomplete="off"
									required
									disabled={edit}
								/>
							</div>
						</div>

						<div class="flex flex-col w-full mt-4">
							<div class=" mb-1 text-xs text-base-500">{$i18n.t('Description')}</div>

							<div class="flex-1">
								<LocalizedField
									bind:value={description}
									bind:translations
									{locale}
									field="description"
									placeholder={$i18n.t('Enter description')}
								/>
							</div>
						</div>

						<hr class=" border-base-100 dark:border-base-700/10 my-2.5 w-full" />

						<div class="text-xs font-medium text-base-700 dark:text-base-300">
							{$i18n.t('settings.admin.models.routerModels.rules.label')}
						</div>

						<div class="mt-1 flex flex-col">
							<ModelSettingsSection
								label={$i18n.t('Patterns')}
								description={$i18n.t('settings.admin.models.routerModels.patterns.description')}
								summary={countSummary(patternRoutes)}
							>
								<div class="flex flex-col w-full gap-1">
									{#each patternRoutes as route, idx}
										<div class="flex w-full items-center gap-2">
											<div class="w-2/5 shrink-0">
												<select
													class="w-full min-w-0 py-1 text-xs rounded-lg bg-transparent outline-hidden {route.model_id
														? ''
														: 'text-base-500'}"
													bind:value={route.model_id}
													aria-label={$i18n.t('Select a model')}
												>
													<option value="" disabled>{$i18n.t('Select a model')}</option>
													{#each targetModels as targetModel}
														<option value={targetModel.id} class="bg-base-50 dark:bg-base-700"
															>{targetModel.name}</option
														>
													{/each}
												</select>
											</div>
											<input
												class="w-full min-w-0 text-xs bg-transparent placeholder:text-base-300 dark:placeholder:text-base-700 outline-hidden font-mono"
												type="text"
												bind:value={route.pattern}
												placeholder={$i18n.t('Regular expression')}
												aria-label={$i18n.t('Regular expression')}
												autocomplete="off"
											/>
											<div class="flex shrink-0 items-center gap-1">
												<button
													type="button"
													class="shrink-0 text-base-400 transition hover:text-base-700 disabled:opacity-30 dark:hover:text-base-200"
													aria-label={$i18n.t('Move up')}
													disabled={idx === 0}
													on:click={() => (patternRoutes = moveItem(patternRoutes, idx, -1))}
												>
													<ChevronUp className="size-3" strokeWidth="2" />
												</button>
												<button
													type="button"
													class="shrink-0 text-base-400 transition hover:text-base-700 disabled:opacity-30 dark:hover:text-base-200"
													aria-label={$i18n.t('Move down')}
													disabled={idx === patternRoutes.length - 1}
													on:click={() => (patternRoutes = moveItem(patternRoutes, idx, 1))}
												>
													<ChevronDown className="size-3" strokeWidth="2" />
												</button>
												<button
													type="button"
													class="shrink-0 text-base-400 transition hover:text-base-700 disabled:opacity-30 dark:hover:text-base-200"
													aria-label={$i18n.t('Remove')}
													on:click={() =>
														(patternRoutes = patternRoutes.filter((_, i) => i !== idx))}
												>
													<Minus strokeWidth="2" className="size-3.5" />
												</button>
											</div>
										</div>
									{/each}
									<button
										type="button"
										class="flex w-fit items-center gap-1 py-1 text-xs text-base-500 transition hover:text-base-700 dark:hover:text-base-300"
										on:click={() =>
											(patternRoutes = [...patternRoutes, { model_id: '', pattern: '' }])}
									>
										<Plus className="size-3" strokeWidth="2" />
										{$i18n.t('Add pattern')}
									</button>
								</div>
							</ModelSettingsSection>

							<ModelSettingsSection
								label={$i18n.t('Conditions')}
								description={$i18n.t('settings.admin.models.routerModels.conditions.description')}
								summary={countSummary(conditionRoutes)}
							>
								<div class="flex flex-col w-full gap-1">
									{#each conditionRoutes as route, idx}
										<div class="flex w-full items-center gap-2">
											<div class="w-2/5 shrink-0">
												<select
													class="w-full min-w-0 py-1 text-xs rounded-lg bg-transparent outline-hidden {route.model_id
														? ''
														: 'text-base-500'}"
													bind:value={route.model_id}
													aria-label={$i18n.t('Select a model')}
												>
													<option value="" disabled>{$i18n.t('Select a model')}</option>
													{#each targetModels as targetModel}
														<option value={targetModel.id} class="bg-base-50 dark:bg-base-700"
															>{targetModel.name}</option
														>
													{/each}
												</select>
											</div>
											<input
												class="w-full min-w-0 text-xs bg-transparent placeholder:text-base-300 dark:placeholder:text-base-700 outline-hidden"
												type="text"
												bind:value={route.condition}
												placeholder={$i18n.t(
													'e.g. the conversation includes personal or medical details'
												)}
												aria-label={$i18n.t('Condition')}
												autocomplete="off"
											/>
											<div class="flex shrink-0 items-center gap-1">
												<button
													type="button"
													class="shrink-0 text-base-400 transition hover:text-base-700 disabled:opacity-30 dark:hover:text-base-200"
													aria-label={$i18n.t('Remove')}
													on:click={() =>
														(conditionRoutes = conditionRoutes.filter((_, i) => i !== idx))}
												>
													<Minus strokeWidth="2" className="size-3.5" />
												</button>
											</div>
										</div>
									{/each}
									<button
										type="button"
										class="flex w-fit items-center gap-1 py-1 text-xs text-base-500 transition hover:text-base-700 dark:hover:text-base-300"
										on:click={() =>
											(conditionRoutes = [...conditionRoutes, { model_id: '', condition: '' }])}
									>
										<Plus className="size-3" strokeWidth="2" />
										{$i18n.t('Add condition')}
									</button>
								</div>
							</ModelSettingsSection>

							<ModelSettingsSection
								label={$i18n.t('Default')}
								description={$i18n.t('settings.admin.models.routerModels.default.description')}
								summary={defaultSummary}
								bind:open={defaultOpen}
							>
								<div class="flex flex-col w-full gap-1">
									{#if defaultRoutes.length > 1}
										<div class="flex items-center justify-between gap-2 text-xs text-base-500">
											<span>{$i18n.t('Strategy')}</span>
											<select
												class="py-0.5 text-xs bg-transparent outline-hidden"
												bind:value={strategy}
												aria-label={$i18n.t('Strategy')}
											>
												<option value="first" class="bg-base-50 dark:bg-base-700"
													>{$i18n.t('First')}</option
												>
												<option value="random" class="bg-base-50 dark:bg-base-700"
													>{$i18n.t('Random')}</option
												>
											</select>
										</div>
									{/if}
									{#each defaultRoutes as route, idx}
										<div class="flex w-full items-center gap-2">
											<div class="flex-1 min-w-0">
												<select
													class="w-full min-w-0 py-1 text-xs rounded-lg bg-transparent outline-hidden {route.model_id
														? ''
														: 'text-base-500'}"
													bind:value={route.model_id}
													aria-label={$i18n.t('Select a model')}
												>
													<option value="" disabled>{$i18n.t('Select a model')}</option>
													{#each targetModels as targetModel}
														<option value={targetModel.id} class="bg-base-50 dark:bg-base-700"
															>{targetModel.name}</option
														>
													{/each}
												</select>
											</div>
											<div class="flex shrink-0 items-center gap-1">
												<button
													type="button"
													class="shrink-0 text-base-400 transition hover:text-base-700 disabled:opacity-30 dark:hover:text-base-200"
													aria-label={$i18n.t('Move up')}
													disabled={idx === 0}
													on:click={() => (defaultRoutes = moveItem(defaultRoutes, idx, -1))}
												>
													<ChevronUp className="size-3" strokeWidth="2" />
												</button>
												<button
													type="button"
													class="shrink-0 text-base-400 transition hover:text-base-700 disabled:opacity-30 dark:hover:text-base-200"
													aria-label={$i18n.t('Move down')}
													disabled={idx === defaultRoutes.length - 1}
													on:click={() => (defaultRoutes = moveItem(defaultRoutes, idx, 1))}
												>
													<ChevronDown className="size-3" strokeWidth="2" />
												</button>
												<button
													type="button"
													class="shrink-0 text-base-400 transition hover:text-base-700 disabled:opacity-30 dark:hover:text-base-200"
													aria-label={$i18n.t('Remove')}
													on:click={() =>
														(defaultRoutes = defaultRoutes.filter((_, i) => i !== idx))}
												>
													<Minus strokeWidth="2" className="size-3.5" />
												</button>
											</div>
										</div>
									{/each}
									<button
										type="button"
										class="flex w-fit items-center gap-1 py-1 text-xs text-base-500 transition hover:text-base-700 dark:hover:text-base-300"
										on:click={() => (defaultRoutes = [...defaultRoutes, { model_id: '' }])}
									>
										<Plus className="size-3" strokeWidth="2" />
										{$i18n.t('Add model')}
									</button>
									{#if defaultRoutes.length === 0}
										<div class="text-xs text-base-500">
											{$i18n.t('Add a default model, or requests that match nothing will fail.')}
										</div>
									{/if}
								</div>
							</ModelSettingsSection>

							{#if conditionRoutes.length > 0}
								<ModelSettingsSection
									label={$i18n.t('settings.admin.models.routerModels.decisions.label')}
									description={$i18n.t('settings.admin.models.routerModels.decisions.description')}
									summary={decisions.model}
								>
									<div class="flex flex-col w-full gap-1.5">
										<input
											class="w-full min-w-0 text-xs bg-transparent placeholder:text-base-300 dark:placeholder:text-base-700 outline-hidden"
											type="text"
											bind:value={decisions.api_base_url}
											placeholder={$i18n.t('settings.admin.models.routerModels.decisionsUrl.label')}
											aria-label={$i18n.t('settings.admin.models.routerModels.decisionsUrl.label')}
											autocomplete="off"
										/>
										<SensitiveInput
											bind:value={decisions.api_key}
											placeholder={$i18n.t('settings.admin.models.routerModels.decisionsKey.label')}
											inputClassName="text-xs!"
											required={false}
										/>
										<div class="flex gap-2">
											<input
												class="w-full min-w-0 text-xs bg-transparent placeholder:text-base-300 dark:placeholder:text-base-700 outline-hidden"
												type="text"
												bind:value={decisions.model}
												placeholder={$i18n.t(
													'settings.admin.models.routerModels.decisionsModel.label'
												)}
												aria-label={$i18n.t(
													'settings.admin.models.routerModels.decisionsModel.label'
												)}
												autocomplete="off"
											/>
											<input
												class="w-20 shrink-0 text-xs bg-transparent outline-hidden"
												type="number"
												min="0"
												max="1"
												step="0.05"
												bind:value={decisions.threshold}
												aria-label={$i18n.t(
													'settings.admin.models.routerModels.decisionsThreshold.label'
												)}
											/>
										</div>
										<Textarea
											bind:value={decisions.prompt}
											className="w-full bg-transparent text-xs outline-hidden placeholder:text-base-300 dark:placeholder:text-base-700"
											placeholder={$i18n.t(
												'Leave empty to use the default prompt, or enter a custom prompt'
											)}
											ariaLabel={$i18n.t('Prompt')}
											rows={1}
										/>
									</div>
								</ModelSettingsSection>
							{/if}
						</div>

						<div class="mt-3 text-[0.6875rem] text-base-400 dark:text-base-600">
							{$i18n.t('People also need access to the models this router model uses.')}
						</div>
					</div>

					<div class="flex justify-end pt-3 text-sm font-medium gap-1.5">
						{#if edit}
							<button
								class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg px-2.5 text-xs font-normal transition disabled:opacity-60 dark:bg-base-1000 dark:hover:bg-base-950 dark:text-base-0 bg-base-0 text-base-1000 hover:bg-base-100 flex-row"
								type="button"
								on:click={() => {
									showDeleteConfirmDialog = true;
								}}
							>
								{$i18n.t('Delete')}
							</button>
						{/if}

						<button
							class="flex h-7 shrink-0 items-center justify-center gap-1.5 rounded-lg bg-base-900 px-2.5 text-xs font-normal text-base-0 transition hover:bg-base-1000 disabled:opacity-60 dark:bg-base-100 dark:text-base-900 dark:hover:bg-base-0 disabled:cursor-not-allowed"
							type="submit"
							disabled={loading}
						>
							{$i18n.t('Save')}

							{#if loading}
								<div class="shrink-0">
									<Spinner className="size-3" />
								</div>
							{/if}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>
