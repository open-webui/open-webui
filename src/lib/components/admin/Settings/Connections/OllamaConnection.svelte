<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import AddConnectionModal from '$lib/components/AddConnectionModal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';

	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import ManageOllamaModal from './ManageOllamaModal.svelte';
	import Download from '$lib/components/icons/Download.svelte';

	export let onDelete = () => {};
	export let onSubmit = () => {};

	export let url = '';
	export let idx = 0;
	export let config = {};

	let showManageModal = false;
	let showConfigModal = false;
	let showDeleteConfirmDialog = false;

	$: isEnabled = config?.enable ?? true;
	$: displayName = config?.remark || url;
	$: tags = config?.tags ?? [];
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

<button
	type="button"
	class="w-full bg-white dark:bg-gray-900 rounded-lg px-4 py-3 border border-gray-100 dark:border-gray-800 hover:border-gray-200 dark:hover:border-gray-700 transition cursor-pointer text-left {!isEnabled ? 'opacity-60' : ''}"
	on:click={() => {
		showConfigModal = true;
	}}
>
	<div class="flex items-center justify-between gap-3">
		<div class="flex-1 min-w-0">
			<div class="flex items-center gap-2 flex-wrap">
				<div class="text-sm font-medium text-gray-800 dark:text-gray-100 truncate">
					{displayName}
				</div>
				{#if !isEnabled}
					<span class="text-xs px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 rounded">
						{$i18n.t('Disabled')}
					</span>
				{/if}
				{#each tags as tag}
					<span class="text-xs px-1.5 py-0.5 bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded">
						{tag.name}
					</span>
				{/each}
			</div>
			{#if config?.remark && url}
				<div class="text-xs text-gray-400 dark:text-gray-500 truncate mt-0.5">
					{url}
				</div>
			{/if}
		</div>
		<div class="flex-shrink-0 flex items-center gap-1">
			<Tooltip content={$i18n.t('Manage Models')}>
				<button
					class="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
					on:click|stopPropagation={() => {
						showManageModal = true;
					}}
					type="button"
				>
					<Download className="size-4 text-gray-400 dark:text-gray-500" />
				</button>
			</Tooltip>
			<Cog6 className="size-4 text-gray-400 dark:text-gray-500" />
		</div>
	</div>
</button>
