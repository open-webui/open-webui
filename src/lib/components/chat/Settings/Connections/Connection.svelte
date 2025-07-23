<script lang="ts">
	import { getContext, tick } from 'svelte';
	const i18n = getContext('i18n');

	import { settings } from '$lib/stores';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import AddConnectionModal from '$lib/components/AddConnectionModal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	export let onDelete = () => {};
	export let onSubmit = () => {};

	export let pipeline = false;

	export let url = '';
	export let key = '';
	export let config = {};

	let showConfigModal = false;
	let showDeleteConfirmDialog = false;
</script>

<AddConnectionModal
	edit
	direct
	bind:show={showConfigModal}
	connection={{
		url,
		key,
		config
	}}
	onDelete={() => {
		showDeleteConfirmDialog = true;
	}}
	onSubmit={(connection) => {
		url = connection.url;
		key = connection.key;
		config = connection.config;
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

<div class="flex w-full gap-2 items-center">
	<Tooltip
		className="w-full relative"
		content={$i18n.t(`WebUI will make requests to "{{url}}/chat/completions"`, {
			url
		})}
		placement="top-start"
	>
		{#if !(config?.enable ?? true)}
			<div
				class="absolute top-0 bottom-0 left-0 right-0 opacity-60 bg-white dark:bg-gray-900 z-10"
			></div>
		{/if}
		<div class="flex w-full gap-2">
			<div class="flex-1 relative">
				<input
					class={`w-full bg-transparent ${($settings?.highContrastMode ?? false) ? '' : 'outline-hidden'} ${pipeline ? 'pr-8' : ''}`}
					placeholder={$i18n.t('API Base URL')}
					bind:value={url}
					autocomplete="off"
				/>
			</div>

			<SensitiveInput
				inputClassName="bg-transparent w-full"
				placeholder={$i18n.t('API Key')}
				bind:value={key}
			/>
		</div>
	</Tooltip>

	<div class="flex gap-1">
		<Tooltip content={$i18n.t('Configure')} className="self-start">
			<button
				aria-label={$i18n.t('Open modal to configure connection')}
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
