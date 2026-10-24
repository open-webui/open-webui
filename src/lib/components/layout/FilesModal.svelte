<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount, onDestroy } from 'svelte';
	import type { Writable } from 'svelte/store';
	import dayjs from 'dayjs';

	import {
		searchUserFiles,
		deleteFileById,
		getUserFileCount,
		getFileById,
		getFileBlobById
	} from '$lib/apis/files';
	import { formatFileSize } from '$lib/utils';
	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Loader from '$lib/components/common/Loader.svelte';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import FileItemModal from '$lib/components/common/FileItemModal.svelte';
	import FileTypeIcon from '$lib/components/chat/FileNav/FileTypeIcon.svelte';
	import Icon from '$lib/components/chat/FileNav/Icon.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import ArrowDownTray from '$lib/components/icons/ArrowDownTray.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n: Writable<any> = getContext('i18n');
	const PAGE_SIZE = 50;
	export let show = false;

	let files: any[] | null = null;
	let fileCount: number | null = null;
	let query = '';
	let orderBy = 'created_at';
	let direction = 'desc';
	let page = 0;
	let allFilesLoaded = false;
	let filesLoading = false;
	let loadError = false;
	let searchTimer: ReturnType<typeof setTimeout>;
	let generation = 0;

	let selectedIds = new Set<string>();
	let selectionStatus: 'idle' | 'loading' | 'all' | 'error' = 'idle';
	let deleteIds: string[] = [];
	let showDeleteConfirmDialog = false;
	let operation: 'delete' | 'download' | null = null;
	let progress = { done: 0, total: 0, failed: 0 };
	let stopRequested = false;
	let selectedFile: any = null;
	let showFileItemModal = false;
	let shiftKey = false;

	$: busy = selectionStatus === 'loading' || !!operation || showDeleteConfirmDialog;
	$: loadedSelected = (files ?? []).filter((file) => selectedIds.has(file.id)).length;
	$: allLoadedSelected = !!files?.length && loadedSelected === files.length;
	$: shownFileCount = query ? (files?.length ?? null) : fileCount;
	$: sortedFiles = [...(files ?? [])].sort((a, b) => {
		const result =
			orderBy === 'filename'
				? (a.filename ?? '').localeCompare(b.filename ?? '')
				: (a.created_at ?? 0) - (b.created_at ?? 0);
		return direction === 'asc' ? result : -result;
	});

	const loadFiles = async (more = false) => {
		if (!show || (more && (busy || filesLoading || allFilesLoaded || loadError))) return;
		const request = generation;
		const nextPage = more ? page + 1 : 0;
		filesLoading = true;
		loadError = false;
		try {
			const result = await searchUserFiles(
				localStorage.token,
				query ? `*${query}*` : '*',
				nextPage * PAGE_SIZE,
				PAGE_SIZE
			);
			if (request !== generation) return;
			files = more ? [...(files ?? []), ...result] : result;
			page = nextPage;
			allFilesLoaded = result.length < PAGE_SIZE;
			if (!more && !query) {
				const count = await getUserFileCount(localStorage.token);
				if (request === generation) fileCount = count;
			}
		} catch {
			if (request !== generation) return;
			files ??= [];
			loadError = true;
		} finally {
			if (request === generation) filesLoading = false;
		}
	};

	const resetSearch = (visible: boolean, _query: string) => {
		++generation;
		selectedIds = new Set();
		selectionStatus = 'idle';
		files = null;
		fileCount = null;
		filesLoading = false;
		clearTimeout(searchTimer);
		if (visible) searchTimer = setTimeout(() => loadFiles(), 300);
	};
	$: resetSearch(show, query);

	const toggleSelection = (ids: string[], selected: boolean) => {
		if (busy) return;
		for (const id of ids) {
			if (selected) selectedIds.add(id);
			else selectedIds.delete(id);
		}
		selectedIds = new Set(selectedIds);
		selectionStatus = 'idle';
	};

	const selectAllMatching = async () => {
		if (busy) return;
		const request = generation;
		const pattern = query ? `*${query}*` : '*';
		const ids = new Set<string>();
		selectionStatus = 'loading';
		try {
			for (let skip = 0; ; skip += PAGE_SIZE) {
				const result = await searchUserFiles(localStorage.token, pattern, skip, PAGE_SIZE);
				if (request !== generation) return;
				for (const file of result) ids.add(file.id);
				if (result.length < PAGE_SIZE) break;
			}
			selectedIds = ids;
			selectionStatus = 'all';
		} catch {
			if (request === generation) selectionStatus = 'error';
		}
	};

	const requestDelete = (ids: string[]) => {
		if (busy || !ids.length) return;
		deleteIds = ids;
		showDeleteConfirmDialog = true;
	};

	const deleteHandler = async () => {
		if (operation || !deleteIds.length) return;
		operation = 'delete';
		stopRequested = false;
		progress = { done: 0, total: deleteIds.length, failed: 0 };
		++generation;
		clearTimeout(searchTimer);
		for (let offset = 0; offset < deleteIds.length && !stopRequested; offset += 3) {
			await Promise.all(
				deleteIds.slice(offset, offset + 3).map(async (id) => {
					try {
						await deleteFileById(localStorage.token, id);
						// toast.success($i18n.t('File deleted successfully.'));
						selectedIds.delete(id);
						files = files?.filter((file) => file.id !== id) ?? null;
					} catch {
						progress.failed++;
						selectedIds.add(id);
					} finally {
						progress.done++;
						selectedIds = new Set(selectedIds);
					}
				})
			);
		}
		const message = $i18n.t(
			'{{deleted}} deleted, {{failed}} failed, {{remaining}} not processed.',
			{
				deleted: progress.done - progress.failed,
				failed: progress.failed,
				remaining: progress.total - progress.done
			}
		);
		if (progress.failed) toast.error(message);
		else toast.success(message);
		selectionStatus = 'idle';
		await loadFiles();
		operation = null;
	};

	const downloadHandler = async (ids: string[]) => {
		if (busy || !ids.length) return;
		operation = 'download';
		stopRequested = false;
		progress = { done: 0, total: ids.length, failed: 0 };
		try {
			// One archive avoids browser prompts for hundreds of separate downloads.
			const zip = ids.length > 1 ? new (await import('jszip')).default() : null;
			let output: Blob | undefined;
			let filename = '';
			for (const id of ids) {
				if (stopRequested) return;
				const file =
					files?.find((file) => file.id === id) ?? (await getFileById(localStorage.token, id));
				if (!file) throw new Error($i18n.t('Could not load files.'));
				const blob = await getFileBlobById(localStorage.token, id, { attachment: true });
				filename = (file.filename || 'file').replace(/[\\/]/g, '_');
				if (filename === '.' || filename === '..') filename = 'file';
				if (zip) {
					let name = filename;
					let suffix = 1;
					while (zip.file(name)) name = `${suffix++}-${filename}`;
					zip.file(name, await blob.arrayBuffer());
				} else output = blob;
				progress.done++;
			}
			if (stopRequested) return;
			if (zip) output = await zip.generateAsync({ type: 'blob' });
			if (stopRequested || !output) return;
			const url = URL.createObjectURL(output);
			const link = document.createElement('a');
			link.href = url;
			link.download = zip ? 'files.zip' : filename;
			link.click();
			setTimeout(() => URL.revokeObjectURL(url), 1000);
		} catch (error) {
			toast.error(error instanceof Error ? error.message : String(error));
		} finally {
			operation = null;
		}
	};

	onMount(() => {
		const onKeyDown = (event: KeyboardEvent) => {
			if (event.key === 'Shift') {
				shiftKey = true;
			}
		};

		const onKeyUp = (event: KeyboardEvent) => {
			if (event.key === 'Shift') {
				shiftKey = false;
			}
		};

		const onBlur = () => {
			shiftKey = false;
		};

		window.addEventListener('keydown', onKeyDown);
		window.addEventListener('keyup', onKeyUp);
		window.addEventListener('blur', onBlur);

		return () => {
			window.removeEventListener('keydown', onKeyDown);
			window.removeEventListener('keyup', onKeyUp);
			window.removeEventListener('blur', onBlur);
		};
	});

	onDestroy(() => {
		show = false;
		stopRequested = true;
		++generation;
		clearTimeout(searchTimer);
	});
