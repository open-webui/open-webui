<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import { getContext, createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	import Modal from '$lib/components/common/Modal.svelte';
	import AddMemoryModal from './AddMemoryModal.svelte';
	import { deleteMemoriesByUserId, deleteMemoryById, getMemories } from '$lib/apis/memories';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EditMemoryModal from './EditMemoryModal.svelte';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	import XMark from '$lib/components/icons/XMark.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';

	const i18n = getContext('i18n');
	dayjs.extend(localizedFormat);

	export let show = false;

	let memories = [];
	let loading = true;

	let query = '';
	let orderBy = 'updated_at';
	let direction = 'desc';

	const setSortKey = (key: string) => {
		if (orderBy === key) {
			direction = direction === 'asc' ? 'desc' : 'asc';
		} else {
			orderBy = key;
			direction = 'asc';
		}
	};

	let showAddMemoryModal = false;
	let showEditMemoryModal = false;

	let selectedMemory = null;

	let showClearConfirmDialog = false;
	let showDeleteConfirm = false;

	$: filteredMemories = query
		? memories.filter((m) => m.content?.toLowerCase().includes(query.toLowerCase()))
		: memories;

	$: sortedMemories = [...filteredMemories].sort((a, b) => {
		let aVal, bVal;
		if (orderBy === 'content') {
			aVal = (a.content ?? '').toLowerCase();
			bVal = (b.content ?? '').toLowerCase();
		} else {
			aVal = a.updated_at ?? 0;
			bVal = b.updated_at ?? 0;
		}
		if (direction === 'asc') {
			return aVal > bVal ? 1 : -1;
		} else {
			return aVal < bVal ? 1 : -1;
		}
	});

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

	$: if (show && memories.length === 0 && loading) {
		(async () => {
			memories = await getMemories(localStorage.token);
			loading = false;
		})();
	}
</script>

<Modal size="lg" bind:show>
	<div>
		<!-- Header -->
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
			<!-- Search -->
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

			<!-- Memories List -->
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
						{#if sortedMemories.length > 0}
							<div class="flex text-xs font-medium mb-1">
								<button
									class="px-1.5 py-1 cursor-pointer select-none basis-3/5"
									on:click={() => setSortKey('content')}
								>
									<div class="flex gap-1.5 items-center">
										{$i18n.t('Content')}
										{#if orderBy === 'content'}
											<span class="font-normal">
												{#if direction === 'asc'}
													<ChevronUp className="size-2" />
												{:else}
													<ChevronDown className="size-2" />
												{/if}
											</span>
										{:else}
											<span class="invisible">
												<ChevronUp className="size-2" />
											</span>
										{/if}
									</div>
								</button>
								<button
									class="px-1.5 py-1 cursor-pointer select-none hidden sm:flex sm:basis-2/5 justify-end"
									on:click={() => setSortKey('updated_at')}
								>
									<div class="flex gap-1.5 items-center">
										{$i18n.t('Updated at')}
										{#if orderBy === 'updated_at'}
											<span class="font-normal">
												{#if direction === 'asc'}
													<ChevronUp className="size-2" />
												{:else}
													<ChevronDown className="size-2" />
												{/if}
											</span>
										{:else}
											<span class="invisible">
												<ChevronUp className="size-2" />
											</span>
										{/if}
									</div>
								</button>
							</div>
						{/if}

						<div class="text-left text-sm w-full max-h-[28rem] overflow-y-auto">
							{#each sortedMemories as memory (memory.id)}
								<div
									class="w-full flex justify-between items-center rounded-xl text-sm py-2 px-3 hover:bg-gray-50 dark:hover:bg-gray-850 transition cursor-pointer"
									on:click={() => {
										selectedMemory = memory;
										showEditMemoryModal = true;
									}}
								>
									<div class="flex-1 min-w-0 pr-2">
										<div class="text-ellipsis line-clamp-1">{memory.content}</div>
										<div class="text-xs text-gray-500 dark:text-gray-400">
											{dayjs(memory.updated_at * 1000).format('MMM D, YYYY')}
										</div>
									</div>

									<div class="flex items-center shrink-0">
										<div
											class="hidden sm:flex text-gray-500 dark:text-gray-400 text-xs whitespace-nowrap mr-2"
										>
											{dayjs(memory.updated_at * 1000).format('h:mm A')}
										</div>

										<div class="flex text-gray-600 dark:text-gray-300">
											<Tooltip content={$i18n.t('Edit')}>
												<button
													class="self-center w-fit text-sm p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
													on:click={(e) => {
														e.stopPropagation();
														selectedMemory = memory;
														showEditMemoryModal = true;
													}}
												>
													<Pencil className="size-4" />
												</button>
											</Tooltip>

											<Tooltip content={$i18n.t('Delete')}>
												<button
													class="self-center w-fit text-sm p-1.5 hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
													on:click={(e) => {
														e.stopPropagation();
														selectedMemory = memory;
														showDeleteConfirm = true;
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

			<!-- Footer -->
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
						showAddMemoryModal = true;
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
		const res = await deleteMemoryById(localStorage.token, selectedMemory.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Memory deleted successfully'));
			memories = await getMemories(localStorage.token);
		}
		showDeleteConfirm = false;
	}}
	on:cancel={() => {
		showDeleteConfirm = false;
	}}
>
	<div class=" text-sm text-gray-500 flex-1">
		{$i18n.t('Are you sure you want to delete this memory? This action cannot be undone.')}
		<div
			class=" mt-2 bg-gray-50 dark:bg-gray-900 p-3 rounded-xl border border-gray-100 dark:border-gray-800 text-black dark:text-white whitespace-pre-wrap break-words max-h-32 overflow-y-auto"
		>
			{selectedMemory?.content}
		</div>
	</div>
</ConfirmDialog>

<AddMemoryModal
	bind:show={showAddMemoryModal}
	on:save={async () => {
		memories = await getMemories(localStorage.token);
	}}
/>

<EditMemoryModal
	bind:show={showEditMemoryModal}
	memory={selectedMemory}
	on:save={async () => {
		memories = await getMemories(localStorage.token);
	}}
/>
