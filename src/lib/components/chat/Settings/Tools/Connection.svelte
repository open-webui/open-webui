<script lang="ts">
	import { getContext, tick } from 'svelte';
	const i18n = getContext('i18n');

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import AddToolServerModal from '$lib/components/AddToolServerModal.svelte';

	export let onDelete = () => {};
	export let onSubmit = () => {};

	export let connection = null;
	export let direct = false;

	let showConfigModal = false;
	let showDeleteConfirmDialog = false;
</script>

<AddToolServerModal
	edit
	{direct}
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
	<Tooltip
		className="w-full relative"
		content={$i18n.t(`WebUI will make requests to "{{url}}"`, {
			url: `${connection?.url}/${connection?.path ?? 'openapi.json'}`
		})}
		placement="top-start"
	>
		<div class="flex w-full">
			<div class="flex-1 relative">
				<input
					class=" outline-hidden w-full bg-transparent {!(connection?.config?.enable ?? true)
						? 'opacity-50'
						: ''}"
					placeholder={$i18n.t('API Base URL')}
					bind:value={connection.url}
					autocomplete="off"
				/>
			</div>

			{#if (connection?.auth_type ?? 'bearer') === 'bearer'}
				<SensitiveInput
					inputClassName=" outline-hidden bg-transparent w-full"
					placeholder={$i18n.t('API Key')}
					bind:value={connection.key}
					required={false}
				/>
			{/if}
		</div>
	</Tooltip>

	<div class="flex gap-1">
		<Tooltip content={$i18n.t('Configure')} className="self-start">
			<button
				class="self-center p-1 bg-transparent hover:bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-850 rounded-lg transition"
				on:click={() => {
					showConfigModal = true;
				}}
				type="button"
			>
				<Cog6 />
			</button>
		</Tooltip>
	</div>
</div>
