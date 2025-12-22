<script lang="ts">
	import Fuse from 'fuse.js';
	import { toast } from 'svelte-sonner';
	import { onMount, getContext, tick } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	const i18n: Writable<i18nType> = getContext('i18n');

	import { WEBUI_NAME, user } from '$lib/stores';
	import {
		getStores,
		createStore,
		deleteStore,
		uploadFileToStore,
		getStoreFiles,
		deleteCorpus,
		type GeminiRagStore
	} from '$lib/apis/gemini-rag';

	import DeleteConfirmDialog from '../common/ConfirmDialog.svelte';
	import Search from '../icons/Search.svelte';
	import Plus from '../icons/Plus.svelte';
	import Spinner from '../common/Spinner.svelte';
	import XMark from '../icons/XMark.svelte';
	import ChevronLeft from '../icons/ChevronLeft.svelte';

	import FolderItem from './OnlineKnowledge/FolderItem.svelte';
	import FileItem from './OnlineKnowledge/FileItem.svelte';
	import CreateFolderModal from './OnlineKnowledge/CreateFolderModal.svelte';
	import SortSelector from './OnlineKnowledge/SortSelector.svelte';
	import ViewToggle from './OnlineKnowledge/ViewToggle.svelte';
	import FilePreviewModal from './OnlineKnowledge/FilePreviewModal.svelte';

	// Types
	interface OnlineKnowledgeFolder {
		id: string;
		name: string;
		itemCount: number;
		totalSize: number;
		createdAt: number;
		updatedAt: number;
	}

	interface OnlineKnowledgeFile {
		id: string;
		folderId: string;
		name: string;
		size: number;
		type: string;
		content: string | null;
		createdAt: number;
	}

	type SortOption = 'name-asc' | 'name-desc' | 'date-desc' | 'date-asc' | 'size-desc' | 'size-asc';
	type ViewMode = 'list' | 'grid';

	// State
	let loaded = false;
	let loading = false;
	let query = '';
	let sortOption: SortOption = 'name-asc';
	let viewMode: ViewMode = 'list';
	let currentFolderId: string | null = null;
	let currentStoreName: string | null = null;

	let selectedItem: OnlineKnowledgeFolder | OnlineKnowledgeFile | null = null;
	let showDeleteConfirm = false;
	let showCreateFolderModal = false;
	let showFilePreviewModal = false;
	let previewFile: OnlineKnowledgeFile | null = null;
	let uploading = false;

	// Data from API
	let folders: OnlineKnowledgeFolder[] = [];
	let files: OnlineKnowledgeFile[] = [];

	// Extract store ID from full name (e.g., "fileSearchStores/xxx" -> "xxx")
	const extractStoreId = (fullName) => {
		return fullName.replace('fileSearchStores/', '');
	};

	// Load stores (folders) from API
	const loadStores = async () => {
		loading = true;
		try {
			const response = await getStores(localStorage.token);
			const stores = response?.stores;
			if (stores) {
				folders = stores.map((store: GeminiRagStore) => ({
					id: extractStoreId(store.name),
					name: store.display_name,
					itemCount: store.corpora_count || 0,
					totalSize: 0,
					createdAt: store.create_time ? new Date(store.create_time).getTime() : Date.now(),
					updatedAt: store.create_time ? new Date(store.create_time).getTime() : Date.now()
				}));
			}
		} catch (error) {
			toast.error($i18n.t('폴더 목록을 불러오는데 실패했습니다.'));
			console.error(error);
		} finally {
			loading = false;
		}
	};

	// Load files from a store
	const loadStoreFiles = async (storeName: string) => {
		loading = true;
		try {
			const response = await getStoreFiles(localStorage.token, storeName);
			const storeFiles = response?.files;
			if (storeFiles) {
				files = storeFiles.map((f) => ({
					id: f.name,
					folderId: storeName,
					name: f.display_name,
					size: parseInt(f.size_bytes || '0', 10),
					type: 'application/pdf',
					content: null,
					createdAt: f.create_time ? new Date(f.create_time).getTime() : Date.now()
				}));
			}
		} catch (error) {
			toast.error($i18n.t('파일 목록을 불러오는데 실패했습니다.'));
			console.error(error);
		} finally {
			loading = false;
		}
	};

	// Computed
	$: currentFolder = currentFolderId ? folders.find(f => f.id === currentFolderId) : null;
	$: currentFolderFiles = currentFolderId ? files.filter(f => f.folderId === currentFolderId) : [];

	let filteredFolders: OnlineKnowledgeFolder[] = [];
	let filteredFiles: OnlineKnowledgeFile[] = [];
	let folderFuse: Fuse<OnlineKnowledgeFolder> | null = null;
	let fileFuse: Fuse<OnlineKnowledgeFile> | null = null;

	// Fuse setup for folders
	const setupFolderFuse = async () => {
		folderFuse = new Fuse(folders, {
			keys: ['name'],
			threshold: 0.3
		});
		await tick();
		updateFilteredFolders();
	};

	// Fuse setup for files
	const setupFileFuse = async () => {
		fileFuse = new Fuse(currentFolderFiles, {
			keys: ['name'],
			threshold: 0.3
		});
		await tick();
		updateFilteredFiles();
	};

	$: if (folders) {
		setupFolderFuse();
	}

	$: if (currentFolderFiles) {
		setupFileFuse();
	}

	const updateFilteredFolders = () => {
		if (!folderFuse) {
			filteredFolders = folders;
			return;
		}
		let items = query ? folderFuse.search(query).map(result => result.item) : [...folders];
		filteredFolders = sortFolders(items, sortOption);
	};

	const updateFilteredFiles = () => {
		if (!fileFuse) {
			filteredFiles = currentFolderFiles;
			return;
		}
		let items = query ? fileFuse.search(query).map(result => result.item) : [...currentFolderFiles];
		filteredFiles = sortFiles(items, sortOption);
	};

	$: if (query !== undefined && (folderFuse || fileFuse)) {
		if (currentFolderId) {
			updateFilteredFiles();
		} else {
			updateFilteredFolders();
		}
	}

	$: if (sortOption) {
		if (currentFolderId) {
			updateFilteredFiles();
		} else {
			updateFilteredFolders();
		}
	}

	// Get current filtered items count
	$: filteredItemsCount = currentFolderId ? filteredFiles.length : filteredFolders.length;

	const sortFolders = (items: OnlineKnowledgeFolder[], option: SortOption): OnlineKnowledgeFolder[] => {
		return [...items].sort((a, b) => {
			switch (option) {
				case 'name-asc':
					return a.name.localeCompare(b.name);
				case 'name-desc':
					return b.name.localeCompare(a.name);
				case 'date-asc':
					return a.createdAt - b.createdAt;
				case 'date-desc':
					return b.createdAt - a.createdAt;
				case 'size-asc':
					return a.totalSize - b.totalSize;
				case 'size-desc':
					return b.totalSize - a.totalSize;
				default:
					return 0;
			}
		});
	};

	const sortFiles = (items: OnlineKnowledgeFile[], option: SortOption): OnlineKnowledgeFile[] => {
		return [...items].sort((a, b) => {
			switch (option) {
				case 'name-asc':
					return a.name.localeCompare(b.name);
				case 'name-desc':
					return b.name.localeCompare(a.name);
				case 'date-asc':
					return a.createdAt - b.createdAt;
				case 'date-desc':
					return b.createdAt - a.createdAt;
				case 'size-asc':
					return a.size - b.size;
				case 'size-desc':
					return b.size - a.size;
				default:
					return 0;
			}
		});
	};

	// Handlers
	const handleFolderClick = async (folder: OnlineKnowledgeFolder) => {
		currentFolderId = folder.id;
		currentStoreName = folder.id;
		query = '';
		await loadStoreFiles(folder.id);
	};

	const handleFileClick = (file: OnlineKnowledgeFile) => {
		previewFile = file;
		showFilePreviewModal = true;
	};

	const handleBack = () => {
		currentFolderId = null;
		currentStoreName = null;
		files = [];
		query = '';
	};

	const handleCreateFolder = async (name: string) => {
		try {
			const result = await createStore(localStorage.token, name);
			if (result) {
				await loadStores();
				showCreateFolderModal = false;
				toast.success($i18n.t('폴더가 생성되었습니다.'));
			}
		} catch (error) {
			toast.error($i18n.t('폴더 생성에 실패했습니다.'));
			console.error(error);
		}
	};

	const handleDeleteFolder = (folder: OnlineKnowledgeFolder) => {
		selectedItem = folder;
		showDeleteConfirm = true;
	};

	const handleDeleteFile = (file: OnlineKnowledgeFile) => {
		selectedItem = file;
		showDeleteConfirm = true;
	};

	const confirmDelete = async () => {
		if (!selectedItem) return;

		try {
			if ('folderId' in selectedItem) {
				// Delete file (corpus)
				await deleteCorpus(localStorage.token, selectedItem.id);
				files = files.filter(f => f.id !== selectedItem!.id);
				toast.success($i18n.t('파일이 삭제되었습니다.'));
			} else {
				// Delete folder (store)
				await deleteStore(localStorage.token, selectedItem.id);
				folders = folders.filter(f => f.id !== selectedItem!.id);
				toast.success($i18n.t('폴더가 삭제되었습니다.'));
			}
		} catch (error) {
			toast.error($i18n.t('삭제에 실패했습니다.'));
			console.error(error);
		}

		selectedItem = null;
		showDeleteConfirm = false;
	};

	const handleFileUpload = async (event: Event) => {
		const input = event.target as HTMLInputElement;
		if (!input.files?.length || !currentStoreName) return;

		const file = input.files[0];
		uploading = true;

		try {
			// pass file.name as displayName so server/client can preserve original filename
			const result = await uploadFileToStore(localStorage.token, currentStoreName, file, file.name);
			if (result) {
				await loadStoreFiles(currentStoreName);
				toast.success($i18n.t('파일이 업로드되었습니다.'));
			}
		} catch (error) {
			toast.error($i18n.t('파일 업로드에 실패했습니다.'));
			console.error(error);
		} finally {
			uploading = false;
			input.value = '';
		}
	};

	// Utility
	const formatFileSize = (bytes: number): string => {
		if (bytes === 0) return '0 B';
		const k = 1024;
		const sizes = ['B', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
	};

	onMount(async () => {
		await loadStores();
		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('온라인 지식기반')} • {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<DeleteConfirmDialog
		bind:show={showDeleteConfirm}
		on:confirm={confirmDelete}
	/>

	<CreateFolderModal
		bind:show={showCreateFolderModal}
		on:create={(e) => handleCreateFolder(e.detail)}
	/>

	{#if previewFile}
		<FilePreviewModal
			bind:show={showFilePreviewModal}
			file={previewFile}
			{formatFileSize}
		/>
	{/if}

	<div class="flex flex-col gap-1 px-1 mt-1.5 mb-3 text-gray-900 dark:text-gray-100">
		<div class="flex justify-between items-center">
			<div class="flex items-center md:self-center text-xl font-medium px-0.5 gap-1 shrink-0">
				{#if currentFolderId}
					<button
						class="hover:text-gray-600 dark:hover:text-gray-300 transition"
						on:click={handleBack}
					>
						{$i18n.t('온라인 지식기반')}
					</button>
					<span class="text-gray-400 dark:text-gray-600">/</span>
					<span>{currentFolder?.name}</span>
					<span class="text-gray-400 dark:text-gray-600">/</span>
					<span class="text-lg font-medium text-gray-500">{filteredItemsCount}</span>
				{:else}
					<span>{$i18n.t('온라인 지식기반')}</span>
					<span class="text-lg font-medium text-gray-500 ml-1">{filteredItemsCount}</span>
				{/if}
			</div>

			<div class="flex w-full justify-end gap-1.5">
				{#if currentFolderId}
					<label
						class="px-2 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black transition font-medium text-sm flex items-center cursor-pointer {uploading ? 'opacity-50 cursor-not-allowed' : ''}"
					>
						{#if uploading}
							<Spinner className="size-3" />
							<span class="hidden md:block md:ml-1 text-xs">{$i18n.t('업로드 중...')}</span>
						{:else}
							<Plus className="size-3" strokeWidth="2.5" />
							<span class="hidden md:block md:ml-1 text-xs">{$i18n.t('파일 업로드')}</span>
						{/if}
						<input
							type="file"
							class="hidden"
							accept=".pdf"
							disabled={uploading}
							on:change={handleFileUpload}
						/>
					</label>
				{:else}
					<button
						class="px-2 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black transition font-medium text-sm flex items-center"
						on:click={() => showCreateFolderModal = true}
					>
						<Plus className="size-3" strokeWidth="2.5" />
						<span class="hidden md:block md:ml-1 text-xs">{$i18n.t('새 폴더')}</span>
					</button>
				{/if}
			</div>
		</div>
	</div>

	<div class="py-2 bg-white dark:bg-gray-900 rounded-3xl border border-gray-100 dark:border-gray-850">
		<!-- Search -->
		<div class="flex w-full space-x-2 py-0.5 px-3.5 pb-2">
			<div class="flex flex-1">
				<div class="self-center ml-1 mr-3">
					<Search className="size-3.5" />
				</div>
				<input
					class="w-full text-sm py-1 rounded-r-xl outline-hidden bg-transparent"
					bind:value={query}
					placeholder={currentFolderId ? $i18n.t('파일 검색') : $i18n.t('폴더 검색')}
				/>
				{#if query}
					<div class="self-center pl-1.5 translate-y-[0.5px] rounded-l-xl bg-transparent">
						<button
							class="p-0.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
							on:click={() => { query = ''; }}
						>
							<XMark className="size-3" strokeWidth="2" />
						</button>
					</div>
				{/if}
			</div>
		</div>

		<!-- Sort and View Options -->
		<div class="px-3 flex w-full justify-between items-center pb-2">
			<SortSelector bind:value={sortOption} />
			<ViewToggle bind:value={viewMode} />
		</div>

		<!-- Content -->
		{#if loading}
			<div class="w-full h-full flex justify-center items-center my-16 mb-24">
				<Spinner className="size-5" />
			</div>
		{:else if filteredItemsCount > 0}
			<div class="my-2 px-3 {viewMode === 'grid' ? 'grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3' : 'flex flex-col gap-1'}">
				{#if currentFolderId}
					{#each filteredFiles as file (file.id)}
						<FileItem
							{file}
							{viewMode}
							{formatFileSize}
							on:click={() => handleFileClick(file)}
							on:delete={() => handleDeleteFile(file)}
						/>
					{/each}
				{:else}
					{#each filteredFolders as folder (folder.id)}
						<FolderItem
							{folder}
							{viewMode}
							{formatFileSize}
							on:click={() => handleFolderClick(folder)}
							on:delete={() => handleDeleteFolder(folder)}
						/>
					{/each}
				{/if}
			</div>
		{:else}
			<div class="w-full h-full flex flex-col justify-center items-center my-16 mb-24">
				<div class="max-w-md text-center">
					<div class="text-3xl mb-3">📁</div>
					<div class="text-lg font-medium mb-1 dark:text-white">
						{currentFolderId ? $i18n.t('파일이 없습니다') : $i18n.t('폴더가 없습니다')}
					</div>
					<div class="text-gray-500 text-center text-xs">
						{currentFolderId
							? $i18n.t('이 폴더에 파일을 업로드해 보세요.')
							: $i18n.t('새 폴더를 만들어 파일을 관리해 보세요.')}
					</div>
				</div>
			</div>
		{/if}
	</div>
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner className="size-5" />
	</div>
{/if}
