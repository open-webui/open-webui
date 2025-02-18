<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { getContext, createEventDispatcher } from 'svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import Dropdown from '$lib/components/common/Dropdown.svelte';

	export let onClose: Function = () => {};
	export let devices: any;

	let show = false;
</script>

<Dropdown
	bind:show
	on:change={(e) => {
		if (e.detail === false) {
			onClose();
		}
	}}
>
	<slot />

	<div slot="content">
		<DropdownMenu.Content
			class="w-full max-w-[180px] rounded-lg px-1 py-1.5 border border-gray-300/30 dark:border-gray-700/50 z-9999 bg-white dark:bg-gray-900 dark:text-white shadow-xs"
			sideOffset={6}
			side="top"
			align="start"
			transition={flyAndScale}
		>
			{#each devices as device}
				<DropdownMenu.Item
					class="flex gap-2 items-center px-3 py-2 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
					on:click={() => {
						dispatch('change', device.deviceId);
					}}
				>
					<div class="flex items-center">
						<div class=" line-clamp-1">
							{device?.label ?? 'Camera'}
						</div>
					</div>
				</DropdownMenu.Item>
			{/each}
		</DropdownMenu.Content>
	</div>
</Dropdown>
