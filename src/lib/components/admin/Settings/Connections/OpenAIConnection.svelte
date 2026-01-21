<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import Tooltip from '$lib/components/common/Tooltip.svelte';
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

	$: isEnabled = config?.enable ?? true;
	$: displayName = config?.remark || url;
	$: tags = config?.tags ?? [];
</script>

<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	on:confirm={() => {
		onDelete();
	}}
/>

<AddConnectionModal
	edit
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
				{#if pipeline}
					<Tooltip content="Pipelines">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 24 24"
							fill="currentColor"
							class="size-4 text-blue-500"
						>
							<path
								d="M11.644 1.59a.75.75 0 0 1 .712 0l9.75 5.25a.75.75 0 0 1 0 1.32l-9.75 5.25a.75.75 0 0 1-.712 0l-9.75-5.25a.75.75 0 0 1 0-1.32l9.75-5.25Z"
							/>
							<path
								d="m3.265 10.602 7.668 4.129a2.25 2.25 0 0 0 2.134 0l7.668-4.13 1.37.739a.75.75 0 0 1 0 1.32l-9.75 5.25a.75.75 0 0 1-.71 0l-9.75-5.25a.75.75 0 0 1 0-1.32l1.37-.738Z"
							/>
							<path
								d="m10.933 19.231-7.668-4.13-1.37.739a.75.75 0 0 0 0 1.32l9.75 5.25c.221.12.489.12.71 0l9.75-5.25a.75.75 0 0 0 0-1.32l-1.37-.738-7.668 4.13a2.25 2.25 0 0 1-2.134-.001Z"
							/>
						</svg>
					</Tooltip>
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
		<div class="flex-shrink-0">
			<Cog6 className="size-4 text-gray-400 dark:text-gray-500" />
		</div>
	</div>
</button>
