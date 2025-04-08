<script lang="ts">
	import { getContext, tick } from 'svelte';
	const i18n = getContext('i18n');

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import AddConnectionModal from '$lib/components/AddConnectionModal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import ManageOllamaModal from './ManageOllamaModal.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';

	export let onDelete = () => {};
	export let onSubmit = () => {};

	export let url = '';
	export let idx = 0;
	export let config = {};

	let showManageModal = false;
	let showConfigModal = false;
	let showDeleteConfirmDialog = false;
</script>

<AddConnectionModal
	ollama
	edit
	bind:show={showConfigModal}
	connection={{
		url,
		key: config?.key ?? '',
		config: config
	}}
	onDelete={() => {
		showDeleteConfirmDialog = true;
	}}
	onSubmit={(connection) => {
		url = connection.url;
		config = { ...connection.config, key: connection.key };
		onSubmit(connection);
	}}
/>

<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	on:confirm={() => {
		onDelete();
		showConfigModal = false;
	}}
/>

<ManageOllamaModal bind:show={showManageModal} urlIdx={idx} />

<div class="flex gap-1.5">
	<Tooltip
		className="w-full relative"
		content={$i18n.t(`WebUI will make requests to "{{url}}/api/chat"`, {
			url
		})}
		placement="top-start"
	>
		{#if !(config?.enable ?? true)}
			<div
				class="absolute top-0 bottom-0 left-0 right-0 opacity-60 bg-white dark:bg-gray-900 z-10"
			></div>
		{/if}

		<input
			class="input-setting"
			placeholder={$i18n.t('Enter URL (e.g. http://localhost:11434)')}
			bind:value={url}
		/>
	</Tooltip>

	<div class="flex gap-1">
		<Tooltip content={$i18n.t('Manage')} className="m-auto">
			<button
				class="self-center p-2 bg-transparent hover:bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-850 rounded-lg transition"
				on:click={() => {
					showManageModal = true;
				}}
				type="button"
			>
				<Cog6 />
			</button>
		</Tooltip>

		<Tooltip content={$i18n.t('Edit Connection')} className="m-auto">
			<button
				class="self-center p-2 bg-transparent hover:bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-850 rounded-lg transition"
				on:click={() => {
					showConfigModal = true;
				}}
				type="button"
			>
				<Pencil />
			</button>
		</Tooltip>
	</div>
</div>
