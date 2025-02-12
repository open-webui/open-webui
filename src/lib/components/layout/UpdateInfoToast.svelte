<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import { showChangelog } from '$lib/stores';

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
	class="flex items-start bg-[#F1F8FE] dark:bg-[#020C1D] border border-[3371D5] dark:border-[#03113B] text-[#3371D5] dark:text-[#6795EC] rounded-lg px-3.5 py-3 text-xs max-w-80 pr-2 w-full shadow-lg"
>
	<div class="flex-1 font-medium">
		{$i18n.t(`A new Canchat version (v{{LATEST_VERSION}}) is now available.`, {
			LATEST_VERSION: version.latest
		})}

		<button class="underline" on:click={() => showChangelog.set(true)}>
			{$i18n.t('See the latest features and improvements')}
		</button>
	</div>

	<div class=" flex-shrink-0 pr-1">
		<button
			class=" hover:text-blue-900 dark:hover:text-blue-300 transition"
			on:click={() => {
				dispatch('close');
			}}
		>
			<XMark />
		</button>
	</div>
</div>
