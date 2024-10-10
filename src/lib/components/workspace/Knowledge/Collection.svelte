<script lang="ts">
	import Fuse from 'fuse.js';
	import { toast } from 'svelte-sonner';

	import { onMount, getContext, onDestroy, tick } from 'svelte';
	const i18n = getContext('i18n');

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { mobile, showSidebar, knowledge as _knowledge } from '$lib/stores';

	import { updateFileDataContentById, uploadFile } from '$lib/apis/files';
	import {
		addFileToKnowledgeById,
		getKnowledgeById,
		getKnowledgeItems,
		removeFileFromKnowledgeById,
		resetKnowledgeById,
		updateFileFromKnowledgeById,
		updateKnowledgeById
	} from '$lib/apis/knowledge';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import Files from './Collection/Files.svelte';
	import AddFilesPlaceholder from '$lib/components/AddFilesPlaceholder.svelte';
	import AddContentModal from './Collection/AddTextContentModal.svelte';
	import { transcribeAudio } from '$lib/apis/audio';
	import { blobToFile } from '$lib/utils';
	import { processFile } from '$lib/apis/retrieval';
	import AddContentMenu from './Collection/AddContentMenu.svelte';
	import AddTextContentModal from './Collection/AddTextContentModal.svelte';

	import SyncConfirmDialog from '../../common/ConfirmDialog.svelte';

	let largeScreen = true;

	type Knowledge = {
		id: string;
		name: string;
		description: string;
		data: {
			file_ids: string[];
		};
		files: any[];
	};

	let id = null;
	let knowledge: Knowledge | null = null;
	let query = '';

	let showAddTextContentModal = false;
	let showSyncConfirmModal = false;

	let inputFiles = null;

	let filteredItems = [];
	$: if (knowledge) {
		fuse = new Fuse(knowledge.files, {
			keys: ['meta.name', 'meta.description']
		});
	}

	$: if (fuse) {
		filteredItems = query
			? fuse.search(query).map((e) => {
					return e.item;
				})
			: (knowledge?.files ?? []);
	}

	let selectedFile = null;
	let selectedFileId = null;

	$: if (selectedFileId) {
		const file = (knowledge?.files ?? []).find((file) => file.id === selectedFileId);
		if (file) {
			file.data = file.data ?? { content: '' };
			selectedFile = file;
		} else {
			selectedFile = null;
		}
	} else {
		selectedFile = null;
	}

	let fuse = null;
	let debounceTimeout = null;
	let mediaQuery;
	let dragged = false;

	const createFileFromText = (name, content) => {
		const blob = new Blob([content], { type: 'text/plain' });
		const file = blobToFile(blob, `${name}.md`);

		console.log(file);
		return file;
	};

	const uploadFileHandler = async (file) => {
		console.log(file);

		const fileItem = {
			type: 'file',
			file: '',
			id: null,
			url: '',
			name: file.name,
			size: file.size,
			status: 'uploading',
			error: ''
		};

		knowledge.files = [...(knowledge.files ?? []), fileItem];

		// Check if the file is an audio file and transcribe/convert it to text file
		if (['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/x-m4a'].includes(file['type'])) {
			const res = await transcribeAudio(localStorage.token, file).catch((error) => {
				toast.error(error);
				return null;
			});

			if (res) {
				console.log(res);
				const blob = new Blob([res.text], { type: 'text/plain' });
				file = blobToFile(blob, `${file.name}.txt`);
			}
		}

		try {
			const uploadedFile = await uploadFile(localStorage.token, file).catch((e) => {
				toast.error(e);
			});

			if (uploadedFile) {
				console.log(uploadedFile);
				await addFileHandler(uploadedFile.id);
			} else {
				toast.error($i18n.t('Failed to upload file.'));
			}
		} catch (e) {
			toast.error(e);
		}
	};

	const uploadDirectoryHandler = async () => {
		// Check if File System Access API is supported
		const isFileSystemAccessSupported = 'showDirectoryPicker' in window;

		try {
			if (isFileSystemAccessSupported) {
				// Modern browsers (Chrome, Edge) implementation
				await handleModernBrowserUpload();
			} else {
				// Firefox fallback
				await handleFirefoxUpload();
			}
		} catch (error) {
			handleUploadError(error);
		}
	};

	// Helper function to check if a path contains hidden folders
	const hasHiddenFolder = (path) => {
		return path.split('/').some((part) => part.startsWith('.'));
	};

	// Modern browsers implementation using File System Access API
	const handleModernBrowserUpload = async () => {
		const dirHandle = await window.showDirectoryPicker();
		let totalFiles = 0;
		let uploadedFiles = 0;

		// Function to update the UI with the progress
		const updateProgress = () => {
			const percentage = (uploadedFiles / totalFiles) * 100;
			toast.info(`Upload Progress: ${uploadedFiles}/${totalFiles} (${percentage.toFixed(2)}%)`);
		};

		// Recursive function to count all files excluding hidden ones
		async function countFiles(dirHandle) {
			for await (const entry of dirHandle.values()) {
				// Skip hidden files and directories
				if (entry.name.startsWith('.')) continue;

				if (entry.kind === 'file') {
					totalFiles++;
				} else if (entry.kind === 'directory') {
					// Only process non-hidden directories
					if (!entry.name.startsWith('.')) {
						await countFiles(entry);
					}
				}
			}
		}

		// Recursive function to process directories excluding hidden files and folders
		async function processDirectory(dirHandle, path = '') {
			for await (const entry of dirHandle.values()) {
				// Skip hidden files and directories
				if (entry.name.startsWith('.')) continue;

				const entryPath = path ? `${path}/${entry.name}` : entry.name;

				// Skip if the path contains any hidden folders
				if (hasHiddenFolder(entryPath)) continue;

				if (entry.kind === 'file') {
					const file = await entry.getFile();
					const fileWithPath = new File([file], entryPath, { type: file.type });

					await uploadFileHandler(fileWithPath);
					uploadedFiles++;
					updateProgress();
				} else if (entry.kind === 'directory') {
					// Only process non-hidden directories
					if (!entry.name.startsWith('.')) {
						await processDirectory(entry, entryPath);
					}
				}
			}
		}

		await countFiles(dirHandle);
		updateProgress();

		if (totalFiles > 0) {
			await processDirectory(dirHandle);
		} else {
			console.log('No files to upload.');
		}
	};

	// Firefox fallback implementation using traditional file input
	const handleFirefoxUpload = async () => {
		return new Promise((resolve, reject) => {
			// Create hidden file input
			const input = document.createElement('input');
			input.type = 'file';
			input.webkitdirectory = true;
			input.directory = true;
			input.multiple = true;
			input.style.display = 'none';

			// Add input to DOM temporarily
			document.body.appendChild(input);

			input.onchange = async () => {
				try {
					const files = Array.from(input.files)
						// Filter out files from hidden folders
						.filter((file) => !hasHiddenFolder(file.webkitRelativePath));

					let totalFiles = files.length;
					let uploadedFiles = 0;

					// Function to update the UI with the progress
					const updateProgress = () => {
						const percentage = (uploadedFiles / totalFiles) * 100;
						toast.info(
							`Upload Progress: ${uploadedFiles}/${totalFiles} (${percentage.toFixed(2)}%)`
						);
					};

					updateProgress();

					// Process all files
					for (const file of files) {
						// Skip hidden files (additional check)
						if (!file.name.startsWith('.')) {
							const relativePath = file.webkitRelativePath || file.name;
							const fileWithPath = new File([file], relativePath, { type: file.type });

							await uploadFileHandler(fileWithPath);
							uploadedFiles++;
							updateProgress();
						}
					}

					// Clean up
					document.body.removeChild(input);
					resolve();
				} catch (error) {
					reject(error);
				}
			};

			input.onerror = (error) => {
				document.body.removeChild(input);
				reject(error);
			};

			// Trigger file picker
			input.click();
		});
	};

	// Error handler
	const handleUploadError = (error) => {
		if (error.name === 'AbortError') {
			toast.info('Directory selection was cancelled');
		} else {
			toast.error('Error accessing directory');
			console.error('Directory access error:', error);
		}
	};

	// Helper function to maintain file paths within zip
	const syncDirectoryHandler = async () => {
		if ((knowledge?.files ?? []).length > 0) {
			const res = await resetKnowledgeById(localStorage.token, id).catch((e) => {
				toast.error(e);
			});

			if (res) {
				knowledge = res;
				toast.success($i18n.t('Knowledge reset successfully.'));

				// Upload directory
				uploadDirectoryHandler();
			}
		} else {
			uploadDirectoryHandler();
		}
	};

	const addFileHandler = async (fileId) => {
		const updatedKnowledge = await addFileToKnowledgeById(localStorage.token, id, fileId).catch(
			(e) => {
				toast.error(e);
			}
		);

		if (updatedKnowledge) {
			knowledge = updatedKnowledge;
			toast.success($i18n.t('File added successfully.'));
		}
	};

	const deleteFileHandler = async (fileId) => {
		const updatedKnowledge = await removeFileFromKnowledgeById(
			localStorage.token,
			id,
			fileId
		).catch((e) => {
			toast.error(e);
		});

		if (updatedKnowledge) {
			knowledge = updatedKnowledge;
			toast.success($i18n.t('File removed successfully.'));
		}
	};

	const updateFileContentHandler = async () => {
		const fileId = selectedFile.id;
		const content = selectedFile.data.content;

		const res = updateFileDataContentById(localStorage.token, fileId, content).catch((e) => {
			toast.error(e);
		});

		const updatedKnowledge = await updateFileFromKnowledgeById(
			localStorage.token,
			id,
			fileId
		).catch((e) => {
			toast.error(e);
		});

		if (res && updatedKnowledge) {
			knowledge = updatedKnowledge;
			toast.success($i18n.t('File content updated successfully.'));
		}
	};

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
				name: knowledge.name,
				description: knowledge.description
			}).catch((e) => {
				toast.error(e);
			});

			if (res) {
				toast.success($i18n.t('Knowledge updated successfully'));
				_knowledge.set(await getKnowledgeItems(localStorage.token));
			}
		}, 1000);
	};

	const handleMediaQuery = async (e) => {
		if (e.matches) {
			largeScreen = true;
		} else {
			largeScreen = false;
		}
	};

	const onDragOver = (e) => {
		e.preventDefault();
		dragged = true;
	};

	const onDragLeave = () => {
		dragged = false;
	};

	const onDrop = async (e) => {
		e.preventDefault();
		dragged = false;

		if (e.dataTransfer?.files) {
			const inputFiles = e.dataTransfer?.files;

			if (inputFiles && inputFiles.length > 0) {
				for (const file of inputFiles) {
					await uploadFileHandler(file);
				}
			} else {
				toast.error($i18n.t(`File not found.`));
			}
		}
	};

	onMount(async () => {
		// listen to resize 1024px
		mediaQuery = window.matchMedia('(min-width: 1024px)');

		mediaQuery.addEventListener('change', handleMediaQuery);
		handleMediaQuery(mediaQuery);

		id = $page.params.id;

		const res = await getKnowledgeById(localStorage.token, id).catch((e) => {
			toast.error(e);
			return null;
		});

		if (res) {
			knowledge = res;
		} else {
			goto('/workspace/knowledge');
		}

		const dropZone = document.querySelector('body');
		dropZone?.addEventListener('dragover', onDragOver);
		dropZone?.addEventListener('drop', onDrop);
		dropZone?.addEventListener('dragleave', onDragLeave);
	});

	onDestroy(() => {
		mediaQuery?.removeEventListener('change', handleMediaQuery);
		const dropZone = document.querySelector('body');
		dropZone?.removeEventListener('dragover', onDragOver);
		dropZone?.removeEventListener('drop', onDrop);
		dropZone?.removeEventListener('dragleave', onDragLeave);
	});
