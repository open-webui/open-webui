<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as I18n } from 'i18next';
	import { toast } from 'svelte-sonner';

	import { config, settings } from '$lib/stores';
	import { deleteMemoryById, getMemories } from '$lib/apis/memories';
	import { updateFolderById } from '$lib/apis/folders';
	import SettingsSelect from '$lib/components/common/SettingsSelect.svelte';
	import UserSettingRow from '$lib/components/chat/Settings/UserSettingRow.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import MemoryModal from '$lib/components/chat/Settings/Personalization/MemoryModal.svelte';
	import MemoryList from '$lib/components/chat/Settings/Personalization/MemoryList.svelte';
	import UserSettingSection from '$lib/components/chat/Settings/UserSettingSection.svelte';

	const i18n = getContext<Writable<I18n>>('i18n');

	export let folder: {
		id: string;
		data?: { memory?: string | null; [key: string]: unknown } | null;
	};

	let memoryMode = folder.data?.memory ?? '';

	const saveMemoryMode = async () => {
		const updated = await updateFolderById(localStorage.token, folder.id, {
			data: { memory: memoryMode || null }
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (updated) folder.data = { ...folder.data, memory: memoryMode || null };
	};

	type Memory = {
		id: string;
		content: string;
		path?: string | null;
		folder_id?: string | null;
		updated_at?: number;
	};

	let memories: Memory[] = [];
	let loading = true;
	let showMemoryModal = false;
	let showDeleteConfirm = false;
	let selectedMemory: Memory | null = null;

	const actionButtonClass =
		'shrink-0 text-xs text-base-500 transition-colors hover:text-base-900 dark:text-base-500 dark:hover:text-base-0';

	const loadMemories = async () => {
		loading = true;
		const all: Memory[] =
			(await getMemories(localStorage.token).catch((error) => {
				toast.error(`${error}`);
				return [];
			})) ?? [];
		memories = all
			.filter((memory) => memory.folder_id === folder.id)
			.sort((a, b) => (b.updated_at ?? 0) - (a.updated_at ?? 0));
		loading = false;
	};

	onMount(loadMemories);
</script>

<UserSettingSection first className="pt-2">
	<UserSettingRow
		label={$i18n.t('Memory')}
		description={memoryMode === 'folder'
			? $i18n.t('Chats in this folder use only this folder’s memories.')
			: $i18n.t('Chats in this folder use this folder’s memories and your account memories.')}
		let:labelId
	>
		<SettingsSelect
			id={`${labelId}-control`}
			aria-labelledby={labelId}
			bind:value={memoryMode}
			on:change={saveMemoryMode}
		>
			<option value="">{$i18n.t('Default')}</option>
			<option value="folder">{$i18n.t('Folder only')}</option>
		</SettingsSelect>
	</UserSettingRow>

	{#if !($settings?.memory ?? $config?.features?.enable_memories ?? false)}
		<p class="text-[0.6875rem] text-base-400 dark:text-base-600">
			{$i18n.t('Memory is turned off in your Personalization settings.')}
		</p>
	{/if}

	<div class="flex items-center justify-between">
		<div class="text-xs text-base-600 dark:text-base-400">
			{$i18n.t('settings.personal.personalization.savedMemories.label')}
			{#if !loading}
				<span class="ml-1 text-base-400 dark:text-base-600">{memories.length}</span>
			{/if}
		</div>
		<button
			type="button"
			class="{actionButtonClass} hover:underline"
			on:click={() => {
				selectedMemory = null;
				showMemoryModal = true;
			}}
		>
			{$i18n.t('Add Memory')}
		</button>
	</div>

	{#if loading}
		<div class="flex min-h-16 w-full items-center justify-center">
			<Spinner className="size-4" />
		</div>
	{:else if memories.length === 0}
		<div class="min-h-16 text-[0.6875rem] text-base-400 dark:text-base-600">
			{$i18n.t('No memories in this folder yet.')}
		</div>
	{:else}
		<MemoryList
			{memories}
			onEdit={(memory) => {
				selectedMemory = memory;
				showMemoryModal = true;
			}}
			onRemove={(memory) => {
				selectedMemory = memory;
				showDeleteConfirm = true;
			}}
		/>
	{/if}
</UserSettingSection>

<MemoryModal
	bind:show={showMemoryModal}
	memory={selectedMemory as any}
	folderId={folder.id}
	on:save={loadMemories}
/>

<ConfirmDialog
	title={$i18n.t('Delete Memory?')}
	show={showDeleteConfirm}
	on:confirm={async () => {
		if (!selectedMemory) return;
		const deleted = await deleteMemoryById(localStorage.token, selectedMemory.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (deleted) {
			toast.success($i18n.t('Memory deleted successfully'));
			await loadMemories();
		}
		showDeleteConfirm = false;
	}}
	on:cancel={() => {
		showDeleteConfirm = false;
	}}
>
	<div class="text-sm text-base-500 flex-1">
		{$i18n.t('Are you sure you want to delete this memory? This action cannot be undone.')}
		<div
			class="mt-2 max-h-32 overflow-y-auto whitespace-pre-wrap break-words rounded-lg border border-base-100/50 bg-base-50/40 p-2 text-xs text-base-600 dark:border-base-0/[0.04] dark:bg-base-0/[0.03] dark:text-base-400"
		>
			{selectedMemory?.content}
		</div>
	</div>
</ConfirmDialog>
