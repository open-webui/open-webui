<script lang="ts">
	import { getContext, onDestroy } from 'svelte';
	import { writable } from 'svelte/store';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { v4 as uuidv4 } from 'uuid';
	import type { AppLayoutContext } from '$lib/types';

	import {
		chatId,
		config,
		embed,
		selectedFolder,
		settings,
		showEmbeds,
		showTabs,
		user
	} from '$lib/stores';
	import { updateFolderDetails, type FolderDetails } from '$lib/stores/folderStates';
	import { getFolderById, updateFolderById } from '$lib/apis/folders';
	import { uploadFile } from '$lib/apis/files';
	import { decodeString, formatFileSize } from '$lib/utils';

	import FilesOverlay from '$lib/components/chat/MessageInput/FilesOverlay.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ChatBubble from '$lib/components/icons/ChatBubble.svelte';
	import Database from '$lib/components/icons/Database.svelte';
	import DocumentPage from '$lib/components/icons/DocumentPage.svelte';
	import Folder from '$lib/components/icons/Folder.svelte';
	import PageEdit from '$lib/components/icons/PageEdit.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext<typeof import('$lib/i18n').default>('i18n');
	const appLayout = getContext<AppLayoutContext | undefined>('appLayout');

	/** The folder's knowledge as a list, saved as soon as it changes, like the edit modal's Knowledge field. */
	export let folder: FolderDetails | null = null;
	export let readOnly = false;
	/** Opens the knowledge picker, which lives with the section's toolbar button. */
	export let onPick: () => void = () => {};

	type Item = {
		type?: string;
		id?: string | null;
		name?: string;
		description?: string;
		size?: number;
		status?: string;
		itemId?: string;
		context?: string;
		[key: string]: any;
	};

	let uploads: Item[] = [];
	let removing = new Set<string>();
	let saving = 0;
	let dragging = false;
	let inputElement: HTMLInputElement;

	$: files = (folder?.data?.files ?? []) as Item[];
	/** Everything shown, saved first, so the count in the toolbar matches the list. */
	export let items: Item[] = [];
	$: items = [...files, ...uploads];

	$: canUpload =
		!readOnly && ($user?.role === 'admin' || ($user?.permissions?.chat?.file_upload ?? true));

	const keyOf = (item: Item) => `${item.type ?? 'file'}:${item.id ?? item.itemId}`;
	const sameEntry = (a: Item, b: Item) =>
		(a.type ?? 'file') === (b.type ?? 'file') && a.id === b.id;

	const maxFiles = () => {
		const max = $config?.features?.folder_max_file_count;
		return max ? Number(max) : null;
	};

	// Changes save one at a time against the folder's latest list, so uploads finishing together
	// and a shared folder's other editors don't overwrite each other's additions.
	let queue: Promise<unknown> = Promise.resolve();
	function save(change: (current: Item[]) => Item[] | null): Promise<boolean> {
		const folderId = folder?.id;
		if (!folderId || readOnly) return Promise.resolve(false);
		saving++;
		const run = queue
			.then(async () => {
				const latest = await getFolderById(localStorage.token, folderId);
				const next = change((latest?.data?.files ?? []) as Item[]);
				if (!next) return false;
				const updated = await updateFolderById(localStorage.token, folderId, {
					data: { files: next }
				});
				if (!updated) return false;
				updateFolderDetails(folderId, updated);
				selectedFolder.update((current) =>
					current?.id === folderId ? { ...current, ...updated } : current
				);
				return true;
			})
			.catch((error) => {
				toast.error(`${error?.detail ?? error}`);
				return false;
			})
			.finally(() => saving--);
		queue = run;
		return run;
	}

	/** Adds a knowledge base, note, chat or file picked from the knowledge picker. */
	export function add(item: Item) {
		if (readOnly || items.some((entry) => sameEntry(entry, item))) return;
		void save((current) => {
			if (current.some((entry) => sameEntry(entry, item))) return null;
			const max = maxFiles();
			if (max && current.length >= max) {
				toast.error($i18n.t('Maximum number of files per folder is {{max}}.', { max }));
				return null;
			}
			return [...current, item];
		});
	}

	async function remove(item: Item) {
		const key = keyOf(item);
		removing = new Set(removing).add(key);
		await save((current) => current.filter((entry) => !sameEntry(entry, item)));
		removing.delete(key);
		removing = removing;
	}

	/** Opens the file chooser. */
	export function upload() {
		if (canUpload) inputElement?.click();
	}

	async function uploadOne(file: File) {
		if (file.size === 0) {
			toast.error($i18n.t('You cannot upload an empty file.'));
			return;
		}
		const maxSize = $config?.file?.max_size ?? null;
		if (maxSize !== null && file.size > maxSize * 1024 * 1024) {
			toast.error($i18n.t(`File size should not exceed {{maxSize}} MB.`, { maxSize }));
			return;
		}
		if (file.type.startsWith('image/')) {
			toast.error($i18n.t(`Unsupported file type.`));
			return;
		}
		const max = maxFiles();
		if (max && items.length >= max) {
			toast.error($i18n.t('Maximum number of files per folder is {{max}}.', { max }));
			return;
		}

		const itemId = uuidv4();
		const pending: Item = {
			type: 'file',
			file: '',
			id: null,
			url: '',
			name: file.name,
			collection_name: '',
			status: 'uploading',
			size: file.size,
			error: '',
			itemId
		};
		uploads = [...uploads, pending];

		try {
			// Audio and video are transcribed on upload, in the user's speech-to-text language.
			const language = $settings?.audio?.stt?.language;
			const metadata =
				(file.type.startsWith('audio/') || file.type.startsWith('video/')) && language
					? { language }
					: null;
			const uploaded = await uploadFile(localStorage.token, file, metadata);
			if (!uploaded) return;
			if (uploaded.error) toast.warning(uploaded.error);

			const item: Item = {
				...pending,
				status: 'uploaded',
				file: uploaded,
				id: uploaded.id,
				collection_name: uploaded?.meta?.collection_name || uploaded?.collection_name,
				url: `${uploaded.id}`
			};
			await save((current) => {
				const max = maxFiles();
				if (max && current.length >= max) {
					toast.error($i18n.t('Maximum number of files per folder is {{max}}.', { max }));
					return null;
				}
				return [...current, item];
			});
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			uploads = uploads.filter((entry) => entry.itemId !== itemId);
		}
	}

	function uploadAll(list: FileList | File[] | null | undefined) {
		if (!canUpload) {
			if (!readOnly) toast.error($i18n.t('You do not have permission to upload files.'));
			return;
		}
		for (const file of Array.from(list ?? [])) void uploadOne(file);
	}

	// Notes and chats open as their own page, in a tab beside the folder like chats do.
	const pageOf = (item: Item) =>
		!item.id
			? null
			: item.type === 'note'
				? `/notes/${item.id}`
				: item.type === 'chat'
					? `/c/${item.id}`
					: null;
	const canOpen = (item: Item) =>
		item.status !== 'uploading' &&
		(!!pageOf(item) || ['file', 'collection'].includes(item.type ?? 'file'));

	function open(item: Item) {
		if (!canOpen(item)) return;
		const href = pageOf(item);
		if (href) {
			if (appLayout?.openPageTab) appLayout.openPageTab({ href, label: item.name ?? '' });
			else void goto(href);
			return;
		}
		if (item.id) openFile(item);
	}

	// A file's tab can switch it between focused retrieval and its full text while the folder is shown.
	let openedFiles: { folderId?: string; item: Item }[] = [];
	const attachedFiles = writable<Item[]>([]);
	$: attachedFiles.set(
		readOnly
			? []
			: openedFiles
					.filter(
						(file) =>
							file.folderId === folder?.id && files.some((entry) => sameEntry(entry, file.item))
					)
					.map((file) => file.item)
	);
	onDestroy(() => {
		attachedFiles.set([]);
		if ($embed?.file?.attachedFiles === attachedFiles) embed.set(null);
	});

	function openFile(item: Item) {
		const attachment = { ...item, type: item.type ?? 'file' };
		openedFiles = [
			...openedFiles.filter((file) => !sameEntry(file.item, item)),
			{ folderId: folder?.id, item: attachment }
		];
		showTabs.set(true);
		showEmbeds.set(true);
		embed.set({
			file: {
				id: item.type === 'collection' ? undefined : item.id,
				knowledgeId: item.type === 'collection' ? item.id : null,
				page: null,
				passages: [],
				content: item.file?.data?.content ?? '',
				attachment,
				attachedFiles,
				onAttachmentChange: () => {
					const { context } = attachment as Item;
					void save((current) =>
						current.map((entry) =>
							sameEntry(entry, attachment)
								? context
									? { ...entry, context }
									: (({ context, ...rest }) => rest)(entry)
								: entry
						)
					);
				}
			},
			key: item.id,
			url: item.url,
			title: decodeString(item.name ?? ''),
			chatId: $chatId
		});
	}

	const typeLabel = (item: Item) =>
		item.type === 'collection'
			? $i18n.t('Knowledge')
			: item.type === 'note'
				? $i18n.t('Note')
				: item.type === 'chat'
					? $i18n.t('Chat')
					: item.type === 'folder'
						? $i18n.t('Folder')
						: $i18n.t('File');

	const isFiles = (event: DragEvent) => event.dataTransfer?.types.includes('Files') ?? false;
