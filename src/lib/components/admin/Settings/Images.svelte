<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, getContext } from 'svelte';

	import { config as backendConfig, imageModels, user, type ImageModel } from '$lib/stores';
	import { getBackendConfig } from '$lib/apis';
	import { getConfig, getImageConnectionModels, updateConfig } from '$lib/apis/images';
	import type { ImageCapability } from '$lib/utils/images';

	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SettingsSelect from '$lib/components/common/SettingsSelect.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import AdminSettingRow from './AdminSettingRow.svelte';
	import AdminSettingSection from './AdminSettingSection.svelte';
	import AdminSettingSaveButton from './AdminSettingSaveButton.svelte';
	import ImageConnection from './Images/ImageConnection.svelte';
	import ImageConnectionModal from './Images/ImageConnectionModal.svelte';
	import Videos from './Videos.svelte';

	const dispatch = createEventDispatcher();
	const i18n: any = getContext('i18n');

	type ImagesConfig = {
		ENABLE_IMAGE_GENERATION: boolean;
		ENABLE_IMAGE_PROMPT_GENERATION: boolean;
		ENABLE_IMAGE_EDIT: boolean;
		IMAGE_GENERATION_DEFAULT_MODEL: string;
		IMAGE_EDIT_DEFAULT_MODEL: string;
		IMAGE_CONNECTIONS: any[];
	};

	let loading = false;
	let config: ImagesConfig | null = null;
	let savedConfig: ImagesConfig | null = null;
	let showAddConnectionModal = false;

	// The Videos section keeps its own config; this page's Save button saves both.
	let videos: Videos;
	let videoConfig: any = null;
	let videoSavedConfig: any = null;

	$: settingLabels = {
		ENABLE_VIDEO_GENERATION: $i18n.t('settings.admin.videos.videoGeneration.label'),
		VIDEO_GENERATION_DEFAULT_MODEL: $i18n.t('settings.admin.videos.defaultVideoModel.label'),
		ENABLE_IMAGE_GENERATION: $i18n.t('settings.admin.images.imageGeneration.label'),
		ENABLE_IMAGE_EDIT: $i18n.t('settings.admin.images.imageEdit.label'),
		IMAGE_GENERATION_DEFAULT_MODEL: $i18n.t('settings.admin.images.defaultGenerationModel.label'),
		IMAGE_EDIT_DEFAULT_MODEL: $i18n.t('settings.admin.images.defaultEditModel.label'),
		ENABLE_IMAGE_PROMPT_GENERATION: $i18n.t('settings.admin.images.imagePromptGeneration.label')
	};

	let connectionModels: ImageModel[] = [];

	// Every model the connections offer, synced ones included, as the backend lists them.
	const loadConnectionModels = async () => {
		connectionModels = (await getImageConnectionModels(localStorage.token).catch(() => [])) ?? [];
	};

	const getModelOptions = (models: ImageModel[], capability: ImageCapability) =>
		models
			.filter((model) => model[capability])
			.map((model) => ({
				value: model.id,
				label: model.model ? `${model.connection_name} / ${model.name}` : model.connection_name
			}));

	$: generationModelOptions = getModelOptions(connectionModels, 'image_generation');
	$: editModelOptions = getModelOptions(connectionModels, 'image_edit');

	const save = async (next: ImagesConfig) => {
		const res = await updateConfig(localStorage.token, next).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			savedConfig = structuredClone(res);
			imageModels.set(null);
			loadConnectionModels();
			backendConfig.set(await getBackendConfig());
		}
		return res;
	};

	// Connection changes save right away, like other connection lists, without the unsaved toggles above.
	const saveConnections = async (connections: any[]) => {
		if (!config || !savedConfig) return;

		const res = await save({ ...savedConfig, IMAGE_CONNECTIONS: connections });
		if (res) {
			config = { ...config, IMAGE_CONNECTIONS: res.IMAGE_CONNECTIONS };
			toast.success($i18n.t('Connections saved successfully'));
		}
	};

	const saveHandler = async () => {
		if (!config) return;

		loading = true;
		const [res, videoRes] = await Promise.all([save(config), videos?.saveHandler() ?? null]);
		loading = false;

		if (res) {
			config = structuredClone(res);
		}
		if (res && (videoRes || !videoConfig)) {
			dispatch('save');
		}
	};

	onMount(async () => {
		if ($user?.role !== 'admin') return;

		const res = await getConfig(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			config = res;
			savedConfig = structuredClone(res);
			loadConnectionModels();
		}
	});
</script>

<ImageConnectionModal
	bind:show={showAddConnectionModal}
	onSubmit={async (connection) => {
		await saveConnections([...(config?.IMAGE_CONNECTIONS ?? []), connection]);
	}}
/>

