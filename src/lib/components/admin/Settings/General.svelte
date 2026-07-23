<script lang="ts">
	import DOMPurify from 'dompurify';
	import { v4 as uuidv4 } from 'uuid';

	import { getBackendConfig, getVersionUpdates } from '$lib/apis';
	import { getAdminConfig, updateAdminConfig } from '$lib/apis/auths';
	import { getBanners, setBanners } from '$lib/apis/configs';
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

	const i18n: any = getContext('i18n');

	export let saveHandler: Function;

	let updateAvailable: boolean | null = false;
	let version = {
		current: WEBUI_VERSION,
		latest: WEBUI_VERSION
	};

	let adminConfig: any = null;

	let banners: Banner[] = [];
	const inputClass =
		'w-full h-7 rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';
	const textareaClass =
		'w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';

	const checkForVersionUpdates = async () => {
		updateAvailable = null;
		version = await getVersionUpdates(localStorage.token).catch((error) => {
			return {
				current: WEBUI_VERSION,
				latest: WEBUI_VERSION
			};
		});

		console.info(version);

		updateAvailable = compareVersion(version.latest, version.current);
		console.info(updateAvailable);
	};

	const updateBanners = async () => {
		_banners.set(await setBanners(localStorage.token, banners));
	};

	const updateHandler = async () => {
		const res = await updateAdminConfig(localStorage.token, adminConfig);

		await updateBanners();

		await config.set(await getBackendConfig());

		if (res) {
			saveHandler();
		} else {
			toast.error($i18n.t('Failed to update settings'));
		}
	};

	onMount(async () => {
		adminConfig = await getAdminConfig(localStorage.token);

		banners = [...$_banners];
	});
</script>

<form
	class="flex h-full flex-col justify-between text-sm"
	on:submit|preventDefault={async () => {
		updateHandler();
	}}
