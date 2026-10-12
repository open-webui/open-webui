<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { v4 as uuidv4 } from 'uuid';

	import { onMount, getContext, onDestroy } from 'svelte';
	import KnowledgeBrowser from './KnowledgeBase/Browser.svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { config, user, settings } from '$lib/stores';

	import { uploadFile } from '$lib/apis/files';
	import {
		addFileToKnowledgeById,
		getKnowledgeById,
		resetKnowledgeById,
		updateKnowledgeById,
		updateKnowledgeAccessGrants,
		createKnowledgeDirectory,
		syncKnowledgeDiff,
		syncKnowledgeCleanup,
		testExternalKnowledgeRetrieval
	} from '$lib/apis/knowledge';
	import { processUrl } from '$lib/apis/retrieval';

	import { blobToFile, copyToClipboard } from '$lib/utils';
	import { computeFileHash } from '$lib/utils/hash';

	import Spinner from '$lib/components/common/Spinner.svelte';

	import AddTextContentModal from './KnowledgeBase/AddTextContentModal.svelte';

	import SyncConfirmDialog from '../../common/ConfirmDialog.svelte';
	import ConfirmDialog from '../../common/ConfirmDialog.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import AccessButton from '$lib/components/common/AccessButton.svelte';
	import AccessControlModal from '../common/AccessControlModal.svelte';
	import FilesOverlay from '$lib/components/chat/MessageInput/FilesOverlay.svelte';
	import AttachWebpageModal from '$lib/components/chat/MessageInput/AttachWebpageModal.svelte';

	let showAddWebpageModal = false;
	let showAddTextContentModal = false;

	let showSyncConfirmModal = false;
	let pendingSyncFiles: Array<{ path: string; filename: string; file: File }> | null = null;
	let syncing: string | null = null;
	let showAccessControlModal = false;
	let showResetConfirm = false;

	type DirectoryFileEntry = { path: string; filename: string; file: File };
	type DirectoryManifestEntry = DirectoryFileEntry & { checksum: string; size: number };

	type Knowledge = {
		id: string;
		name: string;
		description: string;
		data: {
			file_ids: string[];
		};
		files: any[];
		access_grants?: any[];
		write_access?: boolean;
		meta?: any;
	};

	let id = null;
	let knowledge: Knowledge | null = null;
	let isExternalKnowledge = false;

	let inputFiles = null;
	let fileItems: any[] = [];
	let currentDirectoryId: string | null = null;
	let breadcrumbs: any[] = [];

	let externalTestQuery = '';
	let externalTestResult: {
		documents?: string[];
		metadatas?: Record<string, any>[];
		distances?: number[];
	} | null = null;

	$: isExternalKnowledge = knowledge?.meta?.source === 'external';

	let browser: KnowledgeBrowser;
	const init = async () => {
		await browser?.refresh();
	};
	const requestUpload = (type: string, parent: string | null, ancestors: any[]) => {
		currentDirectoryId = parent;
		breadcrumbs = ancestors;
		if (type === 'directory') uploadDirectoryHandler();
		else if (type === 'web') showAddWebpageModal = true;
		else if (type === 'text') showAddTextContentModal = true;
		else document.getElementById('files-input')?.click();
	};

	const externalTestHandler = async () => {
		if (!isExternalKnowledge || !externalTestQuery.trim()) return;

		const external = knowledge?.meta?.external ?? {};
		const res = await testExternalKnowledgeRetrieval(localStorage.token, external.connection_id, {
			query: externalTestQuery,
			source: external.source,
			count: 5
		}).catch((e) => {
			toast.error(`${e}`);
			return null;
		});

		if (res) {
			externalTestResult = res;
		}
	};

	const createFileFromText = (name, content) => {
		const blob = new Blob([content], { type: 'text/plain' });
		const file = blobToFile(blob, `${name}.txt`);

		console.log(file);
		return file;
	};

	const uploadWeb = async (urls) => {
		const targetDirectoryId = currentDirectoryId;
		if (!knowledge) {
			toast.error($i18n.t('Knowledge base not found.'));
			return;
		}

		if (!Array.isArray(urls)) {
			urls = [urls];
		}

		const newFileItems = urls.map((url) => ({
			type: 'file',
			file: '',
			id: null,
			url: url,
			name: url,
			size: null,
			status: 'uploading',
			error: '',
			directory_id: targetDirectoryId,
			itemId: uuidv4()
		}));

		// Display all items at once
		fileItems = [...newFileItems, ...(fileItems ?? [])];

		for (const fileItem of newFileItems) {
			try {
				console.log(fileItem);
				const res = await processUrl(localStorage.token, fileItem.url);

				if (res) {
					console.log(res);
					let uploadedFile = res.file;

					if (res.type === 'web' || res.type === 'youtube') {
						const file = createFileFromText(
							// Use URL as filename, sanitized
							fileItem.url
								.replace(/[^a-z0-9]/gi, '_')
								.toLowerCase()
								.slice(0, 50),
							res.content ?? ''
						);

						uploadedFile = await uploadFile(localStorage.token, file, {
							knowledge_id: knowledge.id,
							directory_id: targetDirectoryId,
							source_url: fileItem.url
						});
					} else if (uploadedFile?.id) {
						const linkedKnowledge = await addFileToKnowledgeById(
							localStorage.token,
							knowledge.id,
							uploadedFile.id,
							targetDirectoryId
						).catch((e) => {
							toast.error(`${e}`);
							return null;
						});
						if (!linkedKnowledge) {
							toast.error($i18n.t('Failed to add file.'));
							uploadedFile = null;
						}
					}

					if (uploadedFile) {
						console.log(uploadedFile);
						fileItems = fileItems.map((item) => {
							if (item.itemId === fileItem.itemId) {
								item.id = uploadedFile.id;
							}
							return item;
						});

						if (uploadedFile.error) {
							console.warn('File upload warning:', uploadedFile.error);
							toast.warning(uploadedFile.error);
							fileItems = fileItems.filter((file) => file.id !== uploadedFile.id);
						} else {
							toast.success($i18n.t('File added successfully.'));
							init();
						}
					} else {
						toast.error($i18n.t('Failed to upload file.'));
					}
				} else {
					// remove the item from fileItems
					fileItems = fileItems.filter((item) => item.itemId !== fileItem.itemId);
					toast.error($i18n.t('Failed to process URL: {{url}}', { url: fileItem.url }));
				}
			} catch (e) {
				// remove the item from fileItems
				fileItems = fileItems.filter((item) => item.itemId !== fileItem.itemId);
				toast.error(`${e}`);
			} finally {
				fileItems = fileItems.filter((item) => item.itemId !== fileItem.itemId);
				await init();
			}
		}
	};

	const uploadFileHandler = async (file) => {
		const targetDirectoryId = currentDirectoryId;
		console.log(file);

		const fileItem = {
			type: 'file',
			file: '',
			id: null,
			url: '',
			name: file.name,
			size: file.size,
			status: 'uploading',
			error: '',
			directory_id: targetDirectoryId,
			itemId: uuidv4()
		};

		if (fileItem.size == 0) {
			toast.error($i18n.t('You cannot upload an empty file.'));
			return null;
		}

		if (
			($config?.file?.max_size ?? null) !== null &&
			file.size > ($config?.file?.max_size ?? 0) * 1024 * 1024
		) {
			console.log('File exceeds max size limit:', {
				fileSize: file.size,
				maxSize: ($config?.file?.max_size ?? 0) * 1024 * 1024
			});
			toast.error(
				$i18n.t(`File size should not exceed {{maxSize}} MB.`, {
					maxSize: $config?.file?.max_size
				})
			);
			return;
		}

		fileItems = [fileItem, ...(fileItems ?? [])];
		try {
			let metadata = {
				knowledge_id: knowledge.id,
				directory_id: targetDirectoryId,
				// If the file is an audio file, provide the language for STT.
				...((file.type.startsWith('audio/') || file.type.startsWith('video/')) &&
				$settings?.audio?.stt?.language
					? {
							language: $settings?.audio?.stt?.language
						}
					: {})
			};

			const uploadedFile = await uploadFile(localStorage.token, file, metadata).catch((e) => {
				toast.error(`${e}`);
				return null;
			});

			if (uploadedFile) {
				console.log(uploadedFile);
				fileItems = fileItems.map((item) => {
					if (item.itemId === fileItem.itemId) {
						item.id = uploadedFile.id;
					}
					return item;
				});

				if (uploadedFile.error) {
					console.warn('File upload warning:', uploadedFile.error);
					toast.warning(uploadedFile.error);
					fileItems = fileItems.filter((file) => file.id !== uploadedFile.id);
				} else {
					toast.success($i18n.t('File added successfully.'));
					init();
				}
			} else {
				toast.error($i18n.t('Failed to upload file.'));
			}
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			fileItems = fileItems.filter((item) => item.itemId !== fileItem.itemId);
			await init();
		}
	};

	const uploadDirectoryHandler = async () => {
		const entries = await collectDirectoryFiles();
		if (entries?.length) {
			await uploadDirectoryEntries(entries);
		}
	};

	// Helper function to check if a path contains hidden folders
	const hasHiddenFolder = (path) => {
		return path.split('/').some((part) => part.startsWith('.'));
	};

	// Error handler
	const handleUploadError = (error) => {
		if (error.name === 'AbortError') {
			toast.info($i18n.t('Directory selection was cancelled'));
		} else {
			toast.error(`${$i18n.t('Error accessing directory')}: ${error.message}`);
			console.error('Directory access error:', error);
		}
	};

	// Collect files from a directory without uploading.
	const collectDirectoryFiles = async (): Promise<DirectoryFileEntry[] | null> => {
		const isFileSystemAccessSupported = 'showDirectoryPicker' in window;

		try {
			if (isFileSystemAccessSupported) {
				const dirHandle = await window.showDirectoryPicker();
				const collected: DirectoryFileEntry[] = [];

				async function traverse(handle: FileSystemDirectoryHandle, dirPath = '') {
					for await (const entry of handle.values()) {
						if (entry.name.startsWith('.')) continue;
						const entryPath = dirPath ? `${dirPath}/${entry.name}` : entry.name;
						if (hasHiddenFolder(entryPath)) continue;

						if (entry.kind === 'file') {
							let file: File;
							try {
								file = await entry.getFile();
							} catch (error) {
								throw new Error(`"${entryPath}": ${error}`);
							}
							collected.push({ path: dirPath, filename: entry.name, file });
						} else if (entry.kind === 'directory') {
							await traverse(entry, entryPath);
						}
					}
				}

				await traverse(dirHandle, dirHandle.name);
				return collected;
			} else {
				// Firefox fallback
				return new Promise((resolve, reject) => {
					const input = document.createElement('input');
					input.type = 'file';
					input.webkitdirectory = true;
					input.directory = true;
					input.multiple = true;
					input.style.display = 'none';
					document.body.appendChild(input);

					input.onchange = () => {
						try {
							const files = Array.from(input.files || []).filter(
								(file) => !hasHiddenFolder(file.webkitRelativePath) && !file.name.startsWith('.')
							);

							const collected = files.map((file) => {
								const parts = file.webkitRelativePath.split('/');
								const filename = parts.pop() || file.name;
								const path = parts.join('/');
								return { path, filename, file };
							});

							document.body.removeChild(input);
							resolve(collected);
						} catch (error) {
							document.body.removeChild(input);
							reject(error);
						}
					};

					input.onerror = (error) => {
						document.body.removeChild(input);
						reject(error);
					};

					input.click();
				});
			}
		} catch (error) {
			handleUploadError(error);
			return null;
		}
	};

	const buildDirectoryManifest = async (
		entries: DirectoryFileEntry[]
	): Promise<DirectoryManifestEntry[]> => {
		return Promise.all(
			entries.map(async (entry) => ({
				...entry,
				checksum: await computeFileHash(entry.file),
				size: entry.file.size
			}))
		);
	};

	const createMissingDirectories = async (diff: any) => {
		if (!knowledge) return {};

		const directoryIdByPath: Record<string, string> = { ...(diff.directory_map || {}) };

		for (const dirPath of diff.mkdir) {
			const segments = dirPath.split('/');
			const name = segments.at(-1)!;
			const parentPath = segments.slice(0, -1).join('/');
			const parentId = parentPath ? directoryIdByPath[parentPath] : null;

			const directory = await createKnowledgeDirectory(
				localStorage.token,
				knowledge.id,
				name,
				parentId
			);
			if (directory) {
				directoryIdByPath[dirPath] = directory.id;
			}
		}

		return directoryIdByPath;
	};

	const uploadManifestEntries = async (
		entries: DirectoryManifestEntry[],
		resolveDirectoryId: (entry: DirectoryManifestEntry) => string | null | undefined
	) => {
		let failedCount = 0;

		for (const [index, entry] of entries.entries()) {
			const displayPath = entry.path ? `${entry.path}/${entry.filename}` : entry.filename;
			syncing = $i18n.t('Uploading {{current}}/{{total}}: {{file}}', {
				current: index + 1,
				total: entries.length,
				file: displayPath
			});

			const fileObject = new File([entry.file], entry.filename, { type: entry.file.type });
			const uploadedFile = await uploadFile(localStorage.token, fileObject, {
				knowledge_id: knowledge.id,
				file_hash: entry.checksum,
				directory_id: resolveDirectoryId(entry)
			}).catch((error) => ({ error }));

			if (!uploadedFile || uploadedFile.error) {
				const error = uploadedFile?.error;
				const reason =
					typeof error === 'string'
						? error
						: (error?.detail ?? error?.message ?? $i18n.t('Failed to upload file.'));

				failedCount++;
				console.error('Upload failed:', displayPath, reason);
			}
		}

		if (failedCount > 0) {
			toast.error(
				$i18n.t('Upload failed for {{failed}} of {{total}} files.', {
					failed: failedCount,
					total: entries.length
				})
			);
		}

		return failedCount;
	};

	const uploadDirectoryEntries = async (entries: DirectoryFileEntry[]) => {
		if (!knowledge) return;
		const targetDirectoryId = currentDirectoryId;
		const targetPath = breadcrumbs.map((crumb) => crumb.name).join('/');
		const getDirectoryUploadPath = (path: string) =>
			targetPath && path ? `${targetPath}/${path}` : targetPath || path;

		try {
			syncing = $i18n.t('Computing checksums ({{count}} files)', { count: entries.length });
			const manifest = await buildDirectoryManifest(entries);

			syncing = $i18n.t('Comparing with knowledge base...');
			const diff = await syncKnowledgeDiff(
				localStorage.token,
				id,
				manifest.map(({ filename, path, checksum, size }) => ({
					filename,
					path: getDirectoryUploadPath(path),
					checksum,
					size
				}))
			);

			if (!diff) {
				toast.error($i18n.t('Failed to compare files.'));
				return;
			}

			const directoryIdByPath = await createMissingDirectories(diff);

			const failedCount = await uploadManifestEntries(manifest, (entry) =>
				entry.path ? directoryIdByPath[getDirectoryUploadPath(entry.path)] : targetDirectoryId
			);

			if (failedCount === 0) {
				toast.success($i18n.t('File uploaded successfully'));
			}

			init();
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			syncing = null;
		}
	};

	// Incremental sync: hash locally → diff on server → upload only what changed
	const syncDirectoryHandler = async () => {
		if (!pendingSyncFiles?.length) return;

		try {
			// ── 2. Compute checksums ──
			syncing = $i18n.t('Computing checksums ({{count}} files)', {
				count: pendingSyncFiles.length
			});
			const manifest = await buildDirectoryManifest(pendingSyncFiles);
			pendingSyncFiles = null;

			// ── 3. Diff against knowledge base ──
			syncing = $i18n.t('Comparing with knowledge base...');
			const diff = await syncKnowledgeDiff(
				localStorage.token,
				id,
				manifest.map(({ filename, path, checksum, size }) => ({ filename, path, checksum, size }))
			);

			if (!diff) {
				toast.error($i18n.t('Failed to compare files.'));
				return;
			}

			// ── 4. Cleanup — remove deleted + stale modified files first ──
			const staleFileIds = [
				...diff.deleted.map((d: any) => d.file_id),
				...diff.modified.map((m: any) => m.stale_file_id)
			];

			if (staleFileIds.length > 0 || diff.rmdir.length > 0) {
				syncing = $i18n.t('Removing {{count}} stale files...', { count: staleFileIds.length });
				await syncKnowledgeCleanup(localStorage.token, id, staleFileIds, diff.rmdir);
				browser?.clearRemovedSelection(staleFileIds);
			}

			// ── 5. mkdir — create missing directories (parents first) ──
			const directoryIdByPath = await createMissingDirectories(diff);

			// ── 6. Upload added + modified files ──
			const filesToUpload = manifest.filter(
				(entry) =>
					diff.added.some((a: any) => a.filename === entry.filename && a.path === entry.path) ||
					diff.modified.some((m: any) => m.filename === entry.filename && m.path === entry.path)
			);

			const failedCount = await uploadManifestEntries(filesToUpload, (entry) =>
				entry.path ? directoryIdByPath[entry.path] : null
			);

			// ── 7. Report ──
			if (failedCount === 0) {
				toast.success(
					$i18n.t(
						'Sync complete: {{added}} added, {{modified}} modified, {{deleted}} deleted, {{unmodified}} unmodified',
						{
							added: diff.added.length,
							modified: diff.modified.length,
							deleted: diff.deleted.length,
							unmodified: diff.unmodified_count
						}
					)
				);
			}
			init();
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			syncing = null;
		}
	};

	let debounceTimeout = null;

	let dragged = false;

	const changeDebounceHandler = () => {
		console.log('debounce');
		if (debounceTimeout) {
			clearTimeout(debounceTimeout);
		}

		debounceTimeout = setTimeout(async () => {
			if (knowledge.name.trim() === '' || knowledge.description.trim() === '') {
				toast.error($i18n.t('Please fill in all fields.'));
				return;
			}

			const res = await updateKnowledgeById(localStorage.token, id, {
				...knowledge,
				name: knowledge.name,
				description: knowledge.description,
				access_grants: knowledge.access_grants ?? []
			}).catch((e) => {
				toast.error(`${e}`);
			});

			if (res) {
				toast.success($i18n.t('Knowledge updated successfully'));
			}
		}, 1000);
	};

	const readDirectoryEntries = async (reader: any) => {
		const entries: any[] = [];

		while (true) {
			const batch = await new Promise<any[]>((resolve, reject) => {
				reader.readEntries(resolve, reject);
			});

			if (batch.length === 0) {
				break;
			}

			entries.push(...batch);
		}

		return entries;
	};

	const collectDroppedEntryFiles = async (
		entry: any,
		entryPath = entry.name
	): Promise<DirectoryFileEntry[]> => {
		if (entry.name.startsWith('.') || hasHiddenFolder(entryPath)) {
			return [];
		}

		if (entry.isFile) {
			let file: File;
			try {
				file = await new Promise<File>((resolve, reject) => {
					entry.file(resolve, reject);
				});
			} catch (error) {
				throw new Error(`"${entryPath}": ${error}`);
			}
			const parts = entryPath.split('/');
			const filename = parts.pop() || file.name;
			return [{ path: parts.join('/'), filename, file }];
		}

		if (entry.isDirectory) {
			const reader = entry.createReader();
			const entries = await readDirectoryEntries(reader);
			const nested = await Promise.all(
				entries.map((child) => collectDroppedEntryFiles(child, `${entryPath}/${child.name}`))
			);
			return nested.flat();
		}

		return [];
	};

	const onDragOver = (e) => {
		e.preventDefault();

		// Check if a file is being draggedOver.
		if (e.dataTransfer?.types?.includes('Files')) {
			dragged = true;
		} else {
			dragged = false;
		}
	};

	const onDragLeave = () => {
		dragged = false;
	};

	const onDrop = async (e) => {
		e.preventDefault();
		dragged = false;

		if (isExternalKnowledge || !knowledge?.write_access) {
			toast.error($i18n.t('You do not have permission to upload files to this knowledge base.'));
			return;
		}

		if (e.dataTransfer?.types?.includes('Files')) {
			currentDirectoryId = null;
			breadcrumbs = [];
			if (e.dataTransfer?.files) {
				const inputItems = e.dataTransfer?.items;

				if (inputItems && inputItems.length > 0) {
					const directoryEntries: DirectoryFileEntry[] = [];
					const looseFiles: File[] = [];

					for (const rawItem of Array.from(inputItems)) {
						const item = rawItem as DataTransferItem & { webkitGetAsEntry?: () => any };
						const entry = item.webkitGetAsEntry?.();

						if (entry?.isDirectory) {
							try {
								directoryEntries.push(...(await collectDroppedEntryFiles(entry)));
							} catch (error) {
								handleUploadError(error);
								return;
							}
						} else {
							const file = item.getAsFile();
							if (file) {
								looseFiles.push(file);
							}
						}
					}

					for (const file of looseFiles) {
						await uploadFileHandler(file);
					}

					if (directoryEntries.length > 0) {
						await uploadDirectoryEntries(directoryEntries);
					}
				} else {
					toast.error($i18n.t(`File not found.`));
				}
			}
		}
	};

	onMount(async () => {
		id = $page.params.id;
		const res = await getKnowledgeById(localStorage.token, id).catch((e) => {
			toast.error(`${e}`);
			return null;
		});

		if (res) {
			knowledge = res;
			if (!Array.isArray(knowledge?.access_grants)) {
				knowledge.access_grants = [];
			}
		} else {
			goto('/workspace/knowledge');
		}

		const dropZone = document.querySelector('body');
		dropZone?.addEventListener('dragover', onDragOver);
		dropZone?.addEventListener('drop', onDrop);
		dropZone?.addEventListener('dragleave', onDragLeave);
	});

	onDestroy(() => {
		clearTimeout(debounceTimeout);
		const dropZone = document.querySelector('body');
		dropZone?.removeEventListener('dragover', onDragOver);
		dropZone?.removeEventListener('drop', onDrop);
		dropZone?.removeEventListener('dragleave', onDragLeave);
	});
