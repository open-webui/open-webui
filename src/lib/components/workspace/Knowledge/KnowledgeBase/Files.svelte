<script lang="ts">
	import { getContext, onMount, onDestroy, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import {
		searchKnowledgeFilesById,
		getPendingKnowledgeFiles,
		createKnowledgeDirectory,
		updateKnowledgeDirectory,
		deleteKnowledgeDirectory,
		moveFileInKnowledge,
		removeFileFromKnowledgeById
	} from '$lib/apis/knowledge';
	import { renameFileById, getFileBlobById } from '$lib/apis/files';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import EntryRow from './EntryRow.svelte';
	import { fileName, type KnowledgeFile, type KnowledgeDirectory } from './types';
	export let knowledge: { id: string; write_access?: boolean; name: string };
	export let selectedFileId: string | null = null;
	export let transfers: KnowledgeFile[] = [];
	export let query = '';
	export let includeContent = false;
	export let viewOption: string | null = null;
	export let sortKey = 'updated_at';
	export let direction = 'desc';
	export let onSelect: (file: KnowledgeFile) => void = () => {};
	export let onUpload: (
		type: string,
		directoryId: string | null,
		breadcrumbs: KnowledgeDirectory[]
	) => void = () => {};
	export let onChanged: (file?: KnowledgeFile, removed?: string[]) => void = () => {};
	export let guard: (action: () => void | Promise<void>) => void = (action) => {
		action();
	};
	const i18n = getContext<any>('i18n');
	type Listing = {
		items: KnowledgeFile[];
		directories: KnowledgeDirectory[];
		breadcrumbs: KnowledgeDirectory[];
		total: number;
		page: number;
		loading: boolean;
		error: string;
	};
	const empty = (): Listing => ({
		items: [],
		directories: [],
		breadcrumbs: [],
		total: 0,
		page: 0,
		loading: false,
		error: ''
	});
	let cache: Record<string, Listing> = {};
	let results: Listing = empty();
	let expanded = new Set<string>();
	let pending: KnowledgeFile[] = [];
	let timer: ReturnType<typeof setTimeout>;
	let mounted = false;
	let generation = 0;
	let requestIds = new Map<string, number>();
	let filters = '';
	let creating: { parent: string | null; name: string } | null = null;
	let createInput: HTMLInputElement;
	let creatingBusy = false;
	let deletion: { file?: KnowledgeFile; directory?: KnowledgeDirectory } | null = null;
	let showDelete = false;
	let deleteContents = true;
	const key = (id: string | null) => id ?? 'root';
	const report = (error: unknown) =>
		toast.error(error instanceof Error ? error.message : String(error));
	const load = async (id: string | null, more = false, search = false, pages = 1) => {
		const token = generation;
		const cacheKey = search ? 'search' : key(id);
		const request = (requestIds.get(cacheKey) || 0) + 1;
		requestIds.set(cacheKey, request);
		const previous = search ? results : cache[key(id)] || empty();
		const next = { ...previous, loading: true, error: '' };
		if (search) results = next;
		else cache = { ...cache, [key(id)]: next };
		try {
			const page = more ? previous.page + 1 : 1;
			const fetchPage = (page: number) =>
				searchKnowledgeFilesById(
					localStorage.token,
					knowledge.id,
					search ? query : '',
					viewOption,
					sortKey,
					direction,
					page,
					search ? undefined : id,
					includeContent
				);
			const response = await fetchPage(page);
			if (!more && pages > 1) {
				for (
					let nextPage = 2;
					nextPage <= pages && response.items.length < response.total;
					nextPage++
				) {
					if (generation !== token || requestIds.get(cacheKey) !== request) return;
					const next = await fetchPage(nextPage);
					response.items.push(...next.items);
				}
			}
			if (generation !== token || requestIds.get(cacheKey) !== request) return;
			const listing = {
				...response,
				page: more ? page : Math.max(1, Math.ceil(response.items.length / 30)),
				items: more ? [...previous.items, ...response.items] : response.items,
				loading: false,
				error: ''
			};
			if (search) results = listing;
			else cache = { ...cache, [key(id)]: listing };
		} catch (error) {
			if (generation !== token || requestIds.get(cacheKey) !== request) return;
			const listing = { ...previous, loading: false, error: String(error) };
			if (search) results = listing;
			else cache = { ...cache, [key(id)]: listing };
		}
	};
	const reload = async (ids: (string | null)[] = [null, ...expanded]) => {
		const targets = new Set(ids);
		// Collapsed branches must not retain stale children after a move or upload.
		cache = Object.fromEntries(
			Object.entries(cache).filter(([id]) => id === 'root' || expanded.has(id) || targets.has(id))
		);
		await Promise.all([...targets].map((id) => load(id, false, false, cache[key(id)]?.page || 1)));
		if (query) await load(null, false, true, results.page || 1);
	};
	const poll = async () => {
		clearTimeout(timer);
		try {
			const previous = pending;
			const response = await getPendingKnowledgeFiles(localStorage.token, knowledge.id);
			if (!mounted) return;
			pending = response.map((file: KnowledgeFile) => ({
				...file,
				directory_id: file.meta?.data?.directory_id ?? null,
				status: file.data?.status || 'processing'
			}));
			const completed = previous.filter((file) => !pending.some((item) => item.id === file.id));
			if (completed.length) await reload(completed.map((file) => file.directory_id ?? null));
		} catch (error) {
			console.warn('Unable to refresh processing files', error);
		}
		if (mounted && pending.length) timer = setTimeout(poll, 5000);
	};
	export const refresh = async () => {
		await reload();
		await poll();
	};
	$: if (
		mounted &&
		JSON.stringify([query, includeContent, viewOption, sortKey, direction]) !== filters
	) {
		const next = JSON.stringify([query, includeContent, viewOption, sortKey, direction]);
		const previous = filters ? JSON.parse(filters) : null;
		filters = next;
		if (
			!previous ||
			JSON.stringify(previous.slice(1)) !==
				JSON.stringify([includeContent, viewOption, sortKey, direction])
		) {
			++generation;
			cache = {};
			reload();
		} else if (query) load(null, false, true);
		else {
			requestIds.set('search', (requestIds.get('search') || 0) + 1);
			if (!cache.root) reload();
		}
	}
	const toggle = async (directory: KnowledgeDirectory) => {
		if (expanded.has(directory.id)) expanded.delete(directory.id);
		else {
			expanded.add(directory.id);
			if (!cache[directory.id]) await load(directory.id);
		}
		expanded = new Set(expanded);
	};
	export const createDirectory = async (parent: string | null = null) => {
		if (!knowledge.write_access) return;
		if (parent) {
			expanded = new Set([...expanded, parent]);
			if (!cache[parent]) await load(parent);
		}
		query = '';
		creating = { parent, name: '' };
		await tick();
		createInput?.focus();
	};
	const submitDirectory = async () => {
		if (!creating || creatingBusy) return;
		if (!creating.name.trim()) {
			creating = null;
			return;
		}
		creatingBusy = true;
		const { parent, name } = creating;
		try {
			await createKnowledgeDirectory(localStorage.token, knowledge.id, name.trim(), parent);
			creating = null;
			await reload([parent]);
		} catch (error) {
			report(error);
		} finally {
			creatingBusy = false;
		}
	};
	const download = async (file: KnowledgeFile) => {
		try {
			const name = fileName(file);
			const blob = await getFileBlobById(
				localStorage.token,
				file.id!,
				file.has_original === false ? { filename: name } : { attachment: true }
			);
			const url = URL.createObjectURL(blob);
			const anchor = document.createElement('a');
			anchor.href = url;
			anchor.download =
				file.has_original === false && !name.endsWith('.txt') ? `${name}.txt` : name;
			anchor.click();
			setTimeout(() => URL.revokeObjectURL(url), 1000);
		} catch (error) {
			report(error);
		}
	};
	const renameFile = async (file: KnowledgeFile, name: string) => {
		try {
			await renameFileById(localStorage.token, file.id!, name);
			onChanged({ ...file, filename: name, name, meta: { ...file.meta, name } });
			await reload([file.directory_id ?? null]);
		} catch (error) {
			report(error);
			throw error;
		}
	};
	const renameDirectory = async (directory: KnowledgeDirectory, name: string) => {
		try {
			await updateKnowledgeDirectory(localStorage.token, knowledge.id, directory.id, { name });
			await reload();
		} catch (error) {
			report(error);
			throw error;
		}
	};
	const move = async (kind: 'file' | 'directory', id: string, target: string | null) => {
		if (!knowledge.write_access || (kind === 'directory' && id === target)) return;
		try {
			if (kind === 'file') await moveFileInKnowledge(localStorage.token, knowledge.id, id, target);
			else
				await updateKnowledgeDirectory(localStorage.token, knowledge.id, id, { parent_id: target });
			if (target) expanded = new Set([...expanded, target]);
			await reload();
		} catch (error) {
			report(error);
		}
	};
	const remove = async () => {
		if (!deletion || !knowledge.write_access) return;
		try {
			if (deletion.file) {
				await removeFileFromKnowledgeById(localStorage.token, knowledge.id, deletion.file.id!);
				onChanged(undefined, [deletion.file.id!]);
			} else if (deletion.directory) {
				await deleteKnowledgeDirectory(
					localStorage.token,
					knowledge.id,
					deletion.directory.id,
					!deleteContents
				);
				// The selected document may be in an unloaded descendant; let the browser verify membership.
				onChanged();
				expanded.delete(deletion.directory.id);
				expanded = new Set(expanded);
			}
			cache = {};
			await reload();
			deletion = null;
		} catch (error) {
			report(error);
		}
	};
	const askDelete = (value: typeof deletion) =>
		guard(() => {
			deletion = value;
			deleteContents = true;
			showDelete = true;
		});
	const upload = async (type: string, directory: KnowledgeDirectory) => {
		if (type === 'new_directory') {
			await createDirectory(directory.id);
			return;
		}
		if (!cache[directory.id]) await load(directory.id);
		onUpload(type, directory.id, cache[directory.id]?.breadcrumbs || []);
	};
	const rootDrop = (event: DragEvent) => {
		if (!knowledge.write_access) return;
		const raw = event.dataTransfer?.getData('application/x-kb-file-move');
		const dirRaw = event.dataTransfer?.getData('application/x-kb-dir-move');
		if (!raw && !dirRaw) return;
		event.preventDefault();
		event.stopPropagation();
		try {
			if (raw) move('file', JSON.parse(raw).fileId, null);
			else if (dirRaw) move('directory', JSON.parse(dirRaw).dirId, null);
		} catch {}
	};
	onMount(() => {
		mounted = true;
		poll();
	});
	onDestroy(() => {
		mounted = false;
		++generation;
		clearTimeout(timer);
	});
</script>

<ConfirmDialog
	bind:show={showDelete}
	title={$i18n.t(deletion?.directory ? 'Delete folder?' : 'Remove file from knowledge?')}
	on:confirm={remove}
>
	{#if deletion?.directory}<label class="flex items-center gap-2 text-xs"
			><input type="checkbox" bind:checked={deleteContents} />{$i18n.t(
				'Delete all contents inside this directory'
			)}</label
		>{/if}
</ConfirmDialog>
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="min-h-0 flex-1 overflow-auto p-1.5"
	on:keydown={(event) => {
		if (
			!(event.target instanceof HTMLButtonElement) ||
			!event.target.hasAttribute('data-knowledge-entry')
		)
			return;
		const entries = [
			...event.currentTarget.querySelectorAll<HTMLButtonElement>('button[data-knowledge-entry]')
		];
		const index = entries.indexOf(event.target);
		const next =
			event.key === 'ArrowDown'
				? index + 1
				: event.key === 'ArrowUp'
					? index - 1
					: event.key === 'Home'
						? 0
						: event.key === 'End'
							? entries.length - 1
							: null;
		if (next === null) return;
		event.preventDefault();
		entries[Math.max(0, Math.min(entries.length - 1, next))]?.focus();
	}}
>
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="mb-1 px-2 py-1 text-xs text-gray-400"
		on:dragover={(event) => {
			if (
				knowledge.write_access &&
				event.dataTransfer?.types.some((type) => type.startsWith('application/x-kb-'))
			)
				event.preventDefault();
		}}
		on:drop={rootDrop}
		title={$i18n.t('Drop here to move to root')}
	>
		{$i18n.t(query ? 'Search results' : 'All files')}
	</div>
	{#if query}{@render listing(null, results, 0, true)}{:else}{@render branch(null, 0)}{/if}
</div>

{#snippet branch(id: string | null, depth: number)}
	{#if creating && creating.parent === id}<div
			class="flex h-7 items-center"
			style:padding-left={`${26 + depth * 16}px`}
		>
			<input
				bind:this={createInput}
				bind:value={creating.name}
				disabled={creatingBusy}
				aria-label={$i18n.t('Folder name')}
				placeholder={$i18n.t('Folder name')}
				class="h-4 w-full min-w-0 bg-transparent p-0 text-xs leading-4 outline-none"
				on:keydown={(event) => {
					if (event.key === 'Enter') {
						event.preventDefault();
						submitDirectory();
					}
					if (event.key === 'Escape') {
						event.preventDefault();
						creating = null;
					}
				}}
				on:blur={submitDirectory}
			/>
		</div>{/if}
	{#if cache[key(id)]}{@render listing(id, cache[key(id)], depth, false)}{/if}
{/snippet}
{#snippet listing(id: string | null, data: Listing, depth: number, search: boolean)}
	{#if !search}
		{#each data.directories as directory (directory.id)}
			<EntryRow
				item={directory}
				directory
				{depth}
				expanded={expanded.has(directory.id)}
				writeAccess={!!knowledge.write_access}
				onOpen={() => toggle(directory)}
				onRename={(name) => renameDirectory(directory, name)}
				onDelete={() => askDelete({ directory })}
				onAdd={(type) => upload(type, directory)}
				onDrop={(kind, itemId) => move(kind, itemId, directory.id)}
			/>
			{#if expanded.has(directory.id)}{@render branch(directory.id, depth + 1)}{/if}
		{/each}
		{#each [...transfers, ...pending].filter((file, index, all) => (file.directory_id ?? file.meta?.data?.directory_id ?? null) === id && !data.items.some((item) => item.id === file.id) && all.findIndex((item) => (item.id || item.itemId) === (file.id || file.itemId)) === index) as file (file.id || file.itemId)}
			<EntryRow
				item={file}
				{depth}
				active={selectedFileId === file.id}
				onOpen={() => onSelect(file)}
			/>
		{/each}
	{/if}
	{#each data.items as file (file.id)}<EntryRow
			item={file}
			{depth}
			{search}
			active={selectedFileId === file.id}
			writeAccess={!!knowledge.write_access}
			onOpen={() => onSelect(file)}
			onRename={(name) => renameFile(file, name)}
			onDelete={() => askDelete({ file })}
			onDownload={() => download(file)}
		/>{/each}
	{#if data.loading}<div class="p-2"><Spinner className="size-3" /></div>
	{:else if data.error}<div class="p-2 text-xs">
			<p role="alert">{data.error}</p>
			<button type="button" on:click={() => load(id, false, search)}>{$i18n.t('Retry')}</button>
		</div>
	{:else if data.items.length < data.total}<button
			type="button"
			class="px-2 py-1 text-xs text-gray-500"
			on:click={() => load(id, true, search)}>{$i18n.t('Load more')}</button
		>
	{:else if !data.items.length && (search || !data.directories.length)}<p
			class="px-2 py-1 text-xs text-gray-400"
		>
			{$i18n.t(search ? 'No results found' : 'No files')}
		</p>{/if}
{/snippet}
