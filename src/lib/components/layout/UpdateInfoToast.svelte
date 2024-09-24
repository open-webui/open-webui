<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import { WEBUI_VERSION } from '$lib/constants';
	import XMark from '../icons/XMark.svelte';

	export let version = {
		current: WEBUI_VERSION,
		latest: WEBUI_VERSION
	};
</script>

<div
	class="flex items-start bg-[--info-bg] border border-[--info-border] text-[--info-text] rounded-lg px-3.5 py-3 text-xs"
>
	<div class="flex-1 font-medium">
		{$i18n.t(`A new version (v{{LATEST_VERSION}}) is now available.`, {
			LATEST_VERSION: version.latest
		})}

		<a
			href="https://github.com/open-webui/open-webui/releases/tag/v{version.latest}"
			target="_blank"
			class="underline"
		>
			{$i18n.t('Update for the latest features and improvements.')}</a
		>
	</div>

	<div class=" flex-shrink-0 pl-2">
		<button
			class=" hover:text-blue-900 dark:hover:text-blue-300 transition"
			on:click={() => {
				console.log('closeToast');
				dispatch('closeToast');
			}}
		>
			<XMark />
		</button>
	</div>
</div>
