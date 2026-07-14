<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';

	import { config, user, tools as _tools, mobile } from '$lib/stores';
	import { getTools } from '$lib/apis/tools';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import DocumentArrowUpSolid from '$lib/components/icons/DocumentArrowUpSolid.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import GlobeAltSolid from '$lib/components/icons/GlobeAltSolid.svelte';
	import WrenchSolid from '$lib/components/icons/WrenchSolid.svelte';
	import CameraSolid from '$lib/components/icons/CameraSolid.svelte';
	import Camera from '$lib/components/icons/Camera.svelte';
	import Clip from '$lib/components/icons/Clip.svelte';

	const i18n = getContext('i18n');

	export let screenCaptureHandler: Function;
	export let uploadFilesHandler: Function;

	export let onClose: Function = () => {};

	let show = false;

	$: if (show) {
		init();
	}

	const init = async () => {};
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
		<slot />
	</Tooltip>

	<div slot="content">
		<DropdownMenu className="w-[200px] z-999 transition">
			<button
				class="select-none flex w-full gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-xl"
				type="button"
				on:click={() => {
					uploadFilesHandler();
					show = false;
				}}
			>
				<Clip />
				<div class="line-clamp-1">{$i18n.t('Upload Files')}</div>
			</button>

			<button
				class="select-none flex w-full gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50 rounded-xl"
				type="button"
				on:click={() => {
					screenCaptureHandler();
					show = false;
				}}
			>
				<Camera />
				<div class=" line-clamp-1">{$i18n.t('Capture')}</div>
			</button>
		</DropdownMenu>
	</div>
</Dropdown>
