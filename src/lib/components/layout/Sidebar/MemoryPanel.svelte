<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import { getContext, onMount } from 'svelte';
	import { memories, showMemoryPanel } from '$lib/stores';
	import {
		deleteMemoriesByUserId,
		deleteMemoryById,
		getMemories
	} from '$lib/apis/memories';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import AddMemoryModal from '$lib/components/chat/Settings/Personalization/AddMemoryModal.svelte';
	import EditMemoryModal from '$lib/components/chat/Settings/Personalization/EditMemoryModal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import localizedFormat from 'dayjs/plugin/localizedFormat';

	const i18n = getContext('i18n');
	dayjs.extend(localizedFormat);

	let loading = false;
	let showAddMemoryModal = false;
	let showEditMemoryModal = false;
	let selectedMemory = null;
	let showClearConfirmDialog = false;

	const loadMemories = async () => {
		loading = true;
		try {
			const data = await getMemories(localStorage.token);
			memories.set(data || []);
		} catch (error) {
			toast.error($i18n.t('Failed to load memories'));
			console.error(error);
		} finally {
			loading = false;
		}
	};

	const onClearConfirmed = async () => {
		const res = await deleteMemoriesByUserId(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res && $memories.length > 0) {
			toast.success($i18n.t('Memory cleared successfully'));
			memories.set([]);
		}
		showClearConfirmDialog = false;
	};

	const handleDeleteMemory = async (memoryId: string) => {
		const res = await deleteMemoryById(localStorage.token, memoryId).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Memory deleted successfully'));
			await loadMemories();
		}
	};

	onMount(() => {
		if ($showMemoryPanel && $memories.length === 0) {
			loadMemories();
		}
	});

	$: if ($showMemoryPanel && $memories.length === 0 && !loading) {
		loadMemories();
	}
</script>

{#if $showMemoryPanel}
	<div class="px-2.5 mb-2 flex flex-col space-y-1">
		<!-- Header -->
		<div class="flex items-center justify-between px-2 py-2">
			<div class="text-xs font-medium text-gray-600 dark:text-gray-400">
				{$i18n.t('Memory')}
			</div>
			<div class="flex items-center gap-1">
				<Tooltip content={$i18n.t('Add Memory')}>
					<button
						class="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-900 rounded-lg transition"
						on:click={() => {
							showAddMemoryModal = true;
						}}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="2"
							stroke="currentColor"
							class="w-3.5 h-3.5"
						>
							<path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
						</svg>
					</button>
				</Tooltip>
				<Tooltip content={$i18n.t('Clear memory')}>
					<button
						class="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-900 rounded-lg transition text-red-500"
						on:click={() => {
							if ($memories.length > 0) {
								showClearConfirmDialog = true;
							} else {
								toast.error($i18n.t('No memories to clear'));
							}
						}}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="2"
							stroke="currentColor"
							class="w-3.5 h-3.5"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
							/>
						</svg>
					</button>
				</Tooltip>
			</div>
		</div>

		<!-- Memory List -->
		<div class="flex flex-col space-y-1 max-h-96 overflow-y-auto">
			{#if loading}
				<div class="text-center py-8 text-sm text-gray-500">
					{$i18n.t('Loading...')}
				</div>
			{:else if $memories.length === 0}
				<div class="text-center py-8 text-sm text-gray-500">
					<div class="mb-2">{$i18n.t('No memories yet')}</div>
					<button
						class="text-xs text-gray-600 dark:text-gray-400 hover:underline"
						on:click={() => {
							showAddMemoryModal = true;
						}}
					>
						{$i18n.t('Add your first memory')}
					</button>
				</div>
			{:else}
				{#each $memories as memory}
					<div
						class="group flex items-start gap-2 p-2 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-900 transition"
					>
						<div class="flex-1 min-w-0">
							<div class="text-sm text-gray-800 dark:text-gray-200 line-clamp-2 break-words">
								{memory.content}
							</div>
							<div class="text-xs text-gray-500 dark:text-gray-500 mt-1">
								{dayjs(memory.updated_at * 1000).format('ll')}
							</div>
						</div>
						<div class="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition">
							<Tooltip content={$i18n.t('Edit')}>
								<button
									class="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-800 rounded-lg"
									on:click={() => {
										selectedMemory = memory;
										showEditMemoryModal = true;
									}}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="1.5"
										stroke="currentColor"
										class="w-3.5 h-3.5"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Zm0 0L19.5 7.125"
										/>
									</svg>
								</button>
							</Tooltip>
							<Tooltip content={$i18n.t('Delete')}>
								<button
									class="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-800 rounded-lg text-red-500"
									on:click={() => handleDeleteMemory(memory.id)}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="1.5"
										stroke="currentColor"
										class="w-3.5 h-3.5"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
										/>
									</svg>
								</button>
							</Tooltip>
						</div>
					</div>
				{/each}
			{/if}
		</div>

		<!-- Divider -->
		<div class="border-b border-gray-100 dark:border-gray-850 my-2"></div>
	</div>
{/if}

<ConfirmDialog
	title={$i18n.t('Clear Memory')}
	message={$i18n.t('Are you sure you want to clear all memories? This action cannot be undone.')}
	show={showClearConfirmDialog}
	on:confirm={onClearConfirmed}
	on:cancel={() => {
		showClearConfirmDialog = false;
	}}
/>

<AddMemoryModal
	bind:show={showAddMemoryModal}
	on:save={async () => {
		await loadMemories();
	}}
/>

<EditMemoryModal
	bind:show={showEditMemoryModal}
	memory={selectedMemory}
	on:save={async () => {
		await loadMemories();
	}}
/>
