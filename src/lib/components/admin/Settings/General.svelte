<script lang="ts">
	import DOMPurify from 'dompurify';
	import { v4 as uuidv4 } from 'uuid';

	import { getBackendConfig, getVersionUpdates } from '$lib/apis';
	import { getAdminConfig, updateAdminConfig } from '$lib/apis/auths';
	import { getBanners, setBanners } from '$lib/apis/configs';
	import InterfaceSettings from '$lib/components/common/InterfaceSettings.svelte';
	import SettingsSelect from '$lib/components/common/SettingsSelect.svelte';
	import LanguageModeSelect from '$lib/components/common/LanguageModeSelect.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { WEBUI_BUILD_HASH, WEBUI_VERSION } from '$lib/constants';
	import { banners as _banners, config, showChangelog } from '$lib/stores';
	import type { Banner } from '$lib/types';
	import { compareVersion } from '$lib/utils';
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import Banners from './Interface/Banners.svelte';
	import Events from './Events.svelte';
	import AdminSettingField from './AdminSettingField.svelte';
	import AdminSettingRow from './AdminSettingRow.svelte';
	import AdminSettingSection from './AdminSettingSection.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import I18nSettings from './I18nSettings.svelte';
	import { updateI18n } from '$lib/i18n';
	import { entriesToI18n, i18nToEntries, type I18nEntry } from '$lib/utils/translationDictionary';

	const i18n: any = getContext('i18n');

	export let saveHandler: Function;

	let updateAvailable: boolean | null = null;
	let version = {
		current: WEBUI_VERSION,
		latest: ''
	};

	let adminConfig: any = null;
	let defaultInterfaceSettings: Record<string, any> = {};
	let showUserUiDefaults = false;
	let uiI18nEntries: I18nEntry[] = [];
	let saving = false;

	let banners: Banner[] = [];
	let bannerLocale = '';
	const inputClass =
		'w-full h-7 rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';
	const textareaClass =
		'w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';
	const checkForVersionUpdates = async () => {
		updateAvailable = null;
		version = await getVersionUpdates(localStorage.token).catch((error) => {
			return {
				current: WEBUI_VERSION,
				latest: null
			};
		});

		console.info(version);

		updateAvailable = compareVersion(version.latest, version.current);
		console.info(updateAvailable);
	};

	const updateBanners = async () => {
		_banners.set(await setBanners(localStorage.token, banners));
	};

	const saveDefaultInterfaceSettings = (updated: Record<string, any>) => {
		defaultInterfaceSettings = { ...defaultInterfaceSettings, ...updated };
	};

	const getDefaultInterfaceSettings = () => {
		const value = adminConfig?.DEFAULT_INTERFACE_SETTINGS;
		return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
	};

	const updateHandler = async () => {
		if (saving) return;
		saving = true;
		try {
			const cleaned = entriesToI18n(uiI18nEntries);
			const res = await updateAdminConfig(localStorage.token, {
				...adminConfig,
				DEFAULT_INTERFACE_SETTINGS: defaultInterfaceSettings,
				I18N: cleaned
			});
			if (!res) throw new Error($i18n.t('Failed to update settings'));
			await updateI18n(res.I18N ?? cleaned);
			await updateBanners();
			await config.set(await getBackendConfig());
			saveHandler();
		} catch (error) {
			toast.error(
				error instanceof Error
					? error.message
					: Array.isArray(error)
						? error.map((entry) => entry.msg).join('\n')
						: String(error)
			);
		} finally {
			saving = false;
		}
	};

	onMount(async () => {
		adminConfig = await getAdminConfig(localStorage.token);
		defaultInterfaceSettings = getDefaultInterfaceSettings();
		uiI18nEntries = i18nToEntries(adminConfig.I18N ?? {});

		banners = [...$_banners];

		if ($config?.features?.enable_version_update_check) {
			checkForVersionUpdates();
		}
	});
</script>

<form
	class="flex h-full flex-col justify-between text-sm"
	on:submit|preventDefault={async () => {
		updateHandler();
	}}
