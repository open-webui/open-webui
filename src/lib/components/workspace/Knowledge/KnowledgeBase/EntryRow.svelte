<script lang="ts">
	import { getContext, tick } from 'svelte';
	import { formatFileSize } from '$lib/utils';
	import FileTypeIcon from '$lib/components/chat/FileNav/FileTypeIcon.svelte';
	import Icon from '$lib/components/chat/FileNav/Icon.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { fileName, type KnowledgeFile, type KnowledgeDirectory } from './types';
	export let item: KnowledgeFile | KnowledgeDirectory;
	export let directory = false;
	export let depth = 0;
	export let expanded = false;
	export let active = false;
	export let writeAccess = false;
	export let search = false;
	export let onOpen = () => {};
	export let onRename: (name: string) => Promise<void> = async () => {};
	export let onDelete = () => {};
	export let onAdd: (type: string) => void = () => {};
	export let onDrop: (kind: 'file' | 'directory', id: string) => void = () => {};
	export let onDownload = () => {};
	const i18n = getContext<any>('i18n');
	let renaming = false;
	let renameValue = '';
	let input: HTMLInputElement;
	let saving = false;
	let dragOver = false;
	$: file = item as KnowledgeFile;
	$: name = directory ? (item as KnowledgeDirectory).name : fileName(file);
	$: status = file.status || file.data?.status;
	$: pending = ['uploading', 'pending', 'processing'].includes(status || '');
	$: details = [
		file.directory_path,
		file.user?.name || file.user?.email,
		item.updated_at ? new Date(item.updated_at * 1000).toLocaleString() : ''
	]
		.filter(Boolean)
		.join(' · ');
	const startRename = async () => {
		renameValue = name;
		renaming = true;
		await tick();
		input?.select();
	};
	const rename = async () => {
		if (!renaming || saving) return;
		if (!renameValue.trim() || renameValue.trim() === name) {
			renaming = false;
			return;
		}
		saving = true;
		try {
			await onRename(renameValue.trim());
			renaming = false;
		} catch {
			/* Keep the name editable after the caller reports the error. */
		} finally {
			saving = false;
		}
	};
	const accepts = (event: DragEvent) =>
		writeAccess &&
		directory &&
		['application/x-kb-file-move', 'application/x-kb-dir-move'].some((type) =>
			event.dataTransfer?.types.includes(type)
		);
</script>

<div
	data-knowledge-row={item.id || file.itemId}
	class="flex h-7 min-w-0 items-center rounded-xl {active || dragOver
		? 'bg-gray-100 dark:bg-white/8'
		: ''}"
	style:padding-left={`${8 + depth * 16}px`}
	role="presentation"
	on:dragover={(event) => {
		if (accepts(event)) {
			event.preventDefault();
			event.stopPropagation();
			dragOver = true;
		}
	}}
	on:dragleave={() => (dragOver = false)}
	on:drop={(event) => {
		if (!accepts(event)) return;
		event.preventDefault();
		event.stopPropagation();
		dragOver = false;
		try {
			const raw = event.dataTransfer!.getData('application/x-kb-file-move');
			if (raw) onDrop('file', JSON.parse(raw).fileId);
			else
				onDrop(
					'directory',
					JSON.parse(event.dataTransfer!.getData('application/x-kb-dir-move')).dirId
				);
		} catch {}
	}}
>
	<button
		type="button"
		data-knowledge-entry
		class="flex h-full min-w-0 flex-1 items-center gap-1.5 pr-1 text-left text-xs"
		title={details || name}
		aria-expanded={directory ? expanded : undefined}
		on:keydown={(event) => {
			if (renaming || !directory) return;
			if ((event.key === 'ArrowRight' && !expanded) || (event.key === 'ArrowLeft' && expanded)) {
				event.preventDefault();
				onOpen();
			}
		}}
		draggable={writeAccess && !!item.id && !pending && !renaming}
		on:dragstart={(event) =>
			event.dataTransfer?.setData(
				directory ? 'application/x-kb-dir-move' : 'application/x-kb-file-move',
				JSON.stringify(directory ? { dirId: item.id } : { fileId: item.id })
			)}
		on:click={() => {
			if (!renaming && item.id && status !== 'uploading') onOpen();
		}}
	>
		{#if directory}<Icon name={expanded ? 'chevron-down' : 'chevron-right'} size={12} />{:else}<span
				class="w-3 shrink-0"
			></span>{/if}
		{#if pending}<Spinner className="size-3.5 shrink-0" />{:else}<FileTypeIcon
				{name}
				type={directory ? 'directory' : 'file'}
				size={14}
			/>{/if}
		{#if renaming}<input
				bind:this={input}
				bind:value={renameValue}
				aria-label={$i18n.t('Rename')}
				disabled={saving}
				class="h-4 min-w-0 flex-1 bg-transparent p-0 text-xs leading-4 outline-none"
				on:click|stopPropagation
				on:keydown={(event) => {
					event.stopPropagation();
					if (event.key === 'Enter') {
						event.preventDefault();
						rename();
					}
					if (event.key === 'Escape') {
						event.preventDefault();
						renaming = false;
					}
				}}
				on:blur={rename}
			/>
		{:else}<span class="min-w-0 flex-1 truncate"
				>{name}{#if search && file.directory_path}<span class="ml-1 text-gray-400"
						>{file.directory_path}</span
					>{/if}</span
			>{/if}
		{#if !directory && !renaming}<span class="shrink-0 text-[0.6875rem] text-gray-400"
				>{pending
					? $i18n.t(status === 'uploading' ? 'Uploading' : 'Processing')
					: status === 'failed'
						? $i18n.t('Failed')
						: file.meta?.size != null
							? formatFileSize(file.meta.size)
							: ''}</span
			>{/if}
	</button>
	{#if item.id && !pending}<Dropdown closeOnSelect align="end"
			><button
				type="button"
				aria-label={$i18n.t('More')}
				class="mr-1 flex size-5 shrink-0 items-center justify-center text-gray-400"
				><Icon name="three-dots" size={12} /></button
			>
			<div slot="content">
				<DropdownMenu className="min-w-36">
					{#if directory}<button type="button" on:click={onOpen}
							>{$i18n.t(expanded ? 'Collapse' : 'Expand')}</button
						>{:else}<button type="button" on:click={onDownload}>{$i18n.t('Download')}</button>{/if}
					{#if writeAccess}
						{#if directory}<hr class="border-gray-100 dark:border-gray-800" />
							<button type="button" on:click={() => onAdd('new_directory')}
								>{$i18n.t('New folder')}</button
							><button type="button" on:click={() => onAdd('files')}
								>{$i18n.t('Upload files')}</button
							><button type="button" on:click={() => onAdd('directory')}
								>{$i18n.t('Upload directory')}</button
							><button type="button" on:click={() => onAdd('text')}
								>{$i18n.t('Add text content')}</button
							><button type="button" on:click={() => onAdd('web')}>{$i18n.t('Add webpage')}</button
							>{/if}
						<hr class="border-gray-100 dark:border-gray-800" />
						<button type="button" on:click={startRename}>{$i18n.t('Rename')}</button><button
							type="button"
							on:click={onDelete}
							>{$i18n.t(directory ? 'Delete folder' : 'Remove from knowledge')}</button
						>
					{/if}
				</DropdownMenu>
			</div></Dropdown
		>{/if}
</div>