>
	<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-4">{$i18n.t('General')}</h2>

	<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5">
		{#if adminConfig !== null}
			<AdminSettingSection first>
				<div class="flex items-start justify-between gap-4">
					<div class="min-w-0 text-xs">
						<div class="text-gray-600 dark:text-gray-400">{$i18n.t('Version')}</div>
						<div class="mt-1 flex flex-wrap gap-x-1 text-gray-700 dark:text-gray-200">
							<Tooltip content={WEBUI_BUILD_HASH}>v{WEBUI_VERSION}</Tooltip>

							{#if $config?.features?.enable_version_update_check}
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
						</div>

						<button
							class="mt-0.5 text-xs text-gray-400 transition-colors hover:text-gray-700 dark:text-gray-600 dark:hover:text-gray-300"
							type="button"
							on:click={() => {
								showChangelog.set(true);
							}}
						>
							{$i18n.t("See what's new")}
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
							{$i18n.t('Check for updates')}
						</button>
					{/if}
				</div>

				<div class="text-xs">
					<div class="flex items-start justify-between gap-4">
						<div class="min-w-0">
							<div class="text-gray-600 dark:text-gray-400">{$i18n.t('Help')}</div>
							<div class="mt-0.5 text-gray-400 dark:text-gray-600">
								{$i18n.t('Discover how to use Open WebUI and seek support from the community.')}
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
					<div class="text-gray-600 dark:text-gray-400">{$i18n.t('License')}</div>

					{#if $config?.license_metadata}
						<a
							href="https://docs.openwebui.com/enterprise"
							target="_blank"
							class="mt-0.5 block text-gray-500"
						>
							<span class="capitalize text-black dark:text-white"
								>{$config?.license_metadata?.type} license</span
							>
							registered to
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

			<AdminSettingSection title={$i18n.t('Features')}>
				<AdminSettingRow
					label={$i18n.t('Community Sharing')}
					description={$i18n.t('Allow users to share chats with the Open WebUI community.')}
				>
					<Switch bind:state={adminConfig.ENABLE_COMMUNITY_SHARING} />
				</AdminSettingRow>
				<AdminSettingRow
					label={$i18n.t('Message Rating')}
					description={$i18n.t('Let users rate assistant responses.')}
				>
					<Switch bind:state={adminConfig.ENABLE_MESSAGE_RATING} />
				</AdminSettingRow>
				<AdminSettingRow
					label={$i18n.t('Projects')}
					description={$i18n.t('Allow users to organize chats into projects.')}
				>
					<Switch bind:state={adminConfig.ENABLE_FOLDERS} />
				</AdminSettingRow>

				{#if adminConfig.ENABLE_FOLDERS}
					<AdminSettingField
						label={$i18n.t('Project Max File Count')}
						description={$i18n.t('Maximum number of files allowed per project.')}
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
					label={$i18n.t('Memories')}
					description={$i18n.t('Allow users to save memories for more personalized responses.')}
				>
					<Switch bind:state={adminConfig.ENABLE_MEMORIES} />
				</AdminSettingRow>
				{#if adminConfig.ENABLE_MEMORIES}
					<AdminSettingRow
						label={$i18n.t('Memory System Context')}
						description={$i18n.t('Include saved memories in the system context.')}
						labelClassName="text-gray-500 dark:text-gray-500"
					>
						<Switch bind:state={adminConfig.ENABLE_MEMORY_SYSTEM_CONTEXT} />
					</AdminSettingRow>
				{/if}
				<AdminSettingRow
					label={$i18n.t('Notes')}
					description={$i18n.t('Allow users to create and manage notes.')}
				>
					<Switch bind:state={adminConfig.ENABLE_NOTES} />
				</AdminSettingRow>
				<AdminSettingRow
					label={$i18n.t('Channels')}
					description={$i18n.t('Allow users to use channels for shared conversations.')}
				>
					<Switch bind:state={adminConfig.ENABLE_CHANNELS} />
				</AdminSettingRow>
				<AdminSettingRow
					label={$i18n.t('Calendar')}
					description={$i18n.t('Allow users to access calendar features.')}
				>
					<Switch bind:state={adminConfig.ENABLE_CALENDAR} />
				</AdminSettingRow>
				<AdminSettingRow
					label={$i18n.t('Automations')}
					description={$i18n.t('Allow users to create and run automations.')}
				>
					<Switch bind:state={adminConfig.ENABLE_AUTOMATIONS} />
				</AdminSettingRow>
				<AdminSettingRow
					label={$i18n.t('User Webhooks')}
					description={$i18n.t('Allow users to configure webhooks from their account.')}
				>
					<Switch bind:state={adminConfig.ENABLE_USER_WEBHOOKS} />
				</AdminSettingRow>
				<AdminSettingRow
					label={$i18n.t('User Status')}
					description={$i18n.t('Show user status information in the app.')}
				>
					<Switch bind:state={adminConfig.ENABLE_USER_STATUS} />
				</AdminSettingRow>

				<AdminSettingField
					label={$i18n.t('Response Watermark')}
					description={$i18n.t('Append a watermark to assistant responses when configured.')}
				>
					<Textarea
						className={textareaClass}
						placeholder={$i18n.t('Enter a watermark for the response. Leave empty for none.')}
						bind:value={adminConfig.RESPONSE_WATERMARK}
					/>
				</AdminSettingField>

				<AdminSettingField
					label={$i18n.t('WebUI URL')}
					description={$i18n.t(
						'Enter the public URL of your WebUI. This URL will be used to generate links in the notifications.'
					)}
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

			<AdminSettingSection title={$i18n.t('UI')}>
				<div>
					<div class="mb-2 flex w-full items-start justify-between gap-4">
						<div class="min-w-0">
							<div class="text-xs text-gray-600 dark:text-gray-400">{$i18n.t('Banners')}</div>
							<div class="mt-1.5 text-[0.6875rem] text-gray-400 dark:text-gray-600">
								{$i18n.t('Create announcements shown to users in the app.')}
							</div>
						</div>

						<button
							class="flex size-6 items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-black/5 hover:text-gray-900 dark:text-gray-600 dark:hover:bg-white/5 dark:hover:text-white"
							type="button"
							aria-label={$i18n.t('Add banner')}
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

					<Banners bind:banners />
				</div>
			</AdminSettingSection>
		{/if}
	</div>

	<div class="flex justify-end pt-6 text-sm font-normal">
		<button
			class="px-3.5 py-1.5 text-sm font-normal bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
