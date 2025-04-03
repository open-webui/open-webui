<script lang="ts">
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;
	import JSZip from 'jszip';

	import { chats, user, settings, scrollPaginationEnabled, currentChatPage } from '$lib/stores';

	import {
		archiveAllChats,
		createNewChat,
		deleteAllChats,
		getAllChats,
		// getAllUserChats, // This seems unused, potentially removable
		getChatList
	} from '$lib/apis/chats';
	import { getImportOrigin, convertOpenAIChats } from '$lib/utils';
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import ArchivedChatsModal from '$lib/components/layout/Sidebar/ArchivedChatsModal.svelte';

	const i18n = getContext('i18n');

	export let saveSettings: Function; // Assuming this is used elsewhere

	// State Variables
	let importJsonFiles: FileList | null = null;
	let importZipFiles: FileList | null = null;

	let showArchiveConfirm = false;
	let showDeleteConfirm = false;
	let showArchivedChatsModal = false;

	// Refined state flags for clarity (Point 7)
	let isImportingJson = false;
	let isImportingZip = false;
	let isExportingJson = false;
	let isExportingZip = false; // Renamed from isExporting

	let chatImportJsonInputElement: HTMLInputElement;
	let chatImportZipInputElement: HTMLInputElement;

	// Computed state for disabling buttons during any operation (Point 8)
	$: isAnyOperationInProgress =
		isImportingJson || isImportingZip || isExportingJson || isExportingZip;

	// Reactive triggers for file inputs
	$: if (importJsonFiles) {
		handleImportJson(importJsonFiles);
		// Reset input immediately after triggering handler (Point 11)
		if (chatImportJsonInputElement) chatImportJsonInputElement.value = '';
		importJsonFiles = null;
	}

	$: if (importZipFiles) {
		handleImportZipFileSelect(importZipFiles);
		// Reset input immediately after triggering handler (Point 11)
		if (chatImportZipInputElement) chatImportZipInputElement.value = '';
		importZipFiles = null;
	}

	// Helper Functions (Point 13)
	const readFileAsText = (file: File): Promise<string> => {
		return new Promise((resolve, reject) => {
			const reader = new FileReader();
			reader.onload = (event) => {
				if (event.target?.result && typeof event.target.result === 'string') {
					resolve(event.target.result);
				} else {
					reject(new Error($i18n.t('File content could not be read as text.')));
				}
			};
			reader.onerror = (error) => {
				console.error('File reading error:', error);
				reject(new Error($i18n.t('Failed to read file.')));
			};
			reader.readAsText(file);
		});
	};

	const importChats = async (chatsToImport: any[]) => {
		// Ensure we handle both single chat objects and arrays correctly within the batch
		const validChats = (Array.isArray(chatsToImport) ? chatsToImport : [chatsToImport]).filter(
			(c) => c !== null
		);

		if (validChats.length === 0) return; // Nothing to import in this batch

		// Assuming createNewChat can handle the structure (either chat object directly or { chat: chatObject })
		// Modify this part if createNewChat expects a specific format only
		for (const chat of validChats) {
			// Check if the chat data is nested under a 'chat' key or is the root object
			const chatData = chat.chat && typeof chat.chat === 'object' ? chat.chat : chat;
			// Basic check for some content, adjust as needed
			if (chatData && (chatData.id || chatData.title || chatData.messages?.length > 0)) {
				await createNewChat(localStorage.token, chatData);
			} else {
				console.warn('Skipping potentially empty or invalid chat object during import:', chat);
			}
		}

		// Refresh chat list after importing all chats in the batch/file
		currentChatPage.set(1);
		await chats.set(await getChatList(localStorage.token, 1)); // Use page 1 explicitly
		scrollPaginationEnabled.set(true);
	};

	// Standardized Error Message Formatting (Point 12 applied throughout)
	const formatError = (prefixKey: string, err: any): string => {
		const prefix = $i18n.t(prefixKey);
		const message = err?.message || (typeof err === 'string' ? err : JSON.stringify(err));
		return `${prefix} ${message}`;
	};

	// 1. handleImportJson (Refactored from handleImport/importJsonFile) (Point 1)
	const handleImportJson = async (files: FileList) => {
		if (files.length === 0) return;
		const file = files[0];

		// Basic check before starting the promise
		if (!file.name.toLowerCase().endsWith('.json')) {
			toast.error($i18n.t('Invalid file type. Please select a .json file.'));
			return;
		}

		if (isAnyOperationInProgress) {
			toast.error($i18n.t('Another operation is already in progress.'));
			return;
		}

		isImportingJson = true;

		const importPromise = async () => {
			// Read file content using helper
			const fileContent = await readFileAsText(file);
			const parsedData = JSON.parse(fileContent); // JSON parsing errors will reject the promise

			let chatsToImport: any[] = [];
			let origin = 'unknown';

			try {
				origin = getImportOrigin(parsedData);
			} catch (error) {
				console.warn(
					`Could not determine import origin for ${file.name}, assuming standard format. Error: ${error?.message}`
				);
				// Proceed with standard/unknown logic
			}

			if (origin === 'openai') {
				// Show converting message temporarily? toast.promise only has one loading state.
				// We can include conversion in the main promise logic.
				try {
					chatsToImport = convertOpenAIChats(parsedData);
				} catch (conversionError) {
					console.error('OpenAI conversion failed:', conversionError);
					// Throw specific error to be caught by toast.promise error handler
					throw new Error(formatError('Failed to convert OpenAI chats:', conversionError));
				}
			} else {
				// Handle standard format (single chat object or array of chats)
				if (typeof parsedData === 'object' && parsedData !== null) {
					chatsToImport = Array.isArray(parsedData) ? parsedData : [parsedData];
				} else {
					throw new Error($i18n.t('Parsed JSON data is not a valid object or array.'));
				}
			}

			// Filter out potentially null/invalid entries before counting/importing
			// This check might be redundant if importChats also filters, but good for early feedback
			const validChatsToImport = chatsToImport.filter((chat) => chat && typeof chat === 'object');

			if (validChatsToImport.length === 0) {
				// Resolve with 0 to indicate success but no chats imported.
				// This allows the success handler to provide a specific message.
				return 0;
			}

			// Perform the actual import (API calls + list refresh)
			await importChats(validChatsToImport);

			// Resolve the promise with the count of successfully processed chats
			return validChatsToImport.length;
		};

		toast.promise(importPromise(), {
			loading: $i18n.t('Importing chats from JSON...'),
			success: (count) => {
				isImportingJson = false; // Reset flag on success
				if (count === 0) {
					return $i18n.t('No valid chats found in the file.');
				}
				return `${$i18n.t('Successfully imported')} ${count} ${$i18n.t(count > 1 ? 'chats' : 'chat')}`;
			},
			error: (err) => {
				isImportingJson = false; // Reset flag on error
				console.error('JSON Import error:', err);
				// If the error was thrown by us (e.g., conversion), it's already formatted.
				// Otherwise, format it. Check if it's an error object first.
				if (err instanceof Error && err.message.startsWith($i18n.t('Failed to'))) {
					return err.message;
				}
				return formatError('Failed to import JSON:', err);
			}
			// No finally callback in svelte-sonner's promise type, reset flags in success/error
		});
	};

	// Wrapper function triggered by file input change for ZIP
	const handleImportZipFileSelect = async (files: FileList) => {
		if (files.length === 0) return;
		const file = files[0];

		// Basic check
		if (!file.name.toLowerCase().endsWith('.zip')) {
			toast.error($i18n.t('Invalid file type. Please select a .zip file.'));
			return;
		}

		if (isAnyOperationInProgress) {
			toast.error($i18n.t('Another operation is already in progress.'));
			return;
		}

		// Call the main ZIP import logic
		await handleImportZip(file);
	};

	// 2. handleImportZip (Refactored from importZipChats) (Point 2)
	const handleImportZip = async (zipFile: File) => {
		isImportingZip = true;
		let toastId = toast.loading($i18n.t('Processing ZIP file...')); // Initial toast

		try {
			const zip = await JSZip.loadAsync(zipFile);
			const chatFiles: JSZip.JSZipObject[] = [];
			const chatsFolder = zip.folder('chats'); // Use optional chaining (Point 2)

			if (!chatsFolder) {
				throw new Error($i18n.t('No "chats" folder found in the ZIP archive.'));
			}

			// Iterate safely over files within the 'chats' folder
			chatsFolder.forEach((relativePath, file) => {
				// Ensure it's a file directly within 'chats' and ends with .json
				if (!file.dir && relativePath.endsWith('.json') && !relativePath.includes('/')) {
					chatFiles.push(file);
				}
			});

			if (chatFiles.length === 0) {
				// Update toast to show info/error
				toast.info($i18n.t('No valid .json chat files found directly in the /chats folder.'), {
					id: toastId
				});
				isImportingZip = false; // Reset flag
				return; // Exit early
			}

			toast.info(
				`${$i18n.t('Found')} ${chatFiles.length} ${$i18n.t('potential chat files. Starting import...')}`,
				{ id: toastId }
			);
			// Update to a new loading toast for progress tracking
			toastId = toast.loading(`${$i18n.t('Import Progress:')} 0%`);

			// Process files in batches
			const BATCH_SIZE = 25; // Adjusted batch size
			const totalBatches = Math.ceil(chatFiles.length / BATCH_SIZE);
			let totalImportedCount = 0;
			let totalSkippedCount = 0;

			for (let i = 0; i < totalBatches; i++) {
				const start = i * BATCH_SIZE;
				const end = Math.min(start + BATCH_SIZE, chatFiles.length);
				const batchFiles = chatFiles.slice(start, end);
				const currentBatchNum = i + 1;

				// Update progress toast before processing batch
				const progressPercent = Math.round((i / totalBatches) * 100); // Progress before batch starts
				toast.loading(
					`${$i18n.t('Import Progress:')} ${progressPercent}% (${$i18n.t('Batch')} ${currentBatchNum}/${totalBatches})`,
					{ id: toastId }
				);

				const batchParsePromises = batchFiles.map(async (file) => {
					try {
						const content = await file.async('text');
						const chatData = JSON.parse(content);
						// Add basic validation if needed, e.g., check for essential fields
						// Let importChats handle deeper validation for now
						return chatData;
					} catch (e) {
						console.error(`Error processing file ${file.name}:`, e);
						// Provide specific feedback about skipped file (Point 2)
						toast.warning(`${$i18n.t('Skipped invalid JSON file:')} ${file.name}`);
						totalSkippedCount++;
						return null; // Indicate failure for this file
					}
				});

				const parsedChatsInBatch = await Promise.all(batchParsePromises);
				const validChatsInBatch = parsedChatsInBatch.filter((chat) => chat !== null);

				if (validChatsInBatch.length > 0) {
					// Import the valid chats from this batch
					// Note: importChats now handles the list refresh internally
					await importChats(validChatsInBatch);
					totalImportedCount += validChatsInBatch.length;
				}

				// Optional: Yield to event loop for large imports
				if (totalBatches > 5) {
					await new Promise((resolve) => setTimeout(resolve, 0));
				}
			}

			// Final progress update before success message
			toast.loading(`${$i18n.t('Import Progress:')} 100% - ${$i18n.t('Finalizing...')}`, {
				id: toastId
			});

			// Final toast update: Success
			let successMessage = `${$i18n.t('Successfully imported')} ${totalImportedCount} ${$i18n.t(totalImportedCount !== 1 ? 'chats' : 'chat')}.`;
			if (totalSkippedCount > 0) {
				successMessage += ` ${$i18n.t('Skipped')} ${totalSkippedCount} ${$i18n.t(totalSkippedCount !== 1 ? 'files' : 'file')}.`;
			}
			toast.success(successMessage, { id: toastId });
		} catch (error) {
			console.error('ZIP Import Error:', error);
			// Update toast to error, replacing the loading one
			toast.error(formatError('Failed to import ZIP:', error), { id: toastId });
		} finally {
			isImportingZip = false; // Reset flag regardless of outcome
		}
	};

	// 3. exportChats (JSON) (Point 3)
	const exportChats = async () => {
		if (isAnyOperationInProgress) {
			toast.error($i18n.t('Another operation is already in progress.'));
			return;
		}
		isExportingJson = true;
		const fetchToastId = toast.loading($i18n.t('Fetching chats...')); // Initial fetch toast

		try {
			const allChats = await getAllChats(localStorage.token);

			if (!allChats || allChats.length === 0) {
				toast.info($i18n.t('No chats found to export.'), { id: fetchToastId });
				isExportingJson = false; // Reset flag
				return; // Exit early
			}

			// Dismiss fetch toast, proceed with export promise
			toast.dismiss(fetchToastId);

			const exportPromise = new Promise((resolve, reject) => {
				try {
					const blob = new Blob([JSON.stringify(allChats, null, 2)], {
						type: 'application/json;charset=utf-8'
					});
					saveAs(blob, `chats-export-${Date.now()}.json`);
					resolve(allChats.length); // Resolve with the count
				} catch (err) {
					reject(err);
				}
			});

			toast.promise(exportPromise, {
				loading: $i18n.t('Saving JSON file...'),
				success: (count) => {
					isExportingJson = false; // Reset flag on success
					return `${$i18n.t('Successfully exported')} ${count} ${$i18n.t(count !== 1 ? 'chats' : 'chat')}`;
				},
				error: (err) => {
					isExportingJson = false; // Reset flag on error
					console.error('JSON Export error:', err);
					return formatError('Failed to save JSON file:', err);
				}
			});
		} catch (fetchError) {
			console.error('Failed to fetch chats for export:', fetchError);
			toast.error(formatError('Failed to fetch chats:', fetchError), { id: fetchToastId });
			isExportingJson = false; // Reset flag on fetch error
		}
		// Note: isExportingJson is reset within success/error handlers or early exits.
	};

	// 4. exportChatsAsZip (Point 4)
	const exportChatsAsZip = async () => {
		if (isAnyOperationInProgress) {
			toast.error($i18n.t('Another operation is already in progress.'));
			return;
		}
		isExportingZip = true;
		let toastId = toast.loading($i18n.t('Fetching chats...')); // Start with fetching state

		try {
			const allChats = await getAllChats(localStorage.token);

			if (!allChats || allChats.length === 0) {
				// Update the existing toast to info and exit (Point 4)
				toast.info($i18n.t('No chats found to export.'), { id: toastId });
				isExportingZip = false; // Reset flag early
				return;
			}

			// Update toast: Found chats, starting ZIP process
			toast.loading(
				`${$i18n.t('Found')} ${allChats.length} ${$i18n.t('chats. Preparing ZIP...')}`,
				{ id: toastId }
			);

			const zip = new JSZip();
			const chatsFolder = zip.folder('chats'); // Required by import format

			if (!chatsFolder) {
				// This should not happen with jszip, but good practice to check
				throw new Error("Failed to create 'chats' folder in ZIP.");
			}

			// Process in batches for progress updates
			const BATCH_SIZE = 50;
			const totalBatches = Math.ceil(allChats.length / BATCH_SIZE);
			const totalChats = allChats.length;

			for (let i = 0; i < totalBatches; i++) {
				const start = i * BATCH_SIZE;
				const end = Math.min(start + BATCH_SIZE, totalChats);
				const batchChats = allChats.slice(start, end);
				const currentBatchNum = i + 1;

				// Update progress before processing batch
				const progressPercent = Math.round((i / totalBatches) * 100);
				toast.loading(
					`${$i18n.t('Export Progress:')} ${progressPercent}% (${$i18n.t('Processing batch')} ${currentBatchNum}/${totalBatches})`,
					{ id: toastId }
				);

				batchChats.forEach((chat, index) => {
					const chatId = chat.id || `no-id-${start + index}`;
					const chatTitle = chat.title || `Untitled Chat`;
					const safeTitle = chatTitle
						.replace(/[<>:"/\\|?*]/g, '_')
						.replace(/\s+/g, '_')
						.substring(0, 60);
					const fileName = `${safeTitle}_${chatId}.json`;

					// Add file to zip - consider minimal spacing for large exports
					const spacing = totalChats > 200 ? 0 : 2;
					chatsFolder.file(fileName, JSON.stringify(chat, null, spacing));
				});

				// Optional: Yield to event loop
				if (totalBatches > 4) {
					await new Promise((resolve) => setTimeout(resolve, 5)); // Small delay
				}
			}

			// Update toast for compression phase
			toast.loading($i18n.t('Compressing files... (May take some time)'), {
				id: toastId
			});

			// Generate ZIP
			const compressionLevel = totalChats > 200 ? 1 : 6; // Faster compression for many files
			const content = await zip.generateAsync(
				{
					type: 'blob',
					compression: 'DEFLATE',
					compressionOptions: { level: compressionLevel },
					streamFiles: totalChats > 100 // Stream if many files
				},
				(metadata) => {
					// Optional metadata callback for finer progress during compression
					// toast.loading(`${$i18n.t('Compressing:')} ${Math.round(metadata.percent)}%`, { id: toastId });
				}
			);

			saveAs(content, `chats-export-${Date.now()}.zip`);

			// Final success toast
			toast.success(
				`${$i18n.t('Successfully exported')} ${totalChats} ${$i18n.t(totalChats !== 1 ? 'chats' : 'chat')} ${$i18n.t('as ZIP')}.`,
				{ id: toastId }
			);
		} catch (error) {
			console.error('ZIP Export error:', error);
			// Update toast to error
			toast.error(formatError('Failed to export ZIP:', error), { id: toastId });
		} finally {
			isExportingZip = false; // Reset flag
		}
	};

	// 5. archiveAllChatsHandler / deleteAllChatsHandler (Point 5)
	const archiveAllChatsHandler = async () => {
		showArchiveConfirm = false; // Hide UI immediately

		if (isAnyOperationInProgress) {
			toast.error($i18n.t('Another operation is already in progress.'));
			return;
		}

		await goto('/'); // Navigate first

		let fetchToastId = toast.loading($i18n.t('Checking active chats...'));

		try {
			// Fetch all chats to get the count *before* archiving
			const activeChats = await getAllChats(localStorage.token);
			const count = activeChats.length;

			if (count === 0) {
				toast.info($i18n.t('No active chats to archive.'), { id: fetchToastId });
				return; // Nothing to do
			}

			// Dismiss the checking toast and show the archiving toast
			toast.dismiss(fetchToastId);

			const archivePromise = async () => {
				await archiveAllChats(localStorage.token);
				// Refresh list after archiving
				currentChatPage.set(1);
				const updatedChats = await getChatList(localStorage.token, 1);
				chats.set(updatedChats);
				scrollPaginationEnabled.set(true);
				return count; // Resolve with the count for the success message
			};

			toast.promise(archivePromise(), {
				loading: $i18n.t('Archiving all chats...'),
				success: (archivedCount) =>
					`${$i18n.t('Successfully archived')} ${archivedCount} ${$i18n.t(archivedCount > 1 ? 'chats' : 'chat')}.`,
				error: (err) => formatError('Failed to archive chats:', err)
			});
		} catch (fetchError) {
			console.error('Failed to fetch chats before archiving:', fetchError);
			toast.error(formatError('Failed to check active chats:', fetchError), { id: fetchToastId });
		}
	};

	const deleteAllChatsHandler = async () => {
		showDeleteConfirm = false; // Hide UI immediately

		if (isAnyOperationInProgress) {
			toast.error($i18n.t('Another operation is already in progress.'));
			return;
		}

		await goto('/'); // Navigate first

		let fetchToastId = toast.loading($i18n.t('Checking active chats...'));

		try {
			// Fetch all chats to get the count *before* deleting
			const activeChats = await getAllChats(localStorage.token);
			const count = activeChats.length;

			if (count === 0) {
				toast.info($i18n.t('No active chats to delete.'), { id: fetchToastId });
				return; // Nothing to do
			}

			// Dismiss the checking toast and show the deleting toast
			toast.dismiss(fetchToastId);

			const deletePromise = async () => {
				await deleteAllChats(localStorage.token);
				// Refresh list after deleting
				currentChatPage.set(1);
				const updatedChats = await getChatList(localStorage.token, 1);
				chats.set(updatedChats);
				scrollPaginationEnabled.set(true);
				return count; // Resolve with the count for the success message
			};

			toast.promise(deletePromise(), {
				loading: $i18n.t('Deleting all chats...'),
				success: (deletedCount) =>
					`${$i18n.t('Successfully deleted')} ${deletedCount} ${$i18n.t(deletedCount > 1 ? 'chats' : 'chat')}.`,
				error: (err) => formatError('Failed to delete chats:', err)
			});
		} catch (fetchError) {
			console.error('Failed to fetch chats before deleting:', fetchError);
			toast.error(formatError('Failed to check active chats:', fetchError), { id: fetchToastId });
		}
	};

	// 6. handleArchivedChatsChange (Point 6)
	const handleArchivedChatsChange = async () => {
		// Show loading toast during refresh for better UX
		const refreshPromise = async () => {
			currentChatPage.set(1);
			const updatedChats = await getChatList(localStorage.token, 1);
			chats.set(updatedChats);
			scrollPaginationEnabled.set(true);
		};

		toast.promise(refreshPromise(), {
			loading: $i18n.t('Refreshing chat list...'),
			success: $i18n.t('Archived chat list updated.'), // Simple success feedback
			error: (err) => formatError('Failed to refresh list:', err)
		});
	};
</script>

<ArchivedChatsModal bind:show={showArchivedChatsModal} on:change={handleArchivedChatsChange} />

<div class="flex flex-col h-full justify-between space-y-3 text-sm">
	<div class=" space-y-2 overflow-y-scroll max-h-[28rem] lg:max-h-full scrollbar-thin">
		<div class="flex flex-col">
			<!-- JSON Import (Point 9: Button Text, Point 8: Disabling) -->
			<input
				id="chat-import-json-input"
				bind:this={chatImportJsonInputElement}
				bind:files={importJsonFiles}
				type="file"
				accept=".json"
				hidden
				disabled={isAnyOperationInProgress}
			/>
			<button
				class=" flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition disabled:opacity-50 disabled:cursor-not-allowed"
				on:click={() => chatImportJsonInputElement.click()}
				disabled={isAnyOperationInProgress}
			>
				<!-- Icon -->
				<div class=" self-center mr-3">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="w-4 h-4"
						><path
							fill-rule="evenodd"
							d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 9.5a.75.75 0 0 1-.75-.75V8.06l-.72.72a.75.75 0 0 1-1.06-1.06l2-2a.75.75 0 0 1 1.06 0l2 2a.75.75 0 1 1-1.06 1.06l-.72-.72v2.69a.75.75 0 0 1-.75.75Z"
							clip-rule="evenodd"
						/></svg
					>
				</div>
				<div class=" self-center text-sm font-medium">
					{isImportingJson ? $i18n.t('Importing JSON...') : $i18n.t('Import Chats (.json)')}
				</div>
			</button>

			<!-- ZIP Import (Point 9: Button Text, Point 8: Disabling) -->
			<input
				id="chat-import-zip-input"
				bind:this={chatImportZipInputElement}
				bind:files={importZipFiles}
				type="file"
				accept=".zip,application/zip,application/x-zip-compressed"
				hidden
				disabled={isAnyOperationInProgress}
			/>
			<button
				class=" flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition disabled:opacity-50 disabled:cursor-not-allowed"
				on:click={() => chatImportZipInputElement.click()}
				disabled={isAnyOperationInProgress}
			>
				<!-- Icon -->
				<div class=" self-center mr-3">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="w-4 h-4"
						><path
							fill-rule="evenodd"
							d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 9.5a.75.75 0 0 1-.75-.75V8.06l-.72.72a.75.75 0 0 1-1.06-1.06l2-2a.75.75 0 0 1 1.06 0l2 2a.75.75 0 1 1-1.06 1.06l-.72-.72v2.69a.75.75 0 0 1-.75.75Z"
							clip-rule="evenodd"
						/></svg
					>
				</div>
				<div class=" self-center text-sm font-medium">
					{isImportingZip ? $i18n.t('Importing ZIP...') : $i18n.t('Import Chats (.zip)')}
				</div>
			</button>

			<!-- JSON Export (Point 9: Button Text, Point 8: Disabling) -->
			<button
				class=" flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition disabled:opacity-50 disabled:cursor-not-allowed"
				on:click={exportChats}
				disabled={isAnyOperationInProgress}
			>
				<!-- Icon -->
				<div class=" self-center mr-3">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="w-4 h-4"
						><path
							fill-rule="evenodd"
							d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 3.5a.75.75 0 0 1 .75.75v2.69l.72-.72a.75.75 0 1 1 1.06 1.06l-2 2a.75.75 0 0 1-1.06 0l-2-2a.75.75 0 0 1 1.06-1.06l.72.72V6.25A.75.75 0 0 1 8 5.5Z"
							clip-rule="evenodd"
						/></svg
					>
				</div>
				<div class=" self-center text-sm font-medium">
					{isExportingJson ? $i18n.t('Exporting JSON...') : $i18n.t('Export Chats (.json)')}
				</div>
			</button>

			<!-- ZIP Export (Point 9: Button Text, Point 8: Disabling) -->
			<button
				class=" flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition disabled:opacity-50 disabled:cursor-not-allowed"
				on:click={exportChatsAsZip}
				disabled={isAnyOperationInProgress}
			>
				<!-- Icon -->
				<div class=" self-center mr-3">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="w-4 h-4"
						><path
							fill-rule="evenodd"
							d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 3.5a.75.75 0 0 1 .75.75v2.69l.72-.72a.75.75 0 1 1 1.06 1.06l-2 2a.75.75 0 0 1-1.06 0l-2-2a.75.75 0 0 1 1.06-1.06l.72.72V6.25A.75.75 0 0 1 8 5.5Z"
							clip-rule="evenodd"
						/></svg
					>
				</div>
				<div class=" self-center text-sm font-medium">
					{isExportingZip ? $i18n.t('Exporting ZIP...') : $i18n.t('Export Chats (.zip)')}
				</div>
			</button>
		</div>

		<hr class=" border-gray-100 dark:border-gray-850" />

		<div class="flex flex-col">
			<!-- Archived Chats Button -->
			<button
				class=" flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition disabled:opacity-50 disabled:cursor-not-allowed"
				on:click={() => (showArchivedChatsModal = true)}
				disabled={isAnyOperationInProgress}
			>
				<!-- Icon -->
				<div class=" self-center mr-3">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 24 24"
						fill="currentColor"
						class="size-4"
						><path
							d="M3.375 3C2.339 3 1.5 3.84 1.5 4.875v.75c0 1.036.84 1.875 1.875 1.875h17.25c1.035 0 1.875-.84 1.875-1.875v-.75C22.5 3.839 21.66 3 20.625 3H3.375Z"
						/><path
							fill-rule="evenodd"
							d="m3.087 9 .54 9.176A3 3 0 0 0 6.62 21h10.757a3 3 0 0 0 2.995-2.824L20.913 9H3.087ZM12 10.5a.75.75 0 0 1 .75.75v4.94l1.72-1.72a.75.75 0 1 1 1.06 1.06l-3 3a.75.75 0 0 1-1.06 0l-3-3a.75.75 0 1 1 1.06-1.06l1.72 1.72v-4.94a.75.75 0 0 1 .75-.75Z"
							clip-rule="evenodd"
						/></svg
					>
				</div>
				<div class=" self-center text-sm font-medium">{$i18n.t('Archived Chats')}</div>
			</button>

			<!-- Archive All Section (Point 10: Confirmation UI - minor tweaks/consistency) -->
			{#if showArchiveConfirm}
				<div
					class="flex justify-between items-center rounded-md py-2 px-3.5 w-full bg-yellow-100 dark:bg-yellow-900/50 text-yellow-800 dark:text-yellow-200 transition"
				>
					<div class="flex items-center space-x-2">
						<!-- Warning Icon -->
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="w-4 h-4"
							><path
								fill-rule="evenodd"
								d="M8 15A7 7 0 1 0 8 1a7 7 0 0 0 0 14ZM8 4a.75.75 0 0 1 .75.75v3a.75.75 0 0 1-1.5 0v-3A.75.75 0 0 1 8 4Zm0 8a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
								clip-rule="evenodd"
							/></svg
						>
						<span class="text-sm font-medium">{$i18n.t('Archive all?')}</span>
					</div>
					<div class="flex space-x-2 items-center">
						<button
							class="p-1 rounded hover:bg-yellow-200 dark:hover:bg-yellow-700 transition"
							on:click={archiveAllChatsHandler}
							title={$i18n.t('Confirm Archive')}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								class="w-4 h-4"
								><path
									fill-rule="evenodd"
									d="M12.416 3.376a.75.75 0 0 1 .208 1.04l-5 7.5a.75.75 0 0 1-1.154.114l-3-3a.75.75 0 0 1 1.06-1.06l2.353 2.353 4.493-6.74a.75.75 0 0 1 1.04-.207Z"
									clip-rule="evenodd"
								/></svg
							>
						</button>
						<button
							class="p-1 rounded hover:bg-yellow-200 dark:hover:bg-yellow-700 transition"
							on:click={() => (showArchiveConfirm = false)}
							title={$i18n.t('Cancel')}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								class="w-4 h-4"
								><path
									d="M5.28 4.22a.75.75 0 0 0-1.06 1.06L6.94 8l-2.72 2.72a.75.75 0 1 0 1.06 1.06L8 9.06l2.72 2.72a.75.75 0 1 0 1.06-1.06L9.06 8l2.72-2.72a.75.75 0 0 0-1.06-1.06L8 6.94 5.28 4.22Z"
								/></svg
							>
						</button>
					</div>
				</div>
			{:else}
				<button
					class=" flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition disabled:opacity-50 disabled:cursor-not-allowed"
					on:click={() => (showArchiveConfirm = true)}
					disabled={isAnyOperationInProgress}
				>
					<!-- Icon -->
					<div class=" self-center mr-3">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 24 24"
							fill="currentColor"
							class="size-4"
							><path
								d="M3.375 3C2.339 3 1.5 3.84 1.5 4.875v.75c0 1.036.84 1.875 1.875 1.875h17.25c1.035 0 1.875-.84 1.875-1.875v-.75C22.5 3.839 21.66 3 20.625 3H3.375Z"
							/><path
								fill-rule="evenodd"
								d="m3.087 9 .54 9.176A3 3 0 0 0 6.62 21h10.757a3 3 0 0 0 2.995-2.824L20.913 9H3.087Zm6.163 3.75A.75.75 0 0 1 10 12h4a.75.75 0 0 1 0 1.5h-4a.75.75 0 0 1-.75-.75Z"
								clip-rule="evenodd"
							/></svg
						>
					</div>
					<div class=" self-center text-sm font-medium">{$i18n.t('Archive All Chats')}</div>
				</button>
			{/if}

			<!-- Delete All Section (Point 10: Confirmation UI - minor tweaks/consistency) -->
			{#if showDeleteConfirm}
				<div
					class="flex justify-between items-center rounded-md py-2 px-3.5 w-full bg-red-100 dark:bg-red-900/50 text-red-800 dark:text-red-200 transition"
				>
					<div class="flex items-center space-x-2">
						<!-- Danger Icon -->
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="w-4 h-4"
							><path
								fill-rule="evenodd"
								d="M8 15A7 7 0 1 0 8 1a7 7 0 0 0 0 14ZM8 4a.75.75 0 0 1 .75.75v3a.75.75 0 0 1-1.5 0v-3A.75.75 0 0 1 8 4Zm0 8a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
								clip-rule="evenodd"
							/></svg
						>
						<span class="text-sm font-medium">{$i18n.t('Delete all forever?')}</span>
					</div>
					<div class="flex space-x-2 items-center">
						<button
							class="p-1 rounded hover:bg-red-200 dark:hover:bg-red-700 transition"
							on:click={deleteAllChatsHandler}
							title={$i18n.t('Confirm Delete')}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								class="w-4 h-4"
								><path
									fill-rule="evenodd"
									d="M12.416 3.376a.75.75 0 0 1 .208 1.04l-5 7.5a.75.75 0 0 1-1.154.114l-3-3a.75.75 0 0 1 1.06-1.06l2.353 2.353 4.493-6.74a.75.75 0 0 1 1.04-.207Z"
									clip-rule="evenodd"
								/></svg
							>
						</button>
						<button
							class="p-1 rounded hover:bg-red-200 dark:hover:bg-red-700 transition"
							on:click={() => (showDeleteConfirm = false)}
							title={$i18n.t('Cancel')}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								class="w-4 h-4"
								><path
									d="M5.28 4.22a.75.75 0 0 0-1.06 1.06L6.94 8l-2.72 2.72a.75.75 0 1 0 1.06 1.06L8 9.06l2.72 2.72a.75.75 0 1 0 1.06-1.06L9.06 8l2.72-2.72a.75.75 0 0 0-1.06-1.06L8 6.94 5.28 4.22Z"
								/></svg
							>
						</button>
					</div>
				</div>
			{:else}
				<button
					class=" flex rounded-md py-2 px-3.5 w-full hover:bg-red-200/50 dark:hover:bg-red-900/30 text-red-600 dark:text-red-400 transition disabled:opacity-50 disabled:cursor-not-allowed"
					on:click={() => (showDeleteConfirm = true)}
					disabled={isAnyOperationInProgress}
				>
					<!-- Trash Icon -->
					<div class=" self-center mr-3">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="w-4 h-4"
							><path
								fill-rule="evenodd"
								d="M5 3.25V4H2.75a.75.75 0 0 0 0 1.5h.3l.815 8.15A1.5 1.5 0 0 0 5.357 15h5.285a1.5 1.5 0 0 0 1.493-1.35l.815-8.15h.3a.75.75 0 0 0 0-1.5H11v-.75A2.25 2.25 0 0 0 8.75 1h-1.5A2.25 2.25 0 0 0 5 3.25Zm2.25-.75a.75.75 0 0 0-.75.75V4h3v-.75a.75.75 0 0 0-.75-.75h-1.5ZM6.05 6a.75.75 0 0 1 .787.713l.275 5.5a.75.75 0 0 1-1.498.075l-.275-5.5A.75.75 0 0 1 6.05 6Zm3.9 0a.75.75 0 0 1 .75.75l-.275 5.5a.75.75 0 0 1-1.498-.075l.275-5.5a.75.75 0 0 1 .748-.675Z"
								clip-rule="evenodd"
							/></svg
						>
					</div>
					<div class=" self-center text-sm font-medium">{$i18n.t('Delete All Chats')}</div>
				</button>
			{/if}
		</div>
	</div>
</div>
