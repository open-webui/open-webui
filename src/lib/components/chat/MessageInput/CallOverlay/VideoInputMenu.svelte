<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';

	export let onClose: Function = () => {};
	export let devices: any;

	let show = false;
</script>

<Dropdown
	bind:show
	side="top"
	sideOffset={6}
	onOpenChange={(state) => {
		if (state === false) {
			onClose();
		}
	}}
>
	<slot />

	<div slot="content">
		<DropdownMenu className="min-w-[180px] z-[9999] dark:bg-gray-900 shadow-xs">
			{#each devices as device}
				<button
					class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md w-full"
					on:click={() => {
						dispatch('change', device.deviceId);
					}}
				>
					<div class="flex items-center">
						<div class=" line-clamp-1">
							{device?.label ?? 'Camera'}
						</div>
					</div>
				</button>
			{/each}
		</DropdownMenu>
	</div>
</Dropdown>
