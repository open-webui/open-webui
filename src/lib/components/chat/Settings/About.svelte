<script lang="ts">
	import { getVersionUpdates } from '$lib/apis';
	import { getOllamaVersion } from '$lib/apis/ollama';
	import { Falcor_BUILD_HASH, Falcor_VERSION } from '$lib/constants';
	import { Falcor_NAME, config, showChangelog } from '$lib/stores';
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

	const checkForVersionUpdates = async () => {
		updateAvailable = null;
		version = await getVersionUpdates(localStorage.token).catch((error) => {
			return {
				current: Falcor_VERSION,
				latest: Falcor_VERSION
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
	<div class=" space-y-3">
		<div>
			<div class=" mb-2.5 text-sm font-medium flex space-x-2 items-center">
				<div>
					{$Falcor_NAME}
					{$i18n.t('Version')}
				</div>
			</div>
			<div class="flex w-full justify-between items-center">
				<div class="flex flex-col text-xs text-gray-700 dark:text-gray-200">
					<div class="flex gap-1">
						<Tooltip content={Falcor_BUILD_HASH}>
							v{Falcor_VERSION}
						</Tooltip>

						<a
							href="https://github.com/dangerpotter/open-webui/releases/tag/v{version.latest}"
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
			<hr class=" dark:border-gray-850" />

			<div>
				<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Ollama Version')}</div>
				<div class="flex w-full">
					<div class="flex-1 text-xs text-gray-700 dark:text-gray-200">
						{ollamaVersion ?? 'N/A'}
					</div>
				</div>
			</div>
		{/if}

		<hr class=" dark:border-gray-850" />

		<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
			{#if !$Falcor_NAME.includes('Falcor')}
				<span class=" text-gray-500 dark:text-gray-300 font-medium">{$Falcor_NAME}</span> -
			{/if}
			{$i18n.t('Modified from OpenWeb UI for Capella University by')}
			<a
				class=" text-gray-500 dark:text-gray-300 font-medium"
				href="https://github.com/dangerpotter"
				target="_blank">Austin Potter</a
			>
		</div>
	</div>
</div>
