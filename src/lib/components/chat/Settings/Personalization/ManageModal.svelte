<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import { getContext } from 'svelte';

	import Modal from '$lib/components/common/Modal.svelte';
	import MemoryModal from './MemoryModal.svelte';
	import { deleteMemoriesByUserId, deleteMemoryById, getMemories } from '$lib/apis/memories';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	import XMark from '$lib/components/icons/XMark.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Search from '$lib/components/icons/Search.svelte';

	const i18n = getContext('i18n');
	dayjs.extend(localizedFormat);

	export let show = false;

	type Memory = {
		id: string;
		content: string;
		type?: string;
		path?: string;
		updated_at?: number;
	};

	let memories: Memory[] = [];
	let loading = true;
	let loaded = false;

	let query = '';

	let showMemoryModal = false;
	let selectedMemory: Memory | null = null;

	let showClearConfirmDialog = false;
	let showDeleteConfirm = false;

	const loadMemories = async () => {
		loading = true;
		memories = (await getMemories(localStorage.token)) ?? [];
		loading = false;
	};

	const editMemory = (memory: Memory) => {
		selectedMemory = memory;
		showMemoryModal = true;
	};

	const confirmDeleteMemory = (memory: Memory) => {
		selectedMemory = memory;
		showDeleteConfirm = true;
	};

	const memoryTypeLabel = (memory: Memory) =>
		(memory.type ?? 'user') === 'user' ? $i18n.t('User') : $i18n.t('Context');

	const memoryUpdatedAt = (memory: Memory) =>
		memory.updated_at ? dayjs(memory.updated_at * 1000).format('MMM D, h:mm A') : '';

	$: filteredMemories = query
		? memories.filter((memory) => {
				const value = query.toLowerCase();
				return (
					memory.content?.toLowerCase().includes(value) ||
					memory.path?.toLowerCase().includes(value) ||
					memory.type?.toLowerCase().includes(value)
				);
			})
		: memories;

	$: sortedMemories = [...filteredMemories].sort(
		(a, b) => (b.updated_at ?? 0) - (a.updated_at ?? 0)
	);

	let onClearConfirmed = async () => {
		const res = await deleteMemoriesByUserId(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res && memories.length > 0) {
			toast.success($i18n.t('Memory cleared successfully'));
			memories = [];
		}
		showClearConfirmDialog = false;
	};

	$: if (show && !loaded) {
		loaded = true;
		loadMemories();
	}

	$: if (!show) {
		query = '';
		loaded = false;
	}
</script>

