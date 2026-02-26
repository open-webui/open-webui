<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import Switch from '$lib/components/common/Switch.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import AddTerminalServerModal from '$lib/components/AddTerminalServerModal.svelte';
	import Cloud from '$lib/components/icons/Cloud.svelte';

	export let connection = { url: '', key: '', name: '', path: '/openapi.json', enabled: false };
	export let onSubmit: (c: typeof connection) => void = () => {};
	export let onDelete: () => void = () => {};
	export let onEnable: () => void = () => {};
	export let onDisable: () => void = () => {};

	let showConfigModal = false;
	let showDeleteConfirmDialog = false;
</script>

<AddTerminalServerModal
	edit
	bind:show={showConfigModal}
	{connection}
	onDelete={() => {
		showDeleteConfirmDialog = true;
	}}
	onSubmit={(c) => {
		connection = c;
		onSubmit(c);
	}}
/>

<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	on:confirm={() => {
		onDelete();
		showConfigModal = false;
	}}
/>

<div class="flex w-full gap-2 items-center">
	<Tooltip className="w-full relative" content={''} placement="top-start">
		<div class="flex w-full">
			<div
				class="flex-1 relative flex gap-1.5 items-center {!connection.enabled ? 'opacity-50' : ''}"
			>
				<Tooltip content={$i18n.t('Terminal')}>
					<Cloud className="size-4" strokeWidth="1.5" />
				</Tooltip>

				<div class="capitalize outline-hidden w-full bg-transparent text-sm">
					{connection.name || connection.url || $i18n.t('New Terminal')}
				</div>
			</div>
		</div>
	</Tooltip>

	<div class="flex gap-1 items-center">
		<Tooltip content={$i18n.t('Configure')}>
			<button
				class="self-center p-1 bg-transparent hover:bg-gray-100 dark:hover:bg-gray-850 rounded-lg transition"
				on:click={() => {
					showConfigModal = true;
				}}
				type="button"
			>
				<Cog6 />
			</button>
		</Tooltip>

		<Tooltip content={connection.enabled ? $i18n.t('Enabled') : $i18n.t('Disabled')}>
			<Switch state={connection.enabled} on:change={() => connection.enabled ? onDisable() : onEnable()} />
		</Tooltip>
	</div>
</div>
