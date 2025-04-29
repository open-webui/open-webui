<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { getContext } from 'svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import MessageEditIcon from '$lib/components/icons/MessageEditIcon.svelte';
	import DeleteIcon from '$lib/components/icons/DeleteIcon.svelte';
    import ShareIcon from '$lib/components/icons/ShareIcon.svelte';
    import PermissionIcon from '$lib/components/icons/PermissionIcon.svelte';
    import RevokeInvite from '$lib/components/icons/RevokeInvite.svelte';

	const i18n = getContext('i18n');

	export let editHandler: Function;
	export let deleteHandler: Function;
	export let onClose: Function;

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
	<Tooltip content={$i18n.t('More')}>
		<slot />
	</Tooltip>

	<div slot="content">
		<DropdownMenu.Content
			class="w-full max-w-[160px] rounded-lg px-1 py-1.5 border border-gray-300/30 dark:border-customGray-700 z-[10000] bg-white dark:bg-customGray-900 dark:text-white shadow"
			sideOffset={-2}
			side="bottom"
			align="start"
			transition={flyAndScale}
		>
            <DropdownMenu.Item
				class="flex  gap-2  items-center px-3 py-2 text-xs dark:text-customGray-100 font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-customGray-950 rounded-md dark:hover:text-white"
				on:click={() => {
					editHandler();
				}}
			>
				<MessageEditIcon />
				<div class="flex items-center">{$i18n.t('Resend invite')}</div>
			</DropdownMenu.Item>
            <DropdownMenu.Item
				class="flex  gap-2  items-center px-3 py-2 text-xs dark:text-customGray-100 font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-customGray-950 rounded-md dark:hover:text-white"
				on:click={() => {
					editHandler();
				}}
			>
				<ShareIcon />
				<div class="flex items-center">{$i18n.t('Copy invite link')}</div>
			</DropdownMenu.Item>
            <DropdownMenu.Item
				class="flex  gap-2  items-center px-3 py-2 text-xs dark:text-customGray-100 font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-customGray-950 rounded-md dark:hover:text-white"
				on:click={() => {
					editHandler();
				}}
			>
				<PermissionIcon />
				<div class="flex items-center">{$i18n.t('Permissions')}</div>
			</DropdownMenu.Item>
			<DropdownMenu.Item
				class="flex  gap-2  items-center px-3 py-2 text-xs dark:text-customGray-100 font-medium cursor-pointer hover:bg-gray-50 dark:hover:bg-customGray-950 rounded-md dark:hover:text-white"
				on:click={() => {
					deleteHandler();
				}}
			>
				<RevokeInvite />
				<div class="flex items-center">{$i18n.t('Revoke invite')}</div>
			</DropdownMenu.Item>
		</DropdownMenu.Content>
	</div>
</Dropdown>
