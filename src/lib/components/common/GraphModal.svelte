<script lang="ts">
	import { getContext } from 'svelte';

	import Modal from '$lib/components/common/Modal.svelte';
	import FullHeightIframe from '$lib/components/common/FullHeightIframe.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import { settings } from '$lib/stores';

	const i18n = getContext('i18n');

	export let show = false;
	export let url = '';
</script>

<Modal size="lg" bind:show>
	<div>
		<div class="flex justify-between dark:text-gray-300 px-4.5 pt-3 pb-2">
			<div class="text-xs font-normal text-gray-500 dark:text-gray-400 self-center truncate">
				{url}
			</div>
			<button
				class="self-center rounded-lg p-1 text-gray-500 transition hover:bg-gray-50 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200"
				aria-label={$i18n.t('Close')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark className={'size-4'} />
			</button>
		</div>

		<div class="w-full h-[70vh] px-5 pb-5">
			<FullHeightIframe
				src={url}
				title={$i18n.t('Record graph')}
				iframeClassName="w-full h-full rounded-none"
				allowScripts={true}
				allowForms={$settings?.iframeSandboxAllowForms ?? false}
				allowSameOrigin={$settings?.iframeSandboxAllowSameOrigin ?? false}
				allowPopups={true}
			/>
		</div>
	</div>
</Modal>
