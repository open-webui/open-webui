<script lang="ts">
	import { getContext, onDestroy, onMount, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { formatFileSize } from '$lib/utils';
	import {
		getCwd,
		listFiles,
		uploadToTerminal,
		joinTerminalPath,
		type FileEntry,
		type TerminalConnection
	} from '$lib/apis/terminal';
	import FileCodeEditor from '../FileNav/FileCodeEditor.svelte';
	import Icon from '../FileNav/Icon.svelte';
	import FileTypeIcon from '../FileNav/FileTypeIcon.svelte';
	import Modal from '../../common/Modal.svelte';
	import ConfirmDialog from '../../common/ConfirmDialog.svelte';

	const i18n = getContext<any>('i18n');
	export let label: string;
	export let connection: TerminalConnection;
	export let chatId: string | null = null;
	export let initialDirectory: string | undefined = undefined;
	export let dirty = false;
	export let onSaved: (path: string) => void;
	export let isOpen: (path: string) => boolean;
	export let initialView: any = null;
	let value = initialView?.value ?? '';
	export const captureView = () => ({
		value,
		fileName,
		directory,
		editor: editor?.captureView(),
		dirty: dirty || saving
	});
	let editor: FileCodeEditor;
	let saving = false;
	let showSave = false;
	let fileName = initialView?.fileName ?? label;
	let directory = initialView?.directory ?? initialDirectory ?? '/';
	let root = '/';
	let entries: FileEntry[] = [];
	let loading = false;
	let writable = false;
	let showHidden = false;
	let error = '';
	let replacePath = '';
	let disposed = false;
	let fileNameInput: HTMLInputElement;
	let saveResult: ((saved: boolean) => void) | null = null;
	let closeChoice: ((confirmed: boolean) => void) | null = null;
	$: dirty = value.length > 0;
	$: byteCount = new TextEncoder().encode(value).length;
	$: fullPath = joinTerminalPath(directory, fileName.trim());
	$: if (fullPath !== replacePath) replacePath = '';

	const browse = async (path: string) => {
		loading = true;
		error = '';
		const listing = await listFiles(connection.baseUrl, connection.key, path, chatId ?? undefined);
		if (disposed) return;
		loading = false;
		writable = listing?.writable !== false && !!listing;
		if (!listing) {
			error = $i18n.t('Failed to load directory');
			return;
		}
		directory = path;
		entries = listing.entries;
	};
	const finishSave = (saved: boolean) => {
		showSave = false;
		saveResult?.(saved);
		saveResult = null;
	};
	const save = async () => {
		if (saving || showSave) return false;
		const result = new Promise<boolean>((resolve) => {
			saveResult = resolve;
		});
		showSave = true;
		loading = true;
		fileName = label;
		replacePath = '';
		const cwd = await getCwd(connection.baseUrl, connection.key, chatId ?? undefined);
		if (disposed || !showSave) return false;
		root = (cwd?.root?.path ?? '/').replace(/\/$/, '') || '/';
		await browse(initialDirectory ?? cwd?.cwd ?? cwd?.home ?? root);
		await tick();
		fileNameInput?.focus();
		fileNameInput?.select();
		return result;
	};
	const write = async () => {
		if (saving || loading || !writable) return;
		const name = fileName.trim();
		if (!name || name === '.' || name === '..' || /[\\/\0]/.test(name)) {
			error = $i18n.t('Enter a file name without slashes.');
			return;
		}
		if (isOpen(fullPath)) {
			error = $i18n.t('This file is already open. Close its tab or choose another name.');
			return;
		}
		saving = true;
		error = '';
		try {
			const listing = await listFiles(
				connection.baseUrl,
				connection.key,
				directory,
				chatId ?? undefined
			);
			if (!listing || listing.writable === false) throw new Error($i18n.t('File is not writable.'));
			const existing = listing.entries.find((entry) => entry.name === name);
			if (existing?.type === 'directory' || existing?.writable === false)
				throw new Error($i18n.t('File is not writable.'));
			if (existing && replacePath !== fullPath) {
				replacePath = fullPath;
				error = $i18n.t('A file with this name already exists. Replace it?');
				return;
			}
			const result = await uploadToTerminal(
				connection.baseUrl,
				connection.key,
				directory,
				new File([value], name, { type: 'text/plain' }),
				chatId ?? undefined
			);
			if (!result)
				throw new Error($i18n.t('Failed to save file. Your changes are still in the editor.'));
			dirty = false;
			finishSave(true);
			onSaved(result.path || fullPath);
		} catch (reason) {
			error = reason instanceof Error ? reason.message : String(reason);
		} finally {
			saving = false;
		}
	};
	export const hasUnsavedChanges = () => dirty || saving;
	export const requestClose = async () => {
		if (saving || showSave || closeChoice) return false;
		if (!dirty) return true;
		const confirmed = await new Promise<boolean>((resolve) => {
			closeChoice = resolve;
		});
		closeChoice = null;
		await tick();
		return confirmed;
	};
	onMount(() => {
		editor?.restoreView(initialView?.editor);
		editor?.focus();
	});
	onDestroy(() => {
		disposed = true;
		saveResult?.(false);
		closeChoice?.(false);
	});
</script>

<div class="flex h-full min-h-0 flex-col">
	<div class="m-0 flex shrink-0 items-center gap-1 px-2 pt-0 pb-1.5">
		<span class="min-w-0 flex-1 truncate text-xs text-gray-700 dark:text-gray-300" title={label}
			>{label}</span
		>
		<span class="shrink-0 text-[0.6875rem] text-gray-400">{formatFileSize(byteCount)}</span>
		<button
			class="flex size-5 shrink-0 items-center justify-center rounded text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300"
			aria-label={$i18n.t('Save')}
			title={$i18n.t('Save')}
			on:click={() => void save().catch((e) => toast.error(String(e)))}
			><Icon name="save" size={11} strokeWidth={1.4} /></button
		>
	</div>
	<div class="relative flex-1 min-h-0">
		<FileCodeEditor
			bind:this={editor}
			bind:value
			ariaLabel={$i18n.t('File content')}
			onSave={async () => {
				await save();
			}}
		/>
	</div>
</div>

<Modal
	show={showSave}
	size="sm"
	ariaLabel={$i18n.t('Save As')}
	onRequestClose={() => {
		if (!saving) finishSave(false);
	}}
	className="bg-white dark:bg-gray-900 rounded-2xl"
>
	<form class="flex max-h-[26rem] flex-col p-3 text-sm" on:submit|preventDefault={write}>
		<label class="flex items-center gap-2 pb-3">
			<FileTypeIcon name={fileName} />
			<input
				bind:this={fileNameInput}
				bind:value={fileName}
				disabled={saving}
				aria-label={$i18n.t('File name')}
				class="min-w-0 flex-1 bg-transparent outline-none"
			/>
		</label>
		<div class="flex h-8 items-center gap-2 text-xs text-gray-500">
			<button
				type="button"
				class="size-6 shrink-0"
				disabled={loading || saving || directory.replace(/\/$/, '') === root.replace(/\/$/, '')}
				aria-label={$i18n.t('Parent directory')}
				on:click={() =>
					browse(directory.replace(/\/$/, '').split('/').slice(0, -1).join('/') || '/')}
				><Icon name="chevron-left" size={14} /></button
			>
			<span class="min-w-0 flex-1 truncate" title={directory}>{directory}</span>
			<label class="flex items-center gap-1"
				><input type="checkbox" bind:checked={showHidden} />{$i18n.t('Hidden')}</label
			>
		</div>
		<div class="min-h-24 overflow-y-auto py-1" class:flex={loading} class:flex-col={loading}>
			{#if loading}<p
					class="flex flex-1 items-center justify-center p-3 text-center text-xs text-gray-400"
				>
					{$i18n.t('Loading...')}
				</p>
			{:else}{#each entries.filter((entry) => entry.type === 'directory' && (showHidden || !entry.name.startsWith('.'))) as entry}
					<button
						type="button"
						disabled={saving}
						class="flex h-7 w-full items-center gap-2 rounded-lg px-2 text-left text-xs hover:bg-gray-100/40 dark:hover:bg-gray-800/25"
						on:click={() => browse(joinTerminalPath(directory, entry.name))}
						><FileTypeIcon name={entry.name} type="directory" /><span class="truncate"
							>{entry.name}</span
						></button
					>
				{/each}{/if}
		</div>
		{#if error}<p role="alert" class="py-2 text-xs text-gray-500 dark:text-gray-400">
				{error}
			</p>{/if}
		<div class="flex items-center gap-2 pt-2">
			<span class="min-w-0 flex-1 truncate text-xs text-gray-400" title={fullPath}>{fullPath}</span>
			<button
				type="button"
				disabled={saving}
				class="rounded-lg px-2 py-1 text-xs"
				on:click={() => finishSave(false)}>{$i18n.t('Cancel')}</button
			>
			<button
				type="submit"
				disabled={saving || loading || !writable || !fileName.trim()}
				class="rounded-lg bg-gray-100 px-3 py-1 text-xs disabled:opacity-40 dark:bg-gray-800"
				>{$i18n.t(replacePath ? 'Replace' : 'Save')}</button
			>
		</div>
	</form>
</Modal>

<ConfirmDialog
	show={closeChoice !== null}
	confirmFirst
	primaryAction="cancel"
	title={$i18n.t('Unsaved changes')}
	message={$i18n.t('Discard unsaved changes and close this file?')}
	on:confirm={() => closeChoice?.(true)}
	on:cancel={() => closeChoice?.(false)}
/>
