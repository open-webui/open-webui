<script lang="ts">
	import Switch from '$lib/components/common/Switch.svelte';
	import { config, settings } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import MemoryModal from './Personalization/MemoryModal.svelte';
	import { deleteMemoriesByUserId, deleteMemoryById, getMemories } from '$lib/apis/memories';
	import { toast } from 'svelte-sonner';

	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	export let saveSettings: Function;

	// Addons
	let enableMemory = false;
	let memories: Memory[] = [];
	let loadingMemories = true;

	let showMemoryModal = false;
	let selectedMemory: Memory | null = null;
	let showClearConfirmDialog = false;
	let showDeleteConfirm = false;
	let query = '';

	type Memory = {
		id: string;
		content: string;
		type?: string;
		path?: string;
		updated_at?: number;
	};

	const loadMemories = async () => {
		loadingMemories = true;
		memories =
			(await getMemories(localStorage.token).catch((error) => {
				toast.error(`${error}`);
				return [];
			})) ?? [];
		loadingMemories = false;
	};

	const confirmDeleteMemory = (memory: Memory) => {
		selectedMemory = memory;
		showDeleteConfirm = true;
	};

	const editMemory = (memory: Memory) => {
		selectedMemory = memory;
		showMemoryModal = true;
	};

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

	onMount(async () => {
		enableMemory = $settings?.memory ?? $config?.features?.enable_memories ?? false;
		await loadMemories();
	});
</script>

<form
	id="tab-personalization"
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={() => {
		dispatch('save');
	}}
>
	<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-4">
		{$i18n.t('Personalization')}
	</h2>

	<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5 py-1">
		<div>
			<div class="flex items-center justify-between mb-1">
				<Tooltip
					content={$i18n.t(
						'This is an experimental feature, it may not function as expected and is subject to change at any time.'
					)}
				>
					<div class="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-600">
						{$i18n.t('Memory')}
						<span
							class="inline-flex items-center text-[0.625rem] font-normal uppercase leading-none text-gray-400 dark:text-gray-600"
							>{$i18n.t('Experimental')}</span
						>
					</div>
				</Tooltip>

				<div class="">
					<Switch
						bind:state={enableMemory}
						on:change={async () => {
							saveSettings({ memory: enableMemory });
						}}
					/>
				</div>
			</div>
			<p class="-mt-1 text-[0.6875rem] text-gray-400 dark:text-gray-600">
				{$i18n
					.t(
						"You can personalize your interactions with LLMs by adding memories through the 'Manage' button below, making them more helpful and tailored to you."
					)
					.replace($i18n.t('Manage'), $i18n.t('Add Memory'))}
			</p>
		</div>

		{#if enableMemory}
			<div class="mt-5">
				<div class="flex items-center justify-between mb-2">
					<div class="flex items-center gap-2">
						<h3 class="text-xs text-gray-400 dark:text-gray-600">
							{$i18n.t('Memory')}
						</h3>

						{#if !loadingMemories}
							<div class="text-xs text-gray-400 dark:text-gray-600">{memories.length}</div>
						{/if}
					</div>

					<button
						type="button"
						class="text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition"
						on:click={() => {
							selectedMemory = null;
							showMemoryModal = true;
						}}
					>
						{$i18n.t('Add Memory')}
					</button>
				</div>

				{#if loadingMemories}
					<div class="w-full flex justify-center items-center min-h-16">
						<Spinner className="size-4" />
					</div>
				{:else}
					{#if memories.length > 0}
						<div class="flex items-center gap-2 mb-3">
							<input
								class="w-full text-xs py-1 bg-transparent outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700"
								bind:value={query}
								placeholder={$i18n.t('Search Memories')}
								maxlength="500"
							/>

							{#if query}
								<button
									type="button"
									class="shrink-0 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
									on:click={() => {
										query = '';
									}}
								>
									{$i18n.t('Clear')}
								</button>
							{/if}
						</div>
					{/if}

					{#if sortedMemories.length === 0}
						<div class="text-xs text-gray-500 dark:text-gray-400 min-h-16 flex items-center">
							{#if memories.length === 0}
								{$i18n.t('Memories accessible by LLMs will be shown here.')}
							{:else}
								{$i18n.t('No results found')}
							{/if}
						</div>
					{:else}
						<div class="flex flex-col gap-2.5">
							{#each sortedMemories as memory (memory.id)}
								<div class="flex items-start justify-between gap-3">
									<div
										class="min-w-0 whitespace-pre-wrap break-words text-xs text-gray-600 dark:text-gray-400"
									>
										{memory.content}
									</div>
									<div class="flex shrink-0 items-center gap-2">
										<button
											type="button"
											class="text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
											on:click={() => editMemory(memory)}
										>
											{$i18n.t('Edit')}
										</button>
										<button
											type="button"
											class="text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
											on:click={() => confirmDeleteMemory(memory)}
										>
											{$i18n.t('Remove')}
										</button>
									</div>
								</div>
							{/each}
						</div>
					{/if}

					<button
						type="button"
						class="mt-3 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 hover:underline transition"
						on:click={() => {
							if (memories.length > 0) {
								showClearConfirmDialog = true;
							} else {
								toast.error($i18n.t('No memories to clear'));
							}
						}}
					>
						{$i18n.t('Clear memory')}
					</button>
				{/if}
			</div>
		{/if}
	</div>

	<div class="shrink-0 flex justify-end text-sm font-normal">
		<button
			class="px-3.5 py-1.5 text-sm font-normal bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>

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