<Modal size="lg" bind:show>
	<div>
		<div class="flex justify-between dark:text-gray-300 px-5 pt-4 pb-1">
			<div class="flex items-center gap-2">
				<div class="text-lg font-medium">{$i18n.t('Memory')}</div>

				{#if !loading}
					<div class="text-lg font-medium text-gray-500 dark:text-gray-500">
						{memories.length}
					</div>
				{/if}
			</div>

			<button class="self-center" on:click={() => (show = false)}>
				<XMark className="size-5" />
			</button>
		</div>

		<div class="flex flex-col w-full px-5 pb-4 dark:text-gray-200">
			<div class="flex flex-1 items-center w-full mb-1">
				<div class="self-center ml-1 mr-3">
					<Search className="size-3.5" />
				</div>
				<input
					class="w-full text-sm py-1 rounded-r-xl outline-hidden bg-transparent"
					bind:value={query}
					placeholder={$i18n.t('Search Memories')}
					maxlength="500"
				/>

				{#if query}
					<div class="self-center pl-1.5 translate-y-[0.5px] bg-transparent">
						<button
							class="p-0.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
							on:click={() => {
								query = '';
							}}
						>
							<XMark className="size-3" strokeWidth="2" />
						</button>
					</div>
				{/if}
			</div>

			<div class="flex flex-col w-full">
				{#if !loading}
					{#if sortedMemories.length === 0}
						<div
							class="text-xs text-gray-500 dark:text-gray-400 text-center px-5 min-h-20 w-full flex justify-center items-center"
						>
							{#if memories.length === 0}
								{$i18n.t('Memories accessible by LLMs will be shown here.')}
							{:else}
								{$i18n.t('No results found')}
							{/if}
						</div>
					{:else}
						<div class="text-left text-sm w-full max-h-[28rem] overflow-y-auto space-y-0.5">
							{#each sortedMemories as memory (memory.id)}
								<div class="group w-full flex justify-between items-center text-sm py-1 px-1">
									<button
										type="button"
										class="flex-1 min-w-0 text-left flex items-center gap-1.5 pr-2 text-gray-900 dark:text-gray-100 hover:text-black dark:hover:text-white transition leading-5"
										on:click={() => editMemory(memory)}
									>
										<div class="truncate leading-5">
											{memory.content}
										</div>
										<span class="shrink-0 text-[11px] leading-5 text-gray-400 dark:text-gray-500">
											{memoryTypeLabel(memory)}
										</span>
										{#if memory.path}
											<span
												class="hidden sm:block shrink min-w-0 truncate text-[11px] leading-5 text-gray-400 dark:text-gray-500"
											>
												{memory.path}
											</span>
										{/if}
										{#if memoryUpdatedAt(memory)}
											<div
												class="hidden sm:block shrink-0 text-[11px] leading-5 text-gray-400 dark:text-gray-500"
											>
												{memoryUpdatedAt(memory)}
											</div>
										{/if}
									</button>

									<div class="flex items-center shrink-0">
										<div
											class="flex items-center text-gray-500 dark:text-gray-400 opacity-70 group-hover:opacity-100 focus-within:opacity-100 transition"
										>
											<Tooltip content={$i18n.t('Edit')}>
												<button
													class="self-center w-fit text-sm p-1 leading-none hover:text-gray-900 dark:hover:text-gray-100 transition"
													on:click={(e) => {
														e.stopPropagation();
														editMemory(memory);
													}}
												>
													<Pencil className="size-4" />
												</button>
											</Tooltip>

											<Tooltip content={$i18n.t('Delete')}>
												<button
													class="self-center w-fit text-sm p-1 leading-none hover:text-gray-900 dark:hover:text-gray-100 transition"
													on:click={(e) => {
														e.stopPropagation();
														confirmDeleteMemory(memory);
													}}
												>
													<GarbageBin className="size-4" strokeWidth="1.5" />
												</button>
											</Tooltip>
										</div>
									</div>
								</div>
							{/each}
						</div>
					{/if}
				{:else}
					<div class="w-full flex justify-center items-center min-h-20">
						<Spinner className="size-4" />
					</div>
				{/if}
			</div>

			<div class="flex justify-between items-center text-sm mt-2">
				<button
					class="px-2 py-1 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:underline transition"
					on:click={() => {
						if (memories.length > 0) {
							showClearConfirmDialog = true;
						} else {
							toast.error($i18n.t('No memories to clear'));
						}
					}}>{$i18n.t('Clear memory')}</button
				>

				<button
					class="px-3.5 py-1.5 font-medium hover:bg-black/5 dark:hover:bg-white/5 outline outline-1 outline-gray-100 dark:outline-gray-800 rounded-3xl"
					on:click={() => {
						selectedMemory = null;
						showMemoryModal = true;
					}}>{$i18n.t('Add Memory')}</button
				>
			</div>
		</div>
	</div>
</Modal>

<ConfirmDialog
	title={$i18n.t('Clear Memory')}
	message={$i18n.t('Are you sure you want to clear all memories? This action cannot be undone.')}
	show={showClearConfirmDialog}
	on:confirm={onClearConfirmed}
	on:cancel={() => {
		showClearConfirmDialog = false;
	}}
/>

<ConfirmDialog
	title={$i18n.t('Delete Memory?')}
	show={showDeleteConfirm}
	on:confirm={async () => {
		if (!selectedMemory) return;

		const res = await deleteMemoryById(localStorage.token, selectedMemory.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Memory deleted successfully'));
			await loadMemories();
		}
		showDeleteConfirm = false;
	}}
	on:cancel={() => {
		showDeleteConfirm = false;
	}}
>
	<div class="text-sm text-gray-500 flex-1">
		{$i18n.t('Are you sure you want to delete this memory? This action cannot be undone.')}
		<div
			class="mt-2 bg-gray-50 dark:bg-gray-900 p-3 rounded-xl border border-gray-100 dark:border-gray-800 text-black dark:text-white whitespace-pre-wrap break-words max-h-32 overflow-y-auto"
		>
			{selectedMemory?.content}
		</div>
	</div>
</ConfirmDialog>

<MemoryModal
	bind:show={showMemoryModal}
	memory={selectedMemory}
	on:save={async () => {
		await loadMemories();
	}}
/>
