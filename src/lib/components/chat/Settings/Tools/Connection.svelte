<script lang="ts">
	import { getContext, tick } from 'svelte';
	const i18n = getContext('i18n');

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import AddToolServerModal from '$lib/components/AddToolServerModal.svelte';
	import WrenchAlt from '$lib/components/icons/WrenchAlt.svelte';

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

<div
	class="bg-gray-50 dark:bg-gray-850 rounded-lg p-4 flex flex-col justify-between border border-gray-100 dark:border-gray-800 {!(connection?.config?.enable ?? true)
		? 'opacity-50'
		: ''}"
>
	<div>
		<div class="flex items-center justify-between mb-3">
			<div class="flex items-center gap-2">
				<Tooltip content={connection?.type === 'mcp' ? $i18n.t('MCP') : $i18n.t('OpenAPI')}>
					<WrenchAlt className="w-5 h-5 opacity-70" />
				</Tooltip>
				<div class="text-xs font-medium text-gray-500">
					{connection?.type === 'mcp' ? $i18n.t('MCP') : $i18n.t('OpenAPI')}
				</div>
			</div>
			<Tooltip content={$i18n.t('Configure')}>
				<button
					class="p-1 bg-transparent hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
					on:click={() => {
						showConfigModal = true;
					}}
					type="button"
				>
					<Cog6 className="w-4 h-4" />
				</button>
			</Tooltip>
		</div>

		<button
			class="w-full text-left"
			on:click={() => {
				showConfigModal = true;
			}}
			type="button"
		>
			{#if connection?.info?.name}
				<div class="text-sm font-medium text-gray-700 dark:text-gray-200 hover:text-blue-600 dark:hover:text-blue-400 transition">
					{connection?.info?.name ?? connection?.url}
				</div>
				{#if connection?.info?.id}
					<div class="text-xs text-gray-500 mt-1">{connection?.info?.id}</div>
				{/if}
			{:else}
				<div class="text-sm font-medium text-gray-700 dark:text-gray-200 hover:text-blue-600 dark:hover:text-blue-400 transition">
					{connection?.url}
				</div>
			{/if}
		</button>
	</div>
</div>
