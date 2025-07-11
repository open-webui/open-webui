<script lang="ts">
	import { WEBUI_BUILD_HASH, WEBUI_VERSION } from '$lib/constants';
	import { WEBUI_NAME, showChangelog } from '$lib/stores';
	import { getContext } from 'svelte';

	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	let version = {
		current: '',
		latest: ''
	};
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
							href="https://github.com/ssc-dsai/canchat-v2/releases/tag/v{version.current}"
							target="_blank"
						>
							{$i18n.t('(latest)')}
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
			</div>
		</div>

		<hr class=" dark:border-gray-850" />

		<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
			Emoji graphics provided by
			<a class="underline" href="https://github.com/jdecked/twemoji" target="_blank">Twemoji</a>,
			licensed under
			<a class="underline" href="https://creativecommons.org/licenses/by/4.0/" target="_blank"
				>CC-BY 4.0</a
			>.
		</div>
		<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
			Application based on
			<a class="underline" href="https://github.com/open-webui/open-webui" target="_blank"
				>Open WebUI</a
			>, licensed under
			<a class="underline" href="https://opensource.org/license/BSD-3-clause" target="_blank"
				>BSD-3-clause</a
			>.
		</div>
	</div>
</div>
