<script lang="ts">
	import { getContext, tick } from 'svelte';
	const i18n = getContext('i18n');

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import AddConnectionModal from './AddConnectionModal.svelte';

	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import Wrench from '$lib/components/icons/Wrench.svelte';
	import ManageOllamaModal from './ManageOllamaModal.svelte';
	import ArrowDownTray from '$lib/components/icons/ArrowDownTray.svelte';

	export let onDelete = () => {};
	export let onSubmit = () => {};

	export let url = '';
	export let idx = 0;
	export let config = {};

	let showManageModal = false;
	let showConfigModal = false;
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
	{onDelete}
	onSubmit={(connection) => {
		url = connection.url;
		config = { ...connection.config, key: connection.key };
		onSubmit(connection);
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
			class="w-full text-sm bg-transparent outline-none"
			placeholder={$i18n.t('Enter URL (e.g. http://localhost:11434)')}
			bind:value={url}
		/>
	</Tooltip>

	<div class="flex gap-1">
		<Tooltip content={$i18n.t('Manage')} className="self-start">
			<button
				class="self-center p-1 bg-transparent hover:bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-850 rounded-lg transition"
				on:click={() => {
					showManageModal = true;
				}}
				type="button"
			>
				<ArrowDownTray />
			</button>
		</Tooltip>

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
