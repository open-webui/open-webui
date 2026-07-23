<script lang="ts">
	import { getVersionUpdates } from '$lib/apis';
	import { getOllamaVersion } from '$lib/apis/ollama';
	import { WEBUI_BUILD_HASH, WEBUI_VERSION } from '$lib/constants';
	import { WEBUI_NAME, config, showChangelog } from '$lib/stores';
	import { compareVersion } from '$lib/utils';
	import { onMount, getContext } from 'svelte';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import UserSettingRow from './UserSettingRow.svelte';
	import UserSettingSection from './UserSettingSection.svelte';

	const i18n = getContext('i18n');

	let ollamaVersion = '';

	let updateAvailable = null;
	let version = {
		current: '',
		latest: ''
	};
	const actionButtonClass =
		'text-xs text-gray-500 transition-colors hover:text-gray-900 dark:text-gray-500 dark:hover:text-white';

	const checkForVersionUpdates = async () => {
		updateAvailable = null;
		version = await getVersionUpdates(localStorage.token).catch((error) => {
			return {
				current: WEBUI_VERSION,
				latest: WEBUI_VERSION
			};
		});

		console.log(version);

		updateAvailable = compareVersion(version.latest, version.current);
		console.log(updateAvailable);
	};

	onMount(async () => {
		ollamaVersion = await getOllamaVersion(localStorage.token).catch((error) => {
			return '';
		});

		if ($config?.features?.enable_version_update_check) {
			checkForVersionUpdates();
		}
	});
</script>

<div id="tab-about" class="flex flex-col h-full justify-between text-sm">
	<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-4">{$i18n.t('About')}</h2>

	<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5">
		<UserSettingSection title={`${$WEBUI_NAME} ${$i18n.t('Version')}`} first>
			<UserSettingRow
				description={$i18n.t('View the installed version and check release updates.')}
			>
				<div slot="label" class="flex flex-col text-xs text-gray-600 dark:text-gray-400">
					<div class="flex gap-1">
						<Tooltip content={WEBUI_BUILD_HASH}>
							v{WEBUI_VERSION}
						</Tooltip>

						{#if $config?.features?.enable_version_update_check}
							<a
								href="https://github.com/open-webui/open-webui/releases/tag/v{version.latest}"
								target="_blank"
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
						class={actionButtonClass}
						on:click={() => {
							showChangelog.set(true);
						}}
					>
						<div>{$i18n.t("See what's new")}</div>
					</button>
				</div>

				{#if $config?.features?.enable_version_update_check}
					<button
						class={actionButtonClass}
						on:click={() => {
							checkForVersionUpdates();
						}}
					>
						{$i18n.t('Check for updates')}
					</button>
				{/if}
			</UserSettingRow>
		</UserSettingSection>

		{#if ollamaVersion}
			<UserSettingSection title={$i18n.t('Ollama Version')}>
				<div class="text-xs text-gray-600 dark:text-gray-400">
					{ollamaVersion ?? 'N/A'}
				</div>
			</UserSettingSection>
		{/if}

		<UserSettingSection title={$i18n.t('Community')}>
			{#if $config?.license_metadata}
				<div class="text-xs text-gray-600 dark:text-gray-400">
					{#if !$WEBUI_NAME.includes('Open WebUI')}
						<span>{$WEBUI_NAME}</span> -
					{/if}

					<span class="capitalize">{$config?.license_metadata?.type}</span> license purchased by
					<span class="capitalize">{$config?.license_metadata?.organization_name}</span>
				</div>
			{:else}
				<div class="flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-400 dark:text-gray-600">
					<a
						class="hover:text-gray-700 dark:hover:text-gray-400"
						href="https://discord.gg/5rJgQTnV4s"
						target="_blank">Discord</a
					>
					<a
						class="hover:text-gray-700 dark:hover:text-gray-400"
						href="https://twitter.com/OpenWebUI"
						target="_blank">X</a
					>
					<a
						class="hover:text-gray-700 dark:hover:text-gray-400"
						href="https://github.com/open-webui/open-webui"
						target="_blank">GitHub</a
					>
				</div>
			{/if}

			<div class="text-xs text-gray-400 dark:text-gray-500">
				Emoji graphics provided by
				<a href="https://github.com/jdecked/twemoji" target="_blank">Twemoji</a>, licensed under
				<a href="https://creativecommons.org/licenses/by/4.0/" target="_blank">CC-BY 4.0</a>.
			</div>

			<div class="text-xs text-gray-400 dark:text-gray-500">
				Copyright (c) {new Date().getFullYear()}
				<a href="https://openwebui.com" target="_blank" class="underline">Open WebUI Inc.</a>
				<a href="https://github.com/open-webui/open-webui/blob/main/LICENSE" target="_blank"
					>All rights reserved.</a
				>
			</div>

			<div class="text-xs text-gray-400 dark:text-gray-500">
				{$i18n.t('Created by')}
				<a class="text-gray-500 dark:text-gray-400" href="https://github.com/tjbck" target="_blank"
					>Tim J. Baek</a
				>
			</div>
		</UserSettingSection>
	</div>
</div>