</script>

<FilesOverlay show={dragged} />
<SyncConfirmDialog
	bind:show={showSyncConfirmModal}
	message={$i18n.t(
		'{{count}} files selected. Only new and modified files will be uploaded. Deleted files will be removed. The folder structure will be mirrored. Continue?',
		{ count: pendingSyncFiles?.length ?? 0 }
	)}
	on:confirm={() => {
		syncDirectoryHandler();
	}}
	on:cancel={() => {
		pendingSyncFiles = null;
	}}
/>

<AttachWebpageModal
	bind:show={showAddWebpageModal}
	onSubmit={async (e) => {
		uploadWeb(e.data);
	}}
/>

<AddTextContentModal
	bind:show={showAddTextContentModal}
	on:submit={(e) => {
		const file = createFileFromText(e.detail.name, e.detail.content);
		uploadFileHandler(file);
	}}
/>

<input
	id="files-input"
	bind:files={inputFiles}
	type="file"
	multiple
	hidden
	on:change={async () => {
		if (inputFiles && inputFiles.length > 0) {
			for (const file of inputFiles) {
				await uploadFileHandler(file);
			}

			inputFiles = null;
			const fileInputElement = document.getElementById('files-input');

			if (fileInputElement) {
				fileInputElement.value = '';
			}
		} else {
			toast.error($i18n.t(`File not found.`));
		}
	}}
