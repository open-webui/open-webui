<script lang="ts">
	import { run } from 'svelte/legacy';

	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { getContext, onMount, tick } from 'svelte';

	import { config, user, tools as _tools, mobile } from '$lib/stores';
	import { getTools } from '$lib/apis/tools';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import DocumentArrowUpSolid from '$lib/components/icons/DocumentArrowUpSolid.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import GlobeAltSolid from '$lib/components/icons/GlobeAltSolid.svelte';
	import WrenchSolid from '$lib/components/icons/WrenchSolid.svelte';
	import CameraSolid from '$lib/components/icons/CameraSolid.svelte';

	import { getI18nContext } from '$lib/contexts';
const i18n = getContext('i18n');

	interface Props {
		screenCaptureHandler: Function;
		uploadFilesHandler: Function;
		onClose?: Function;
		children?: import('svelte').Snippet;
	}

	let { screenCaptureHandler, uploadFilesHandler, onClose = () => {}, children }: Props = $props();

	let show = $state(false);

	const init = async () => {};
	run(() => {
		if (show) {
			init();
		}
	});
</script>

<Dropdown
	bind:show
	on:change={(e) => {
		if (e.detail === false) {
			onClose();
		}
	}}
>
	<Tooltip content={$i18n.t('More')}>
		{@render children?.()}
	</Tooltip>

	{#snippet content()}
		<div>
			<DropdownMenu.Content
				class="w-full max-w-[200px] rounded-xl px-1 py-1  border-gray-300/30 dark:border-gray-700/50 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-sm"
				align="start"
				alignOffset={-8}
				side="top"
				sideOffset={15}
				transition={flyAndScale}
			>
				{#if !$mobile}
					<DropdownMenu.Item
						class="flex gap-2 items-center px-3 py-2 text-sm  font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800  rounded-xl"
						on:click={() => {
							screenCaptureHandler();
						}}
					>
						<CameraSolid />
						<div class=" line-clamp-1">{$i18n.t('Capture')}</div>
					</DropdownMenu.Item>
				{/if}

				<DropdownMenu.Item
					class="flex gap-2 items-center px-3 py-2 text-sm font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
					on:click={() => {
						uploadFilesHandler();
					}}
				>
					<DocumentArrowUpSolid />
					<div class="line-clamp-1">{$i18n.t('Upload Files')}</div>
				</DropdownMenu.Item>
			</DropdownMenu.Content>
		</div>
	{/snippet}
</Dropdown>
