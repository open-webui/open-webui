<script lang="ts">
	import { getVersionUpdates } from '$lib/apis';
	import { getOllamaVersion } from '$lib/apis/ollama';
	import { WEBUI_BUILD_HASH, WEBUI_VERSION } from '$lib/constants';
	import { WEBUI_NAME, config, showChangelog } from '$lib/stores';
	import { compareVersion } from '$lib/utils';
	import { onMount, getContext } from 'svelte';

	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	let ollamaVersion = '';

	let updateAvailable = null;
	let version = {
		current: '',
		latest: ''
	};

	const currentYear = new Date().getFullYear();

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

		checkForVersionUpdates();
	});
</script>

<div class="flex flex-col h-full justify-between space-y-3 text-sm mb-6">
	<div class=" space-y-3 overflow-y-scroll max-h-[28rem] lg:max-h-full">
		<div>
			<div class=" mb-2.5 text-sm font-medium flex space-x-2 items-center">
				<div>
					{$WEBUI_NAME}
					{$i18n.t('Version')}
				</div>
			</div>
			<div class="flex w-full justify-between items-center">
				<div class="flex flex-col text-xs text-gray-700 dark:text-gray-200">
					<div class="flex gap-1">
						<Tooltip content={WEBUI_BUILD_HASH}>
							v{WEBUI_VERSION}
						</Tooltip>

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
					</div>

					<button
						class=" underline flex items-center space-x-1 text-xs text-gray-500 dark:text-gray-500"
						on:click={() => {
							showChangelog.set(true);
						}}
					>
						<div>{$i18n.t("See what's new")}</div>
					</button>
				</div>

				<button
					class=" text-xs px-3 py-1.5 bg-gray-100 hover:bg-gray-200 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-lg font-medium"
					on:click={() => {
						checkForVersionUpdates();
					}}
				>
					{$i18n.t('Check for updates')}
				</button>
			</div>
		</div>

		{#if ollamaVersion}
			<hr class=" border-gray-100 dark:border-gray-850" />

			<div>
				<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Ollama Version')}</div>
				<div class="flex w-full">
					<div class="flex-1 text-xs text-gray-700 dark:text-gray-200">
						{ollamaVersion ?? 'N/A'}
					</div>
				</div>
			</div>
		{/if}

		<hr class=" border-gray-100 dark:border-gray-850" />

		{#if $config?.license_metadata}
			<div class="mb-2 text-xs">
				{#if !$WEBUI_NAME.includes('Evolution')}
					{$i18n.t('This is a fork of')}

					{#if $WEBUI_NAME === 'Ollama'}
						<a
							href="https://ollama.com"
							target="_blank"
							class="text-gray-500 dark:text-gray-300 font-medium"
						>Ollama</a>
					{:else}
							<span class="text-gray-500 dark:text-gray-300 font-medium">{$WEBUI_NAME}</span> -
				{/if}
				{/if}

				<span class=" capitalize">{$config?.license_metadata?.type}</span> license purchased by
				<span class=" capitalize">{$config?.license_metadata?.organization_name}</span>
			</div>
		{:else}
			<div class="flex space-x-1">
				<a href="https://x.com/BIGLao666" target="_blank">
					<img
						alt="X (formerly Twitter) Follow"
						src="https://img.shields.io/badge/twitter-Evolution-follow"
					/>
				</a>
				<a href="http://weixin.qq.com/r/mp/gha7o2LELT9SrSbA90OQ" target="_blank">
					<img
						alt="WeChat"
						src="https://img.shields.io/badge/WeChat-Evolution-brightgreen"
					/>
				</a>
			</div>
		{/if}

		<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
			Emoji graphics provided by
			<a href="https://github.com/jdecked/twemoji" target="_blank">Twemoji</a>, licensed under
			<a href="https://creativecommons.org/licenses/by/4.0/" target="_blank">CC-BY 4.0</a>.
		</div>

		<div class="text-xs text-gray-400 dark:text-gray-500 mt-2">
			Evolution is built on top of open WebUI.<br />
			Copyright (c) {currentYear}
			<a
				href="https://zhangbusan.notion.site/EvolutionAI-1cdf938ebd6e807b884fe76042addb51"
				target="_blank"
				class="underline"
			>
				Evolution (Johnny Zhang)
			</a>
			<br />
			Copyright (c) {currentYear}
			<a
				href="https://openwebui.com"
				target="_blank"
				class="underline"
			>
				Open WebUI (Timothy Jaeryang Baek)
			</a>
			<br />
			All rights reserved.<br /><br />
			Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:<br />
			1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.<br />
			2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.<br />
			3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
		</div>
	</div>
</div>