/>

<div class="flex h-full min-h-0 w-full flex-col overflow-hidden" id="collection-container">
	{#if id && knowledge}
		<AccessControlModal
			bind:show={showAccessControlModal}
			bind:accessGrants={knowledge.access_grants}
			share={$user?.permissions?.sharing?.knowledge || $user?.role === 'admin'}
			sharePublic={$user?.permissions?.sharing?.public_knowledge || $user?.role === 'admin'}
			shareUsers={($user?.permissions?.access_grants?.allow_users ?? true) ||
				$user?.role === 'admin'}
			allowGroups={($user?.permissions?.access_grants?.allow_groups ?? true) ||
				$user?.role === 'admin'}
			onChange={async () => {
				try {
					await updateKnowledgeAccessGrants(localStorage.token, id, knowledge.access_grants ?? []);
					toast.success($i18n.t('Saved'));
				} catch (error) {
					toast.error(`${error}`);
				}
			}}
			accessRoles={['read', 'write']}
		/>
		<div class="flex min-h-7 shrink-0 items-center justify-between gap-2 pr-0.5">
			<button
				type="button"
				class="flex h-6 w-fit shrink-0 items-center gap-1 whitespace-nowrap rounded-md text-xs text-gray-400 hover:text-gray-700 dark:text-gray-600 dark:hover:text-gray-300"
				on:click={() => goto('/workspace/knowledge')}
				><ChevronLeft className="size-3" strokeWidth="2" />{$i18n.t('Back')}</button
			>
			<!-- Previous file count label: {$i18n.t('{{COUNT}} files')} -->
			{#if knowledge.write_access}<AccessButton
					on:click={() => (showAccessControlModal = true)}
				/>{:else}<span class="text-xs text-gray-500">{$i18n.t('Read Only')}</span>{/if}
		</div>
		<div class="shrink-0 px-1 pb-2.5">
			<input
				class="w-full bg-transparent text-sm outline-hidden"
				bind:value={knowledge.name}
				aria-label={$i18n.t('Knowledge Name')}
				placeholder={$i18n.t('Knowledge Name')}
				disabled={!knowledge.write_access}
				on:input={changeDebounceHandler}
			/>
			<div class="mt-0.5 flex min-w-0 items-center gap-2 text-xs text-gray-500">
				<input
					class="min-w-0 flex-1 bg-transparent outline-hidden"
					bind:value={knowledge.description}
					aria-label={$i18n.t('Knowledge Description')}
					placeholder={$i18n.t('Knowledge Description')}
					disabled={!knowledge.write_access}
					on:input={changeDebounceHandler}
				/>
				<button
					type="button"
					title={$i18n.t('Click to copy ID')}
					class="max-w-[40%] shrink-0 truncate font-mono"
					on:click={() => {
						copyToClipboard(id);
						toast.success($i18n.t('ID copied to clipboard'));
					}}>{id}</button
				>
			</div>
		</div>
		<div class="mb-2 min-h-0 flex-1">
			{#if isExternalKnowledge}<div
					class="h-full overflow-auto rounded-2xl border border-gray-100/80 dark:border-white/[0.04]"
				>
					<div class="p-5 flex flex-col gap-4">
						<div class="flex flex-wrap gap-2 text-xs">
							<div class="px-2 py-1 rounded-lg bg-gray-50 dark:bg-gray-850">
								{$i18n.t('Connected')}
							</div>
							<div class="px-2 py-1 rounded-lg bg-gray-50 dark:bg-gray-850">
								{$i18n.t('Read Only')}
							</div>
							<div class="px-2 py-1 rounded-lg bg-gray-50 dark:bg-gray-850">
								{knowledge?.meta?.external?.provider ?? $i18n.t('Provider')}
							</div>
							<div class="px-2 py-1 rounded-lg bg-gray-50 dark:bg-gray-850">
								{$i18n.t('Service Account')}
							</div>
						</div>

						<div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
							<div>
								<div class="text-xs text-gray-500 mb-1">{$i18n.t('Mapped Source')}</div>
								<div class="rounded-xl bg-gray-50 dark:bg-gray-850 px-3 py-2">
									{knowledge?.meta?.external?.source?.name ?? $i18n.t('Not configured')}
								</div>
							</div>
							<div>
								<div class="text-xs text-gray-500 mb-1">{$i18n.t('Auth Mode')}</div>
								<div class="rounded-xl bg-gray-50 dark:bg-gray-850 px-3 py-2">
									{$i18n.t('Admin-managed service account')}
								</div>
							</div>
						</div>

						<div class="text-xs text-gray-500">
							<!-- LICENSE covers this Open WebUI wordmark.
						Do not alter, remove, obscure, or replace it except as LICENSE permits:
						https://docs.openwebui.com/license. -->
							{$i18n.t(
								'This knowledge base retrieves from a connected source. Open WebUI can query it, but cannot upload, sync, edit, delete, reset, or reindex its source data.'
							)}
						</div>

						<div class="flex flex-col gap-2">
							<div class="text-xs">{$i18n.t('Test Query')}</div>
							<div class="flex gap-2">
								<input
									class="w-full text-xs rounded-xl bg-gray-50 dark:bg-gray-850 px-3 py-2 outline-hidden"
									bind:value={externalTestQuery}
									placeholder={$i18n.t('Ask this knowledge source a test question')}
								/>
								<button
									class="px-3 py-2 rounded-xl bg-black text-white dark:bg-white dark:text-black text-xs"
									on:click={externalTestHandler}
								>
									{$i18n.t('Test')}
								</button>
							</div>
						</div>

						{#if externalTestResult}
							<div class="rounded-xl bg-gray-50 dark:bg-gray-850 p-3 text-xs">
								<div class="mb-2">{$i18n.t('Preview')}</div>
								{#each externalTestResult.documents ?? [] as document, idx}
									<div class="border-t border-gray-100 dark:border-gray-800 py-2">
										<div class="line-clamp-4">{document}</div>
										<div class="text-gray-500 mt-1">
											{externalTestResult.metadatas?.[idx]?.source ?? ''}
										</div>
									</div>
								{/each}
							</div>
						{/if}
					</div>
				</div>{:else}
				<KnowledgeBrowser
					bind:this={browser}
					{knowledge}
					transfers={fileItems}
					{syncing}
					onUpload={requestUpload}
					onSync={async () => {
						pendingSyncFiles = await collectDirectoryFiles();
						if (pendingSyncFiles?.length) showSyncConfirmModal = true;
					}}
					onReset={() => (showResetConfirm = true)}
				/>
			{/if}
		</div>
	{:else}<Spinner className="size-5" />{/if}
</div>

<ConfirmDialog
	bind:show={showResetConfirm}
	title={$i18n.t('Reset knowledge base?')}
	on:confirm={async () => {
		await resetKnowledgeById(localStorage.token, id);
		browser?.clearRemovedSelection();
		toast.success($i18n.t('Knowledge base has been reset'));
		init();
	}}
>
	<div class="text-sm text-gray-700 dark:text-gray-300 flex-1 line-clamp-3">
		{$i18n.t(
			'This will remove all files and directories from this knowledge base. This action cannot be undone.'
		)}
	</div>
</ConfirmDialog>