</script>

{#if dragged}
	<div
		class="fixed {$showSidebar
			? 'left-0 md:left-[260px] md:w-[calc(100%-260px)]'
			: 'left-0'}  w-full h-full flex z-50 touch-none pointer-events-none"
		id="dropzone"
		role="region"
		aria-label="Drag and Drop Container"
	>
		<div class="absolute w-full h-full backdrop-blur bg-gray-800/40 flex justify-center">
			<div class="m-auto pt-64 flex flex-col justify-center">
				<div class="max-w-md">
					<AddFilesPlaceholder>
						<div class=" mt-2 text-center text-sm dark:text-gray-200 w-full">
							Drop any files here to add to my documents
						</div>
					</AddFilesPlaceholder>
				</div>
			</div>
		</div>
	</div>
{/if}

<SyncConfirmDialog
	bind:show={showSyncConfirmModal}
	message={$i18n.t(
		'This will reset the knowledge base and sync all files. Do you wish to continue?'
	)}
	on:confirm={() => {
		syncDirectoryHandler();
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
	on:change={() => {
		if (inputFiles && inputFiles.length > 0) {
			for (const file of inputFiles) {
				uploadFileHandler(file);
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

<div class="flex flex-col w-full max-h-[100dvh] h-full">
	<button
		class="flex space-x-1 w-fit"
		on:click={() => {
			goto('/workspace/knowledge');
		}}
	>
		<div class=" self-center">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="w-4 h-4"
			>
				<path
					fill-rule="evenodd"
					d="M17 10a.75.75 0 01-.75.75H5.612l4.158 3.96a.75.75 0 11-1.04 1.08l-5.5-5.25a.75.75 0 010-1.08l5.5-5.25a.75.75 0 111.04 1.08L5.612 9.25H16.25A.75.75 0 0117 10z"
					clip-rule="evenodd"
				/>
			</svg>
		</div>
		<div class=" self-center font-medium text-sm">{$i18n.t('Back')}</div>
	</button>

	<div class="flex flex-col my-2 flex-1 overflow-auto h-0">
		{#if id && knowledge}
			<div class=" flex w-full mt-1 mb-3.5">
				<div class="flex-1">
					<div class="flex items-center justify-between w-full px-0.5 mb-1">
						<div class="w-full">
							<input
								type="text"
								class="w-full font-medium text-2xl font-primary bg-transparent outline-none"
								bind:value={knowledge.name}
								on:input={() => {
									changeDebounceHandler();
								}}
							/>
						</div>

						<div class=" flex-shrink-0">
							<div>
								<Badge type="success" content="Collection" />
							</div>
						</div>
					</div>

					<div class="flex w-full px-1">
						<input
							type="text"
							class="w-full text-gray-500 text-sm bg-transparent outline-none"
							bind:value={knowledge.description}
							on:input={() => {
								changeDebounceHandler();
							}}
						/>
					</div>
				</div>
			</div>

			<div class="flex flex-row h-0 flex-1 overflow-auto">
				<div
					class=" {largeScreen
						? 'flex-shrink-0'
						: 'flex-1'} flex py-2.5 w-80 rounded-2xl border border-gray-50 dark:border-gray-850"
				>
					<div class=" flex flex-col w-full space-x-2 rounded-lg h-full">
						<div class="w-full h-full flex flex-col">
							<div class=" px-3">
								<div class="flex">
									<div class=" self-center ml-1 mr-3">
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 20 20"
											fill="currentColor"
											class="w-4 h-4"
										>
											<path
												fill-rule="evenodd"
												d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
												clip-rule="evenodd"
											/>
										</svg>
									</div>
									<input
										class=" w-full text-sm pr-4 py-1 rounded-r-xl outline-none bg-transparent"
										bind:value={query}
										placeholder={$i18n.t('Search Collection')}
									/>

									<div>
										<AddContentMenu
											on:upload={(e) => {
												if (e.detail.type === 'directory') {
													uploadDirectoryHandler();
												} else if (e.detail.type === 'text') {
													showAddTextContentModal = true;
												} else {
													document.getElementById('files-input').click();
												}
											}}
											on:sync={(e) => {
												showSyncConfirmModal = true;
											}}
										/>
									</div>
								</div>

								<hr class=" mt-2 mb-1 border-gray-50 dark:border-gray-850" />
							</div>

							{#if filteredItems.length > 0}
								<div class=" flex overflow-y-auto h-full w-full scrollbar-hidden text-xs">
									<Files
										files={filteredItems}
										{selectedFileId}
										on:click={(e) => {
											selectedFileId = e.detail;
										}}
										on:delete={(e) => {
											console.log(e.detail);

											selectedFileId = null;
											deleteFileHandler(e.detail);
										}}
									/>
								</div>
							{:else}
								<div class="m-auto text-gray-500 text-xs">No content found</div>
							{/if}
						</div>
					</div>
				</div>

				{#if largeScreen}
					<div class="flex-1 flex justify-start max-h-full overflow-hidden pl-3">
						{#if selectedFile}
							<div class=" flex flex-col w-full h-full">
								<div class=" flex-shrink-0 mb-2 flex items-center">
									<div class=" flex-1 text-xl line-clamp-1">
										{selectedFile?.meta?.name}
									</div>

									<div>
										<button
											class="self-center w-fit text-sm py-1 px-2.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-lg"
											on:click={() => {
												updateFileContentHandler();
											}}
										>
											{$i18n.t('Save')}
										</button>
									</div>
								</div>

								<div class=" flex-grow">
									<textarea
										class=" w-full h-full resize-none rounded-xl py-4 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
										bind:value={selectedFile.data.content}
										placeholder={$i18n.t('Add content here')}
									/>
								</div>
							</div>
						{:else}
							<div class="m-auto">
								<AddFilesPlaceholder title={$i18n.t('Select/Add Files')}>
									<div class=" mt-2 text-center text-sm dark:text-gray-200 w-full">
										Select a file to view or drag and drop a file to upload
									</div>
								</AddFilesPlaceholder>
							</div>
						{/if}
					</div>
				{/if}
			</div>
		{:else}
			<Spinner />
		{/if}
	</div>
</div>