<form class="flex h-full flex-col justify-between text-sm" on:submit|preventDefault={saveHandler}>
	<h2 class="text-sm font-medium text-base-900 dark:text-white mb-4">
		{$i18n.t('Images & Videos')}
	</h2>

	<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5">
		{#if config}
			<div class="flex flex-col">
				<AdminSettingSection first>
					<AdminSettingRow
						label={$i18n.t('settings.admin.images.imageGeneration.label')}
						description={$i18n.t('settings.admin.images.imageGeneration.description')}
						let:labelId
					>
						<Switch bind:state={config.ENABLE_IMAGE_GENERATION} ariaLabelledbyId={labelId} />
					</AdminSettingRow>

					<AdminSettingRow
						label={$i18n.t('settings.admin.images.imageEdit.label')}
						description={$i18n.t('settings.admin.images.imageEdit.description')}
						let:labelId
					>
						<Switch bind:state={config.ENABLE_IMAGE_EDIT} ariaLabelledbyId={labelId} />
					</AdminSettingRow>

					{#if config.ENABLE_IMAGE_GENERATION || config.ENABLE_IMAGE_EDIT}
						<div>
							<div class="mb-2 flex items-center justify-between gap-4">
								<div class="text-xs text-base-600 dark:text-base-400">
									{$i18n.t('settings.admin.images.manageImageConnections.label')}
								</div>

								<Tooltip content={$i18n.t('settings.admin.images.addConnection.label')}>
									<button
										aria-label={$i18n.t('settings.admin.images.addConnection.label')}
										class="flex size-6 items-center justify-center rounded-lg text-base-400 transition-colors hover:bg-black/5 hover:text-base-700 dark:text-base-600 dark:hover:bg-white/5 dark:hover:text-base-300"
										on:click={() => {
											showAddConnectionModal = true;
										}}
										type="button"
									>
										<Plus />
									</button>
								</Tooltip>
							</div>

							<div class="flex flex-col gap-1.5">
								{#each config.IMAGE_CONNECTIONS as connection, idx (connection.id)}
									<ImageConnection
										{connection}
										onSubmit={(updated) => {
											saveConnections(
												(config?.IMAGE_CONNECTIONS ?? []).map((c, i) => (i === idx ? updated : c))
											);
										}}
										onDelete={() => {
											saveConnections(
												(config?.IMAGE_CONNECTIONS ?? []).filter((_, i) => i !== idx)
											);
										}}
									/>
								{/each}
							</div>
						</div>
					{/if}
				</AdminSettingSection>

				{#if config.ENABLE_IMAGE_GENERATION || config.ENABLE_IMAGE_EDIT}
					<AdminSettingSection
						title={$i18n.t('settings.admin.images.sections.defaultModels.title')}
					>
						{#if config.ENABLE_IMAGE_GENERATION}
							<AdminSettingRow
								label={$i18n.t('settings.admin.images.defaultGenerationModel.label')}
								description={$i18n.t('settings.admin.images.defaultGenerationModel.description')}
								let:labelId
							>
								<SettingsSelect
									id={`${labelId}-control`}
									bind:value={config.IMAGE_GENERATION_DEFAULT_MODEL}
								>
									<option value="">{$i18n.t('First available')}</option>
									{#each generationModelOptions as option (option.value)}
										<option value={option.value}>{option.label}</option>
									{/each}
								</SettingsSelect>
							</AdminSettingRow>
						{/if}

						{#if config.ENABLE_IMAGE_EDIT}
							<AdminSettingRow
								label={$i18n.t('settings.admin.images.defaultEditModel.label')}
								description={$i18n.t('settings.admin.images.defaultEditModel.description')}
								let:labelId
							>
								<SettingsSelect
									id={`${labelId}-control`}
									bind:value={config.IMAGE_EDIT_DEFAULT_MODEL}
								>
									<option value="">{$i18n.t('First available')}</option>
									{#each editModelOptions as option (option.value)}
										<option value={option.value}>{option.label}</option>
									{/each}
								</SettingsSelect>
							</AdminSettingRow>
						{/if}
					</AdminSettingSection>
				{/if}

				{#if config.ENABLE_IMAGE_GENERATION}
					<AdminSettingSection title={$i18n.t('settings.admin.images.sections.legacy.title')}>
						<AdminSettingRow
							label={$i18n.t('settings.admin.images.imagePromptGeneration.label')}
							description={$i18n.t('settings.admin.images.imagePromptGeneration.legacyDescription')}
							let:labelId
						>
							<Switch
								bind:state={config.ENABLE_IMAGE_PROMPT_GENERATION}
								ariaLabelledbyId={labelId}
							/>
						</AdminSettingRow>
					</AdminSettingSection>
				{/if}

				<Videos bind:this={videos} bind:config={videoConfig} bind:savedConfig={videoSavedConfig} />
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-6 text-sm font-normal">
		<AdminSettingSaveButton
			settings={config && { ...config, ...videoConfig }}
			savedConfig={savedConfig && { ...savedConfig, ...videoSavedConfig }}
			labels={settingLabels}
			disabled={loading}
			{loading}
		/>
	</div>
</form>