</script>

<ConfirmDialog
	bind:show={showDeleteConfirmDialog}
	title={$i18n.t('Delete {{count}} files?', { count: deleteIds.length })}
	message={$i18n.t('This cannot be undone. References to these files may stop working.')}
	confirmLabel={$i18n.t('Delete')}
	on:confirm={deleteHandler}
/>
<FileItemModal bind:show={showFileItemModal} item={selectedFile} edit={false} />

<Modal
	size="lg"
	bind:show
	onRequestClose={() => {
		if (!operation) show = false;
	}}
	ariaLabel={$i18n.t('Files')}
>
	<div class="px-4 pb-3 pt-3 text-gray-700 dark:text-gray-200">
		<div class="mb-2 flex h-6 items-center gap-2">
			<div class="flex flex-1 items-center gap-1.5 text-sm font-medium">
				{$i18n.t('Files')}
				{#if shownFileCount !== null}<span class="text-xs font-normal tabular-nums text-gray-400"
						>{shownFileCount}</span
					>{/if}
			</div>
			<Dropdown closeOnSelect align="end">
				<button
					type="button"
					aria-label={$i18n.t('Selection actions')}
					disabled={busy || !selectedIds.size}
					class="flex h-6 items-center gap-1 rounded-lg px-1.5 text-xs text-gray-500 transition hover:text-gray-900 disabled:opacity-40 dark:text-gray-400 dark:hover:text-gray-100"
				>
					{$i18n.t('Actions')}<Icon name="chevron-down" size={11} />
				</button>
				<div slot="content">
					<DropdownMenu className="min-w-36" style="border: 0">
						<button
							type="button"
							disabled={busy || !selectedIds.size}
							on:click={() => downloadHandler([...selectedIds])}
							><ArrowDownTray className="size-3.5" />{$i18n.t('Download')}</button
						>
						<button
							type="button"
							disabled={busy || !selectedIds.size}
							on:click={() => requestDelete([...selectedIds])}
							><GarbageBin className="size-3.5" />{$i18n.t('Delete')}</button
						>
					</DropdownMenu>
				</div>
			</Dropdown>
			<button
				type="button"
				aria-label={$i18n.t('Close')}
				disabled={!!operation}
				class="flex size-6 items-center justify-center rounded-lg text-gray-400 transition hover:text-gray-700 disabled:opacity-40 dark:hover:text-gray-200"
				on:click={() => {
					show = false;
				}}><XMark className="size-3.5" /></button
			>
		</div>

		<div class="mb-1 flex h-7 items-center gap-2 px-1 pb-1">
			{#if operation}
				<Spinner className="size-3" />
				<span class="min-w-0 flex-1 truncate text-xs text-gray-500 dark:text-gray-400" role="status"
					>{$i18n.t(
						operation === 'download'
							? 'Preparing {{processed}} of {{total}}'
							: 'Processed {{processed}} of {{total}}',
						{ processed: progress.done, total: progress.total }
					)}</span
				>
				<button
					type="button"
					class="text-xs text-gray-500 hover:text-gray-900 disabled:opacity-40 dark:hover:text-gray-100"
					disabled={stopRequested}
					on:click={() => {
						stopRequested = true;
					}}>{stopRequested ? $i18n.t('Stopping...') : $i18n.t('Stop')}</button
				>
			{:else}
				<Icon name="search" size={13} class="shrink-0 text-gray-400" />
				<input
					class="min-w-0 flex-1 bg-transparent py-1 text-xs outline-hidden placeholder:text-gray-400"
					bind:value={query}
					disabled={showDeleteConfirmDialog}
					placeholder={$i18n.t('Search Files')}
					aria-label={$i18n.t('Search Files')}
					maxlength="500"
				/>
				{#if query}<button
						type="button"
						aria-label={$i18n.t('Clear search')}
						disabled={showDeleteConfirmDialog}
						class="flex size-5 shrink-0 items-center justify-center text-gray-400 hover:text-gray-600"
						on:click={() => {
							query = '';
						}}><XMark className="size-3" /></button
					>{/if}
				{#if selectedIds.size}
					<span
						role="status"
						class="shrink-0 text-[0.6875rem] tabular-nums text-gray-500 dark:text-gray-400"
						>{$i18n.t('{{count}} selected', { count: selectedIds.size })}</span
					>
					<button
						type="button"
						aria-label={$i18n.t('Clear selection')}
						title={$i18n.t('Clear selection')}
						disabled={busy}
						class="flex size-5 shrink-0 items-center justify-center text-gray-400 hover:text-gray-600 disabled:opacity-40 dark:hover:text-gray-200"
						on:click={() => {
							selectedIds = new Set();
							selectionStatus = 'idle';
						}}><XMark className="size-3" /></button
					>
				{/if}
			{/if}
		</div>

		{#if selectionStatus === 'loading'}
			<div class="flex h-6 items-center gap-1.5 px-1 text-[0.6875rem] text-gray-500" role="status">
				<Spinner className="size-3" /><span>{$i18n.t('Selecting all matching files...')}</span>
			</div>
		{:else if selectionStatus === 'error'}
			<div class="flex items-center gap-2 px-1 py-1 text-[0.6875rem] text-gray-500" role="alert">
				<span
					>{$i18n.t('Could not select all matching files. Your selection has not changed.')}</span
				><button disabled={busy} class="shrink-0 underline" on:click={selectAllMatching}
					>{$i18n.t('Retry')}</button
				>
			</div>
		{:else if allLoadedSelected && !allFilesLoaded && selectionStatus !== 'all' && !operation}
			<button
				class="h-6 px-1 text-[0.6875rem] text-gray-500 transition hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
				disabled={busy}
				on:click={selectAllMatching}>{$i18n.t('Select all matching files')}</button
			>
		{/if}

		{#if files !== null}
			{#if files.length}
				<div
					class="grid h-7 grid-cols-[1.75rem_minmax(0,1fr)_3.5rem_1.75rem] items-center gap-x-2 text-[0.6875rem] text-gray-400 sm:grid-cols-[1.75rem_minmax(0,1fr)_4rem_7rem_1.75rem]"
				>
					<div class="flex justify-center">
						<Checkbox
							state={allLoadedSelected ? 'checked' : 'unchecked'}
							indeterminate={loadedSelected > 0 && !allLoadedSelected}
							disabled={busy}
							ariaLabel={$i18n.t('Select loaded files')}
							on:change={() =>
								toggleSelection(
									(files ?? []).map((file) => file.id),
									!allLoadedSelected
								)}
						/>
					</div>
					<button
						disabled={busy}
						class="flex items-center gap-1 text-left hover:text-gray-700 dark:hover:text-gray-200"
						on:click={() => {
							direction = orderBy === 'filename' && direction === 'asc' ? 'desc' : 'asc';
							orderBy = 'filename';
						}}
					>
						{$i18n.t('Filename')}{#if orderBy === 'filename'}<Icon
								name={direction === 'asc' ? 'chevron-up' : 'chevron-down'}
								size={10}
							/>{/if}
					</button>
					<span class="text-right">{$i18n.t('Size')}</span>
					<button
						disabled={busy}
						class="hidden items-center justify-end gap-1 hover:text-gray-700 dark:hover:text-gray-200 sm:flex"
						on:click={() => {
							direction = orderBy === 'created_at' && direction === 'asc' ? 'desc' : 'asc';
							orderBy = 'created_at';
						}}
					>
						{$i18n.t('Created at')}{#if orderBy === 'created_at'}<Icon
								name={direction === 'asc' ? 'chevron-up' : 'chevron-down'}
								size={10}
							/>{/if}
					</button>
				</div>
			{/if}
			<div class="max-h-[min(28rem,calc(100dvh-12rem))] overflow-y-auto">
				{#if !files.length && !loadError}<div
						class="flex min-h-20 items-center justify-center text-xs text-gray-400"
					>
						{$i18n.t('No files found')}
					</div>{/if}
				{#each sortedFiles as file (file.id)}
					<div
						class="group grid h-7 grid-cols-[1.75rem_minmax(0,1fr)_3.5rem_1.75rem] items-center gap-x-2 rounded-xl text-xs transition-colors hover:bg-gray-50/40 dark:hover:bg-white/4 sm:grid-cols-[1.75rem_minmax(0,1fr)_4rem_7rem_1.75rem]"
					>
						<div class="flex justify-center">
							<Checkbox
								state={selectedIds.has(file.id) ? 'checked' : 'unchecked'}
								disabled={busy}
								ariaLabel={$i18n.t('Select {{filename}}', { filename: file.filename })}
								on:change={() => toggleSelection([file.id], !selectedIds.has(file.id))}
							/>
						</div>
						<button
							class="flex h-full min-w-0 items-center gap-1.5 text-left"
							title={file.filename}
							disabled={!!operation}
							on:click={() => {
								selectedFile = {
									id: file.id,
									name: file.filename,
									type: 'file',
									size: file.meta?.size,
									meta: file.meta
								};
								showFileItemModal = true;
							}}
						>
							<FileTypeIcon name={file.filename} size={14} /><span class="truncate"
								>{file.filename}</span
							>
						</button>
						<span class="truncate text-right text-[0.6875rem] tabular-nums text-gray-400"
							>{formatFileSize(file.meta?.size ?? 0)}</span
						>
						<span
							class="hidden text-right text-[0.6875rem] tabular-nums text-gray-400 sm:block"
							title={dayjs(file.created_at * 1000)
								.locale($i18n.language)
								.format('MMM D, YYYY h:mm A')}
							>{dayjs(file.created_at * 1000)
								.locale($i18n.language)
								.format('MMM D, YYYY')}</span
						>
						<Dropdown closeOnSelect align="end">
							<button
								type="button"
								aria-label={$i18n.t('Actions for {{filename}}', { filename: file.filename })}
								disabled={busy}
								class="flex size-6 items-center justify-center rounded-lg text-gray-400 transition hover:text-gray-700 disabled:opacity-40 dark:hover:text-gray-200"
								><Icon name="three-dots" size={14} /></button
							>
							<div slot="content">
								<DropdownMenu className="min-w-36" style="border: 0">
									<button type="button" disabled={busy} on:click={() => downloadHandler([file.id])}
										><ArrowDownTray className="size-3.5" />{$i18n.t('Download')}</button
									>
									<!-- {$i18n.t('Delete File')} -->
									<button
										type="button"
										disabled={busy}
										class={shiftKey ? 'text-red-500' : ''}
										on:click={(event) => {
											if (event.shiftKey) {
												deleteIds = [file.id];
												deleteHandler();
											} else {
												requestDelete([file.id]);
											}
										}}><GarbageBin className="size-3.5" />{$i18n.t('Delete')}</button
									>
								</DropdownMenu>
							</div>
						</Dropdown>
					</div>
				{/each}
				{#if loadError}
					<div role="alert" class="py-2 text-center text-xs text-gray-500">
						{$i18n.t('Could not load files.')}
						<button disabled={busy} class="underline" on:click={() => loadFiles()}
							>{$i18n.t('Retry')}</button
						>
					</div>
				{:else if !allFilesLoaded && !busy}
					<Loader on:visible={() => loadFiles(true)}
						><div class="flex justify-center py-2"><Spinner className="size-3" /></div></Loader
					>
				{/if}
			</div>
		{:else}
			<div class="flex min-h-20 items-center justify-center"><Spinner className="size-4" /></div>
		{/if}
	</div>
</Modal>
