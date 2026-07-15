<script lang="ts">
	import Switch from '$lib/components/common/Switch.svelte';
	import { config, settings } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import MemoryModal from './Personalization/MemoryModal.svelte';
	import { deleteMemoriesByUserId, deleteMemoryById, getMemories } from '$lib/apis/memories';
	import { toast } from 'svelte-sonner';
	import UserSettingRow from './UserSettingRow.svelte';
	import UserSettingSection from './UserSettingSection.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Trash from '$lib/components/icons/Trash.svelte';

	const dispatch = createEventDispatcher();

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let saveSettings: (settings: any) => void | Promise<void>;

	// Addons
	let enableMemory = false;
	let memories: Memory[] = [];
	let loadingMemories = true;

	let showMemoryModal = false;
	let selectedMemory: Memory | null = null;
	let showClearConfirmDialog = false;
	let showDeleteConfirm = false;
	let query = '';
	const inputClass =
		'h-7 w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';
	const actionButtonClass =
		'shrink-0 text-xs text-gray-500 transition-colors hover:text-gray-900 dark:text-gray-500 dark:hover:text-white';

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
	class="flex flex-col h-full justify-between text-sm"
	on:submit|preventDefault={() => {
		dispatch('save');
	}}
>
	<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-4">
		{$i18n.t('Personalization')}
	</h2>

	<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5">
		<UserSettingSection title={$i18n.t('Memory')} first>
			<UserSettingRow
				description={$i18n
					.t(
						"You can personalize your interactions with LLMs by adding memories through the 'Manage' button below, making them more helpful and tailored to you."
					)
					.replace($i18n.t('Manage'), $i18n.t('Add Memory'))}
			>
				<Tooltip
					slot="label"
					content={$i18n.t(
						'This is an experimental feature, it may not function as expected and is subject to change at any time.'
					)}
				>
					<div class="flex items-center gap-2">
						{$i18n.t('Memory')}
						<span class="text-[0.625rem] uppercase text-gray-400 dark:text-gray-600"
							>{$i18n.t('Experimental')}</span
						>
					</div>
				</Tooltip>

				<Switch
					bind:state={enableMemory}
					on:change={async () => {
						saveSettings({ memory: enableMemory });
					}}
				/>
			</UserSettingRow>

			{#if enableMemory}
				<div>
					<div class="mb-2 flex items-center justify-between">
						<div class="text-xs text-gray-600 dark:text-gray-400">
							{$i18n.t('Saved Memories')}
							{#if !loadingMemories}
								<span class="ml-1 text-gray-400 dark:text-gray-600">{memories.length}</span>
							{/if}
						</div>

						<Dropdown align="end">
							<Tooltip content={$i18n.t('Actions')}>
								<button
									class="flex h-7 items-center gap-1.5 rounded-lg bg-transparent px-1.5 text-xs text-gray-500 transition-colors hover:text-gray-900 dark:text-gray-500 dark:hover:text-white"
									type="button"
								>
									<span>{$i18n.t('Actions')}</span>
									<ChevronDown className="size-3" strokeWidth="2.5" />
								</button>
							</Tooltip>

							<div slot="content">
								<DropdownMenu className="w-[170px] shadow-sm">
									<button
										class="flex h-[1.6875rem] w-full cursor-pointer select-none items-center gap-2 rounded-lg bg-transparent px-2 text-xs hover:text-gray-900 disabled:cursor-default disabled:opacity-30 dark:hover:text-gray-100"
										disabled={loadingMemories}
										type="button"
										on:click={() => {
											selectedMemory = null;
											showMemoryModal = true;
										}}
									>
										<Plus className="size-3.5 shrink-0" strokeWidth="1.5" />
										<div class="min-w-0 flex-1 truncate text-left">{$i18n.t('Add Memory')}</div>
									</button>

									<button
										class="flex h-[1.6875rem] w-full cursor-pointer select-none items-center gap-2 rounded-lg bg-transparent px-2 text-xs hover:text-gray-900 disabled:cursor-default disabled:opacity-30 dark:hover:text-gray-100"
										disabled={loadingMemories || memories.length === 0}
										type="button"
										on:click={() => {
											showClearConfirmDialog = true;
										}}
									>
										<Trash className="size-3.5 shrink-0" strokeWidth="1.5" />
										<div class="min-w-0 flex-1 truncate text-left">{$i18n.t('Clear memory')}</div>
									</button>
								</DropdownMenu>
							</div>
						</Dropdown>
					</div>

					{#if loadingMemories}
						<div class="flex min-h-16 w-full items-center justify-center">
							<Spinner className="size-4" />
						</div>
					{:else}
						{#if memories.length > 0}
							<div class="mb-2 flex items-center gap-2">
								<input
									class={inputClass}
									bind:value={query}
									placeholder={$i18n.t('Search Memories')}
									maxlength="500"
								/>

								{#if query}
									<button
										type="button"
										class={actionButtonClass}
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
							<div class="min-h-16 text-[0.6875rem] text-gray-400 dark:text-gray-600">
								{#if memories.length === 0}
									{$i18n.t('Memories accessible by LLMs will be shown here.')}
								{:else}
									{$i18n.t('No results found')}
								{/if}
							</div>
						{:else}
							<div class="flex flex-col gap-2">
								{#each sortedMemories as memory (memory.id)}
									<div class="flex items-start justify-between gap-3">
										<div
											class="min-w-0 whitespace-pre-wrap break-words text-xs text-gray-700 dark:text-gray-300"
										>
											{memory.content}
										</div>
										<div class="flex shrink-0 items-center justify-end gap-2">
											<button
												type="button"
												class="{actionButtonClass} hover:underline"
												on:click={() => editMemory(memory)}
											>
												{$i18n.t('Edit')}
											</button>
											<button
												type="button"
												class="{actionButtonClass} hover:underline"
												on:click={() => confirmDeleteMemory(memory)}
											>
												{$i18n.t('Remove')}
											</button>
										</div>
									</div>
								{/each}
							</div>
						{/if}
					{/if}
				</div>
			{/if}
		</UserSettingSection>
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
			class="mt-2 max-h-32 overflow-y-auto whitespace-pre-wrap break-words rounded-lg border border-gray-100/50 bg-gray-50/40 p-2 text-xs text-gray-600 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-400"
		>
			{selectedMemory?.content}
		</div>
	</div>
</ConfirmDialog>

<MemoryModal
	bind:show={showMemoryModal}
	memory={selectedMemory as any}
	on:save={async () => {
		await loadMemories();
	}}
/>