</script>

<input
	bind:this={inputElement}
	type="file"
	hidden
	multiple
	on:change={(event) => {
		uploadAll(event.currentTarget.files);
		event.currentTarget.value = '';
	}}
/>

<!-- Dropped files land in the folder, not in the composer (see MessageInput's isAttachmentDrop). -->
<div
	class="relative h-full"
	data-file-drop-target
	role="region"
	aria-label={$i18n.t('Knowledge')}
	aria-busy={saving > 0}
	on:dragover={(event) => {
		if (!canUpload || !isFiles(event)) return;
		event.preventDefault();
		dragging = true;
	}}
	on:dragleave={(event) => {
		if (!event.currentTarget.contains(event.relatedTarget as Node)) dragging = false;
	}}
	on:drop={(event) => {
		dragging = false;
		if (!canUpload || !isFiles(event)) return;
		event.preventDefault();
		uploadAll(event.dataTransfer?.files);
	}}
>
	{#if !items.length}
		<div class="flex h-full flex-col items-center justify-center gap-1 px-6 pb-16 text-center">
			<div class="text-sm text-base-800 dark:text-base-100">{$i18n.t('No knowledge yet')}</div>
			<div class="text-xs text-base-500 dark:text-base-400">
				{readOnly
					? $i18n.t('Knowledge added to this folder will show up here.')
					: $i18n.t('Add knowledge bases, notes, or files. New chats in this folder can use them.')}
			</div>
			{#if !readOnly}
				<div class="mt-2 flex items-center gap-3 text-xs">
					<button
						type="button"
						class="text-base-400 transition-colors hover:text-base-600 dark:text-base-500 dark:hover:text-base-300"
						on:click={onPick}>{$i18n.t('Add knowledge')}</button
					>
					{#if canUpload}
						<button
							type="button"
							class="text-base-400 transition-colors hover:text-base-600 dark:text-base-500 dark:hover:text-base-300"
							on:click={upload}>{$i18n.t('Upload Files')}</button
						>
					{/if}
				</div>
			{/if}
		</div>
	{:else}
		<ul class="scrollbar-hidden h-full overflow-y-auto px-3" aria-label={$i18n.t('Knowledge')}>
			{#each items as item (keyOf(item))}
				{@const busy = item.status === 'uploading' || removing.has(keyOf(item))}
				<li
					class="flex items-center gap-2.5 rounded-xl px-3 py-1.5 transition-colors hover:bg-base-50 dark:hover:bg-base-850/50"
				>
					<button
						type="button"
						class="flex min-w-0 flex-1 items-center gap-2.5 text-left disabled:cursor-default"
						disabled={!canOpen(item)}
						title={item.description || item.name || item.id || ''}
						on:click={() => open(item)}
					>
						<span class="shrink-0 text-base-400 dark:text-base-500">
							{#if busy}
								<Spinner className="size-3.5" />
							{:else if item.type === 'collection'}
								<Database className="size-3.5" />
							{:else if item.type === 'note'}
								<PageEdit className="size-3.5" />
							{:else if item.type === 'chat'}
								<ChatBubble className="size-3.5" />
							{:else if item.type === 'folder'}
								<Folder className="size-3.5" />
							{:else}
								<DocumentPage className="size-3.5" />
							{/if}
						</span>
						<span
							class="min-w-0 shrink truncate text-[0.8125rem] leading-5 text-base-700 dark:text-base-200"
							>{decodeString(item.name || item.id || '')}</span
						>
						{#if item.context === 'full'}
							<span class="hidden shrink-0 text-xs text-base-400 @md:block dark:text-base-500"
								>{$i18n.t('Full text')}</span
							>
						{/if}
					</button>
					<span class="shrink-0 text-[0.6875rem] tabular-nums text-base-400 dark:text-base-500">
						{#if item.status === 'uploading'}
							{$i18n.t('Uploading')}
						{:else if (item.type ?? 'file') === 'file' && item.size}
							{formatFileSize(item.size)}
						{:else}
							{typeLabel(item)}
						{/if}
					</span>
					{#if !readOnly && item.status !== 'uploading'}
						<button
							type="button"
							class="flex size-5 shrink-0 items-center justify-center rounded-full text-base-400 transition hover:text-base-700 disabled:opacity-50 dark:text-base-500 dark:hover:text-base-200"
							aria-label={$i18n.t('Remove File')}
							title={$i18n.t('Remove')}
							disabled={busy}
							on:click={() => remove(item)}><XMark className="size-3" /></button
						>
					{/if}
				</li>
			{/each}
		</ul>
	{/if}

	<FilesOverlay show={dragging} />
</div>