>
	<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-4">
		{$i18n.t('settings.admin.general.title')}
	</h2>

	<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5">
		{#if adminConfig !== null}
			<AdminSettingSection first>
				<div class="flex items-start justify-between gap-4">
					<div class="min-w-0 text-xs">
						<div class="text-gray-600 dark:text-gray-400">
							{$i18n.t('settings.admin.general.version.label')}
						</div>
						<div class="mt-1 flex flex-wrap gap-x-1 text-gray-700 dark:text-gray-200">
							<Tooltip content={WEBUI_BUILD_HASH}>v{WEBUI_VERSION}</Tooltip>

							{#if $config?.features?.enable_version_update_check}
								{#if version.latest === null}
									<span class="text-gray-500 dark:text-gray-500"
										>{$i18n.t('Could not check for updates')}</span
									>
								{:else}
									<a
										href="https://github.com/open-webui/open-webui/releases/tag/v{version.latest}"
										target="_blank"
										class="text-gray-500 hover:text-gray-700 dark:text-gray-500 dark:hover:text-gray-300"
									>
										{updateAvailable === null
											? $i18n.t('Checking for updates...')
											: updateAvailable
												? `(v${version.latest} ${$i18n.t('available!')})`
												: $i18n.t('(latest)')}
									</a>
								{/if}
							{/if}
						</div>

						<button
							class="mt-0.5 text-xs text-gray-400 transition-colors hover:text-gray-700 dark:text-gray-600 dark:hover:text-gray-300"
							type="button"
							on:click={() => {
								showChangelog.set(true);
							}}
						>
							{$i18n.t('settings.admin.general.seeWhatSNew.label')}
						</button>
					</div>

					{#if $config?.features?.enable_version_update_check}
						<button
							class="shrink-0 text-xs text-gray-500 transition-colors hover:text-gray-900 dark:text-gray-500 dark:hover:text-white"
							type="button"
							on:click={() => {
								checkForVersionUpdates();
							}}
						>
							{$i18n.t('settings.admin.general.checkForUpdates.label')}
						</button>
					{/if}
				</div>

				<div class="text-xs">
					<div class="flex items-start justify-between gap-4">
						<div class="min-w-0">
							<div class="text-gray-600 dark:text-gray-400">
								{$i18n.t('settings.admin.general.help.label')}
							</div>
							<div class="mt-0.5 text-gray-400 dark:text-gray-600">
								<!-- LICENSE covers this Open WebUI wordmark.
								Do not alter, remove, obscure, or replace it except as LICENSE permits:
								https://docs.openwebui.com/license. -->
								{$i18n.t('settings.admin.general.help.description')}
							</div>
						</div>

						<a
							class="shrink-0 text-gray-500 transition-colors hover:text-gray-900 dark:text-gray-500 dark:hover:text-white"
							href="https://docs.openwebui.com/"
							target="_blank"
						>
							{$i18n.t('Documentation')}
						</a>
					</div>

					<div class="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-gray-400 dark:text-gray-600">
						<a
							class="hover:text-gray-700 dark:hover:text-gray-300"
							href="https://discord.gg/5rJgQTnV4s"
							target="_blank">Discord</a
						>
						<a
							class="hover:text-gray-700 dark:hover:text-gray-300"
							href="https://twitter.com/OpenWebUI"
							target="_blank">X</a
						>
						<a
							class="hover:text-gray-700 dark:hover:text-gray-300"
							href="https://github.com/open-webui/open-webui"
							target="_blank">GitHub</a
						>
					</div>
				</div>

				<div class="text-xs">
					<!-- LICENSE covers this Open WebUI license attribution.
					Do not alter, remove, obscure, or replace it except as LICENSE permits:
					https://docs.openwebui.com/license. -->
					<div class="text-gray-600 dark:text-gray-400">
						{$i18n.t('settings.admin.general.license.label')}
					</div>

					{#if $config?.license_metadata}
						<a
							href="https://docs.openwebui.com/enterprise"
							target="_blank"
							class="mt-0.5 block text-gray-500"
						>
							<span class="capitalize text-black dark:text-white"
								>{$config?.license_metadata?.type} license</span
							>
							{$i18n.t('registered to')}
							<span class="capitalize text-black dark:text-white"
								>{$config?.license_metadata?.organization_name}</span
							>
							for
							<span class="text-black dark:text-white"
								>{$config?.license_metadata?.seats ?? 'Unlimited'} users.</span
							>
						</a>
						{#if $config?.license_metadata?.html}
							<div class="mt-0.5 text-gray-500">
								{@html DOMPurify.sanitize($config?.license_metadata?.html)}
							</div>
						{/if}
					{:else}
						<a
							class="mt-0.5 block text-gray-400 transition-colors hover:text-gray-700 dark:text-gray-600 dark:hover:text-gray-300"
							href="https://docs.openwebui.com/enterprise"
							target="_blank"
						>
							{$i18n.t(
								'Upgrade to a licensed plan for enhanced capabilities, including custom theming and branding, and dedicated support.'
							)}
						</a>
					{/if}
				</div>
			</AdminSettingSection>

			<AdminSettingSection title={$i18n.t('settings.admin.general.sections.features.title')}>
				<AdminSettingRow
					label={$i18n.t('settings.admin.general.communitySharing.label')}
					description={$i18n.t('settings.admin.general.communitySharing.description')}
					let:labelId
				>
					<!-- LICENSE covers this Open WebUI Community wordmark.
					Do not alter, remove, obscure, or replace it except as LICENSE permits:
					https://docs.openwebui.com/license. -->
					<Switch bind:state={adminConfig.ENABLE_COMMUNITY_SHARING} ariaLabelledbyId={labelId} />
				</AdminSettingRow>
				<AdminSettingRow
					label={$i18n.t('settings.admin.general.messageRating.label')}
					description={$i18n.t('settings.admin.general.messageRating.description')}
					let:labelId
				>
					<Switch bind:state={adminConfig.ENABLE_MESSAGE_RATING} ariaLabelledbyId={labelId} />
				</AdminSettingRow>
				<AdminSettingRow
					label={$i18n.t('settings.admin.general.folders.label')}
					description={$i18n.t('settings.admin.general.folders.description')}
					let:labelId
				>
					<Switch bind:state={adminConfig.ENABLE_FOLDERS} ariaLabelledbyId={labelId} />
				</AdminSettingRow>

				{#if adminConfig.ENABLE_FOLDERS}
					<AdminSettingField
						label={$i18n.t('settings.admin.general.folderMaxFileCount.label')}
						description={$i18n.t('settings.admin.general.folderMaxFileCount.description')}
					>
						<input
							class={inputClass}
							type="number"
							min="0"
							placeholder={$i18n.t('Leave empty for unlimited')}
							bind:value={adminConfig.FOLDER_MAX_FILE_COUNT}
						/>
					</AdminSettingField>
				{/if}

				<AdminSettingRow
					label={$i18n.t('settings.admin.general.memories.label')}
					description={$i18n.t('settings.admin.general.memories.description')}
					let:labelId
				>
					<Switch bind:state={adminConfig.ENABLE_MEMORIES} ariaLabelledbyId={labelId} />
				</AdminSettingRow>
				{#if adminConfig.ENABLE_MEMORIES}
					<AdminSettingRow
						label={$i18n.t('settings.admin.general.memorySystemContext.label')}
						description={$i18n.t('settings.admin.general.memorySystemContext.description')}
						labelClassName="text-gray-500 dark:text-gray-500"
						let:labelId
					>
						<Switch
							bind:state={adminConfig.ENABLE_MEMORY_SYSTEM_CONTEXT}
							ariaLabelledbyId={labelId}
						/>
					</AdminSettingRow>
				{/if}
				<AdminSettingRow
					label={$i18n.t('settings.admin.general.notes.label')}
					description={$i18n.t('settings.admin.general.notes.description')}
					let:labelId
				>
					<Switch bind:state={adminConfig.ENABLE_NOTES} ariaLabelledbyId={labelId} />
				</AdminSettingRow>
				<AdminSettingRow
					label={$i18n.t('settings.admin.general.channels.label')}
					description={$i18n.t('settings.admin.general.channels.description')}
					let:labelId
				>
					<Switch bind:state={adminConfig.ENABLE_CHANNELS} ariaLabelledbyId={labelId} />
				</AdminSettingRow>
				{#if adminConfig.ENABLE_CHANNELS}
					<AdminSettingRow
						label={$i18n.t('settings.admin.general.modelResponseMode.label')}
						description={$i18n.t('settings.admin.general.modelResponseMode.description')}
						labelClassName="text-gray-500 dark:text-gray-500"
						let:labelId
					>
						<SettingsSelect
							bind:value={adminConfig.CHANNEL_MODEL_RESPONSE_MODE}
							aria-labelledby={labelId}
						>
							<option value="thread">{$i18n.t('Thread')}</option>
							<option value="channel">{$i18n.t('Channel')}</option>
						</SettingsSelect>
					</AdminSettingRow>
				{/if}
				<AdminSettingRow
					label={$i18n.t('settings.admin.general.calendar.label')}
					description={$i18n.t('settings.admin.general.calendar.description')}
					let:labelId
				>
					<Switch bind:state={adminConfig.ENABLE_CALENDAR} ariaLabelledbyId={labelId} />
				</AdminSettingRow>
				<AdminSettingRow
					label={$i18n.t('settings.admin.general.automations.label')}
					description={$i18n.t('settings.admin.general.automations.description')}
					let:labelId
				>
					<Switch bind:state={adminConfig.ENABLE_AUTOMATIONS} ariaLabelledbyId={labelId} />
				</AdminSettingRow>
				<AdminSettingRow
					label={$i18n.t('settings.admin.general.userWebhooks.label')}
					description={$i18n.t('settings.admin.general.userWebhooks.description')}
					let:labelId
				>
					<Switch bind:state={adminConfig.ENABLE_USER_WEBHOOKS} ariaLabelledbyId={labelId} />
				</AdminSettingRow>
				<AdminSettingRow
					label={$i18n.t('settings.admin.general.userStatus.label')}
					description={$i18n.t('settings.admin.general.userStatus.description')}
					let:labelId
				>
					<Switch bind:state={adminConfig.ENABLE_USER_STATUS} ariaLabelledbyId={labelId} />
				</AdminSettingRow>

				<AdminSettingField
					label={$i18n.t('settings.admin.general.responseWatermark.label')}
					description={$i18n.t('settings.admin.general.responseWatermark.description')}
				>
					<Textarea
						className={textareaClass}
						placeholder={$i18n.t('Enter a watermark for the response. Leave empty for none.')}
						bind:value={adminConfig.RESPONSE_WATERMARK}
					/>
				</AdminSettingField>

				<AdminSettingField
					label={$i18n.t('settings.admin.general.webuiUrl.label')}
					description={$i18n.t('settings.admin.general.webuiUrl.description')}
				>
					<input
						class={inputClass}
						type="text"
						placeholder={`e.g.) "http://localhost:3000"`}
						bind:value={adminConfig.WEBUI_URL}
					/>
				</AdminSettingField>
			</AdminSettingSection>

			<Events />

			<AdminSettingSection title={$i18n.t('settings.admin.general.sections.ui.title')}>
				<fieldset id="ui-i18n-settings" disabled={saving} class="min-w-0">
					<I18nSettings bind:entries={uiI18nEntries} />
				</fieldset>
				<div class="shrink-0">
					<div class="flex items-center justify-between gap-4 py-0.5">
						<button
							class="min-w-0 flex-1 text-left text-xs text-gray-600 transition hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
							type="button"
							on:click={() => {
								showUserUiDefaults = !showUserUiDefaults;
							}}
						>
							<div>{$i18n.t('Default Interface Settings')}</div>
							<div class="mt-1.5 text-[0.6875rem] text-gray-400 dark:text-gray-600">
								{$i18n.t(
									'Set system-wide interface defaults for every account. Personal settings override these defaults.'
								)}
							</div>
						</button>

						<button
							class="shrink-0 text-[0.6875rem] text-gray-400 transition hover:text-gray-700 dark:text-gray-600 dark:hover:text-gray-300"
							type="button"
							on:click={() => {
								showUserUiDefaults = !showUserUiDefaults;
							}}
						>
							{showUserUiDefaults ? $i18n.t('Close') : $i18n.t('Configure')}
						</button>
					</div>

					{#if showUserUiDefaults}
						<div class="mt-0.5 space-y-2">
							<div class="flex items-center justify-between gap-4 py-0.5">
								<div class="text-[0.6875rem] text-gray-400 dark:text-gray-600">
									{Object.keys(defaultInterfaceSettings).length}
									{$i18n.t('settings configured')}
								</div>

								{#if Object.keys(defaultInterfaceSettings).length > 0}
									<button
										class="shrink-0 text-[0.6875rem] text-gray-400 transition hover:text-gray-700 dark:text-gray-600 dark:hover:text-gray-300"
										type="button"
										on:click={() => {
											defaultInterfaceSettings = {};
										}}
									>
										{$i18n.t('Clear')}
									</button>
								{/if}
							</div>

							<div class="max-h-[28rem] overflow-y-auto pb-2 pr-1 scrollbar-hover">
								<InterfaceSettings
									settingsValue={defaultInterfaceSettings}
									saveSettings={saveDefaultInterfaceSettings}
								/>
							</div>
						</div>
					{/if}
				</div>

				<div>
					<div class="mb-1 flex min-h-7 w-full items-center justify-between gap-2">
						<div class="min-w-0 text-xs text-gray-600 dark:text-gray-400">
							{$i18n.t('settings.admin.general.banners.label')}
						</div>
						<div class="flex shrink-0 items-center gap-1">
							{#if banners.length > 0}
								<LanguageModeSelect bind:value={bannerLocale} className="w-fit" />
							{/if}
							<button
								class="flex size-6 items-center justify-center text-gray-400 dark:text-gray-600"
								type="button"
								aria-label={$i18n.t('settings.admin.general.addBanner.label')}
								on:click={() => {
									if (banners.length === 0 || banners[banners.length - 1]?.content !== '') {
										banners = [
											...banners,
											{
												id: uuidv4(),
												type: '',
												title: '',
												content: '',
												dismissible: true,
												timestamp: Math.floor(Date.now() / 1000)
											}
										];
									}
								}}
							>
								<Plus />
							</button>
						</div>
					</div>
					<div class="mb-2 text-[0.6875rem] text-gray-400 dark:text-gray-600">
						{$i18n.t('Create announcements shown to users in the app.')}
					</div>
					<Banners bind:banners locale={bannerLocale} />
				</div>
			</AdminSettingSection>
		{/if}
	</div>

	<div class="flex justify-end pt-6 text-sm font-normal">
		<button
			class="px-3.5 py-1.5 text-sm font-normal bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
			disabled={saving}
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
