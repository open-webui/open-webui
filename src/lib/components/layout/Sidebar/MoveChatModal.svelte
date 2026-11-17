<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { createNewFolder, getFolders, type Folder } from '$lib/apis/folders';
	import { updateChatFolderIdById } from '$lib/apis/chats';
	import { getRequestToken } from '$lib/services/auth';
	import { getI18n } from '$lib/utils/context';
	import Modal from '$lib/components/common/Modal.svelte';

	const i18n = getI18n();
	const dispatch = createEventDispatcher();

	export let show = false;
	export let chatId = '';
	export let returnFocusSelector = '';

	let folders: Folder[] = [];
	let destination = '';
	let newFolderName = '';
	let createFolder = false;
	let loading = true;
	let saving = false;
	let nameInvalid = false;
	let nameInput: HTMLInputElement | undefined;

	const getSortedFolders = (folders: Folder[]) => {
		const byId = new Map(folders.map((folder) => [folder.id, folder]));
		return folders
			.map((folder) => {
				const names = [folder.name];
				const visited = new Set([folder.id]);
				let parent = folder.parent_id ? byId.get(folder.parent_id) : undefined;
				while (parent && !visited.has(parent.id)) {
					visited.add(parent.id);
					names.unshift(parent.name);
					parent = parent.parent_id ? byId.get(parent.parent_id) : undefined;
				}
				return { id: folder.id, path: names.join(' / ') };
			})
			.sort((a, b) => a.path.localeCompare(b.path));
	};

	$: sortedFolders = getSortedFolders(folders);
	$: nameError = nameInvalid ? $i18n.t('Folder name cannot be empty.') : '';

	const loadFolders = async () => {
		loading = true;
		try {
			folders = await getFolders(getRequestToken());
		} catch (error) {
			console.error('Failed to load folders:', error);
			toast.error($i18n.t('Failed to load folders'));
			show = false;
		} finally {
			loading = false;
		}
	};

	$: if (show) {
		destination = '';
		newFolderName = '';
		createFolder = false;
		nameInvalid = false;
		loadFolders();
	}

	const moveChat = async () => {
		if (saving || loading) return;
		if (createFolder && !newFolderName.trim()) {
			nameInvalid = true;
			nameInput?.focus();
			return;
		}
		saving = true;
		try {
			if (createFolder) {
				const folder: Folder = await createNewFolder(getRequestToken(), newFolderName.trim());
				folders = [...folders, folder];
				destination = folder.id;
				createFolder = false;
			}
			await updateChatFolderIdById(getRequestToken(), chatId, destination || undefined);
			toast.success($i18n.t('Chat moved successfully'));
			show = false;
			let folder = folders.find((item) => item.id === destination);
			const visited = new Set<string>();
			while (folder?.parent_id && !visited.has(folder.id)) {
				visited.add(folder.id);
				const parent = folders.find((item) => item.id === folder?.parent_id);
				if (!parent) break;
				folder = parent;
			}
			dispatch('change', {
				focusId: folder ? `folder-${folder.id}-button` : `chat-menu-${chatId}`
			});
		} catch (error) {
			console.error('Failed to move chat:', error);
			toast.error($i18n.t('Failed to move chat'));
		} finally {
			saving = false;
		}
	};
</script>

<Modal
	bind:show
	size="sm"
	title={$i18n.t('Move to folder')}
	labelledBy={`move-chat-title-${chatId}`}
	{returnFocusSelector}
>
	<form class="p-5 space-y-4" on:submit|preventDefault={moveChat}>
		<h2 id={`move-chat-title-${chatId}`} class="text-lg font-semibold">
			{$i18n.t('Move to folder')}
		</h2>
		<label class="block">
			<span>{$i18n.t('Destination folder')}</span>
			<select
				class="w-full rounded-lg p-2 dark:bg-gray-800"
				bind:value={destination}
				aria-busy={loading}
				disabled={saving || createFolder}
			>
				<option value="">{$i18n.t('No folder')}</option>
				{#each sortedFolders as folder (folder.id)}
					<option value={folder.id}>{folder.path}</option>
				{/each}
			</select>
		</label>
		<label class="flex items-center gap-2">
			<input type="checkbox" bind:checked={createFolder} disabled={loading || saving} />
			{$i18n.t('Create new folder')}
		</label>
		{#if createFolder}
			<label class="block">
				<span>{$i18n.t('Folder name')}</span>
				<input
					class="w-full rounded-lg p-2 dark:bg-gray-800"
					bind:value={newFolderName}
					bind:this={nameInput}
					required
					aria-invalid={!!nameError}
					aria-describedby={nameError ? `folder-name-error-${chatId}` : undefined}
					on:invalid={() => (nameInvalid = true)}
					on:input={() => {
						if (newFolderName.trim()) nameInvalid = false;
					}}
					disabled={saving}
				/>
			</label>
			{#if nameError}
				<p id={`folder-name-error-${chatId}`} class="text-red-600 text-sm" role="alert">
					{nameError}
				</p>
			{/if}
		{/if}
		<div class="flex justify-end gap-3">
			<button type="button" class="rounded-lg px-3 py-2" on:click={() => (show = false)}
				>{$i18n.t('Cancel')}</button
			>
			<button
				type="submit"
				class="rounded-lg px-3 py-2 bg-gray-200 dark:bg-gray-700"
				disabled={loading || saving}>{$i18n.t('Move')}</button
			>
		</div>
	</form>
</Modal>
