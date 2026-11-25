<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';

	import { config as backendConfig, videoModels, user, type VideoModel } from '$lib/stores';
	import { getBackendConfig } from '$lib/apis';
	import { getConfig, getVideoConnectionModels, updateConfig } from '$lib/apis/videos';

	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SettingsSelect from '$lib/components/common/SettingsSelect.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import AdminSettingRow from './AdminSettingRow.svelte';
	import AdminSettingSection from './AdminSettingSection.svelte';
	import VideoConnection from './Videos/VideoConnection.svelte';
	import VideoConnectionModal from './Videos/VideoConnectionModal.svelte';

	// The Videos section of the Images & Videos settings. The page's Save button saves it through
	// `saveHandler`, so the page binds `config` and `savedConfig` to show what changed.
	const i18n: any = getContext('i18n');

	type VideosConfig = {
		ENABLE_VIDEO_GENERATION: boolean;
		VIDEO_GENERATION_DEFAULT_MODEL: string;
		VIDEO_CONNECTIONS: any[];
	};

	export let config: VideosConfig | null = null;
	export let savedConfig: VideosConfig | null = null;
	let showAddConnectionModal = false;

	let connectionModels: VideoModel[] = [];

	// Every model the connections offer, synced ones included, as the backend lists them.
	const loadConnectionModels = async () => {
		connectionModels = (await getVideoConnectionModels(localStorage.token).catch(() => [])) ?? [];
	};

	$: modelOptions = connectionModels.map((model) => ({
		value: model.id,
		label: model.model ? `${model.connection_name} / ${model.name}` : model.connection_name
	}));

	const save = async (next: VideosConfig) => {
		const res = await updateConfig(localStorage.token, next).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			savedConfig = structuredClone(res);
			videoModels.set(null);
			loadConnectionModels();
			backendConfig.set(await getBackendConfig());
		}
		return res;
	};

	// Connection changes save right away, like other connection lists, without the unsaved toggles above.
	const saveConnections = async (connections: any[]) => {
		if (!config || !savedConfig) return;

		const res = await save({ ...savedConfig, VIDEO_CONNECTIONS: connections });
		if (res) {
			config = { ...config, VIDEO_CONNECTIONS: res.VIDEO_CONNECTIONS };
			toast.success($i18n.t('Connections saved successfully'));
		}
	};

	/** Save the video settings; resolves to the saved config, or null when saving failed. */
	export const saveHandler = async (): Promise<VideosConfig | null> => {
		if (!config) return null;

		const res = await save(config);
		if (res) {
			config = structuredClone(res);
		}
		return res;
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

<VideoConnectionModal
	bind:show={showAddConnectionModal}
	onSubmit={async (connection) => {
		await saveConnections([...(config?.VIDEO_CONNECTIONS ?? []), connection]);
	}}
/>

{#if config}
	<div class="flex flex-col">
		<!-- Settings search reads these keys from the locale file, which i18n:parse cannot see: $i18n.t('settings.admin.videos.sections.defaultModels.title') -->
		<AdminSettingSection title={$i18n.t('settings.admin.videos.title')}>
			<AdminSettingRow
				label={$i18n.t('settings.admin.videos.videoGeneration.label')}
				description={$i18n.t('settings.admin.videos.videoGeneration.description')}
				let:labelId
			>
				<Switch bind:state={config.ENABLE_VIDEO_GENERATION} ariaLabelledbyId={labelId} />
			</AdminSettingRow>

			{#if config.ENABLE_VIDEO_GENERATION}
				<div>
					<div class="mb-2 flex items-center justify-between gap-4">
						<div class="text-xs text-base-600 dark:text-base-400">
							{$i18n.t('settings.admin.videos.manageVideoConnections.label')}
						</div>

						<Tooltip content={$i18n.t('settings.admin.videos.addConnection.label')}>
							<button
								aria-label={$i18n.t('settings.admin.videos.addConnection.label')}
								class="flex size-6 items-center justify-center rounded-lg text-base-400 transition-colors hover:bg-base-1000/5 hover:text-base-700 dark:text-base-600 dark:hover:bg-base-0/5 dark:hover:text-base-300"
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
						{#each config.VIDEO_CONNECTIONS as connection, idx (connection.id)}
							<VideoConnection
								{connection}
								onSubmit={(updated) => {
									saveConnections(
										(config?.VIDEO_CONNECTIONS ?? []).map((c, i) => (i === idx ? updated : c))
									);
								}}
								onDelete={() => {
									saveConnections((config?.VIDEO_CONNECTIONS ?? []).filter((_, i) => i !== idx));
								}}
							/>
						{/each}
					</div>
				</div>
			{/if}

			{#if config.ENABLE_VIDEO_GENERATION}
				<AdminSettingRow
					label={$i18n.t('settings.admin.videos.defaultVideoModel.label')}
					description={$i18n.t('settings.admin.videos.defaultVideoModel.description')}
					let:labelId
				>
					<SettingsSelect
						id={`${labelId}-control`}
						bind:value={config.VIDEO_GENERATION_DEFAULT_MODEL}
					>
						<option value="">{$i18n.t('First available')}</option>
						{#each modelOptions as option (option.value)}
							<option value={option.value}>{option.label}</option>
						{/each}
					</SettingsSelect>
				</AdminSettingRow>
			{/if}
		</AdminSettingSection>
	</div>
{/if}
