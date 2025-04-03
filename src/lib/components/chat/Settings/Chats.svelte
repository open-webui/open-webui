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
		getAllUserChats,
		getChatList
	} from '$lib/apis/chats';
	import { getImportOrigin, convertOpenAIChats } from '$lib/utils';
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import ArchivedChatsModal from '$lib/components/layout/Sidebar/ArchivedChatsModal.svelte';

	const i18n = getContext('i18n');

	export let saveSettings: Function;

	// Chats
	let importFiles;
	let importZipFiles;

	let showArchiveConfirm = false;
	let showDeleteConfirm = false;
	let showArchivedChatsModal = false;
	let isExporting = false;
	let isExportingJson = false;
	let isImporting = false;
	let isImportingZip = false;

	let chatImportInputElement: HTMLInputElement;
	let chatImportZipInputElement: HTMLInputElement;

	$: if (importFiles) {
		handleImport(importFiles);
	}

	$: if (importZipFiles) {
		handleImportZip(importZipFiles);
	}

	const handleImport = async (files) => {
		if (files.length === 0) return;

		if (isImporting) {
			toast.error($i18n.t('Import already in progress'));
			return;
		}

		try {
			isImporting = true;
			const file = files[0];

			// Check if it's a ZIP file by examining the file extension
			if (file.name.toLowerCase().endsWith('.zip')) {
				toast.error($i18n.t('Please use "Import Chats as .zip" for ZIP files'));
				return;
			} else {
				// Assume it's a JSON file
				await importJsonFile(file);
			}

			// Reset the file input
			if (chatImportInputElement) {
				chatImportInputElement.value = '';
			}
			importFiles = null;
		} catch (error) {
			console.error('Import error:', error);
			toast.error($i18n.t('Failed to import: ') + error.message);
		} finally {
			isImporting = false;
		}
	};

	const handleImportZip = async (files) => {
		if (files.length === 0) return;

		if (isImportingZip) {
			toast.error($i18n.t('ZIP import already in progress'));
			return;
		}

		try {
			isImportingZip = true;
			const file = files[0];

			// Check if it's a ZIP file
			if (!file.name.toLowerCase().endsWith('.zip')) {
				toast.error($i18n.t('Please use "Import Chats" for JSON files'));
				return;
			}

			toast.info($i18n.t('Processing ZIP file, please wait...'));
			await importZipChats(file);

			// Reset the file input
			if (chatImportZipInputElement) {
				chatImportZipInputElement.value = '';
			}
			importZipFiles = null;
		} catch (error) {
			console.error('ZIP import error:', error);
			toast.error($i18n.t('Failed to import ZIP: ') + error.message);
		} finally {
			isImportingZip = false;
		}
	};

	const importJsonFile = (file) => {
		// No need to return a promise here, use toast.promise for async feedback
		let reader = new FileReader();
		let toastId = null; // Keep track of the toast

		reader.onload = async (event) => {
			try {
				const fileContent = event.target.result;
				if (!fileContent || typeof fileContent !== 'string') {
					throw new Error('File content could not be read.');
				}
				const parsedData = JSON.parse(fileContent);

				let chatsToImport;
				let origin = 'unknown'; // Default origin

				try {
					// Attempt to determine origin, but catch errors if it fails
					// This handles the case where getImportOrigin isn't expecting
					// the single-object format.
					origin = getImportOrigin(parsedData);
				} catch (error) {
					console.warn(
						`Failed to determine import origin for ${file.name}, assuming standard format. Error: ${error.message}`
					);
					// Keep origin as 'unknown' or set explicitly to 'standard' if preferred
					// origin = 'standard';
				}

				if (origin === 'openai') {
					try {
						// Show converting message (if toastId exists)
						if (toastId) toast.info($i18n.t('Converting OpenAI format...'), { id: toastId });
						chatsToImport = convertOpenAIChats(parsedData);
						if (toastId) toast.dismiss(toastId); // Dismiss converting message before import promise
					} catch (error) {
						console.error('Unable to convert OpenAI chats:', error);
						toast.error(`${$i18n.t('Failed to convert OpenAI chats:')} ${error.message}`, {
							id: toastId
						});
						return; // Stop import if conversion fails
					}
				} else {
					// Assume standard format (single chat or array of chats)
					// This block now runs if origin is 'unknown', 'standard', or anything else non-'openai',
					// including when getImportOrigin failed.
					if (typeof parsedData === 'object' && parsedData !== null) {
						chatsToImport = Array.isArray(parsedData) ? parsedData : [parsedData];
						if (toastId) toast.dismiss(toastId); // Dismiss reading message before import promise
					} else {
						// If parsedData isn't an object/array after successful JSON.parse (shouldn't happen with valid JSON)
						throw new Error('Parsed JSON data is not a valid object or array.');
					}
				}

				if (!chatsToImport || chatsToImport.length === 0) {
					toast.info($i18n.t('No valid chats found in the file.'));
					return;
				}

				const chatCount = chatsToImport.length;

				// Use toast.promise for the import process
				toast.promise(importChats(chatsToImport), {
					loading: `${$i18n.t('Importing')} ${chatCount} ${$i18n.t(chatCount > 1 ? 'chats...' : 'chat...')}`,
					success: (result) => {
						// importChats doesn't return specific counts, so we use the count from the file
						return `${$i18n.t('Successfully imported')} ${chatCount} ${$i18n.t(chatCount > 1 ? 'chats' : 'chat')}`;
					},
					error: (err) => {
						console.error('Error during chat import:', err);
						return `${$i18n.t('Failed to import chats:')} ${err.message || err}`;
					}
				});
			} catch (error) {
				console.error('Error processing JSON file:', error);
				// Make sure the error message includes the actual error
				toast.error(`${$i18n.t('Failed to read or parse JSON file:')} ${error.message}`, {
					id: toastId
				});
			}
		};

		reader.onerror = (error) => {
			console.error('File reading error:', error);
			toast.error($i18n.t('Failed to read file.'), { id: toastId });
		};

		// Show initial loading toast
		toastId = toast.loading($i18n.t('Reading file...'));
		reader.readAsText(file);
		// Note: The outer function doesn't need to be async or return a promise
		// because the feedback is handled internally by toast.promise.
	};

	const importZipChats = async (zipFile) => {
		let toastId = null; // Keep track of the toast ID
		try {
			// Load the zip file
			const zip = await JSZip.loadAsync(zipFile);
			const chatFiles = [];

			// Look for JSON files in the chats folder
			zip.folder('chats').forEach((relativePath, file) => {
				if (relativePath.endsWith('.json') && !file.dir) {
					// Ensure it's a file, not a directory entry
					chatFiles.push(file);
				}
			});

			if (chatFiles.length === 0) {
				throw new Error(
					$i18n.t('No valid chat JSON files found in the /chats folder of the ZIP archive')
				);
			}

			// Use template literals for string interpolation with i18n
			toast.info(`${$i18n.t('Found')} ${chatFiles.length} ${$i18n.t('chats to import...')}`);

			// Process files in batches to prevent memory issues
			const BATCH_SIZE = 20;
			const totalBatches = Math.ceil(chatFiles.length / BATCH_SIZE);
			let importedCount = 0;

			// Initial progress toast
			toastId = toast.loading(`${$i18n.t('Import progress:')} 0%`);

			for (let i = 0; i < totalBatches; i++) {
				const start = i * BATCH_SIZE;
				const end = Math.min(start + BATCH_SIZE, chatFiles.length);
				const batchFiles = chatFiles.slice(start, end);

				// Process this batch
				const batchPromises = batchFiles.map(async (file) => {
					try {
						const content = await file.async('text');
						const chatData = JSON.parse(content);
						// Basic validation: check for an ID, or a nested chat with an ID
						if (
							chatData &&
							(typeof chatData.id === 'string' ||
								(chatData.chat && typeof chatData.chat.id === 'string'))
						) {
							return chatData;
						}
						console.warn(`Skipping invalid chat file: ${file.name}`);
						return null;
					} catch (e) {
						console.error(`Error parsing chat file ${file.name}:`, e);
						toast.warning(`${$i18n.t('Skipped invalid JSON file:')} ${file.name}`);
						return null; // Skip this file on error
					}
				});

				const batchResults = await Promise.all(batchPromises);
				const validChatsInBatch = batchResults.filter((chat) => chat !== null);

				if (validChatsInBatch.length > 0) {
					await importChats(validChatsInBatch);
					importedCount += validChatsInBatch.length;
				}

				// Update progress after processing the batch
				const progress = Math.min(100, Math.round(((i + 1) / totalBatches) * 100));
				// Update the existing loading toast
				toast.loading(`${$i18n.t('Import progress:')} ${progress}%`, { id: toastId });

				// Yield to the event loop if processing many batches
				if (totalBatches > 2) {
					await new Promise((resolve) => setTimeout(resolve, 0));
				}
			}

			// Update toast to success, replacing the loading one
			toast.success(`${$i18n.t('Successfully imported')} ${importedCount} ${$i18n.t('chats')}`, {
				id: toastId
			});
		} catch (error) {
			console.error('Error importing ZIP:', error);
			// Update toast to error if it exists, otherwise show a new error
			const errorMsg = `${$i18n.t('Failed to import ZIP:')} ${error.message}`;
			if (toastId) {
				toast.error(errorMsg, { id: toastId });
			} else {
				toast.error(errorMsg);
			}
			// Re-throw the error if needed for upstream handling, though maybe not necessary here
			// throw error;
		}
		// No finally block needed for toast dismissal when updating by ID
	};

	const importChats = async (_chats) => {
		// Make sure we're dealing with an array
		const chatsArray = Array.isArray(_chats) ? _chats : [_chats];

		for (const chat of chatsArray) {
			if (chat.chat) {
				await createNewChat(localStorage.token, chat.chat);
			} else {
				await createNewChat(localStorage.token, chat);
			}
		}

		currentChatPage.set(1);
		await chats.set(await getChatList(localStorage.token, $currentChatPage));
		scrollPaginationEnabled.set(true);
	};

	const exportChats = async () => {
		if (isExportingJson) {
			toast.error($i18n.t('Export already in progress'));
			return;
		}

		isExportingJson = true;

		// Use toast.promise for the entire async operation
		toast.promise(
			// The async function to execute
			async () => {
				const allChats = await getAllChats(localStorage.token);

				if (!allChats || allChats.length === 0) {
					// Throw an error to be caught by the promise's error handler,
					// or handle it as a specific non-error case if preferred.
					// Throwing allows using the error state of the promise toast.
					throw new Error($i18n.t('No chats found to export.'));
				}

				const blob = new Blob([JSON.stringify(allChats, null, 2)], {
					// Add indentation for readability
					type: 'application/json;charset=utf-8'
				});
				saveAs(blob, `chats-export-${Date.now()}.json`);
				return allChats.length; // Return the count for the success message
			},
			// Configuration for the toast messages
			{
				loading: $i18n.t('Preparing export...'),
				success: (count) =>
					`${$i18n.t('Successfully exported')} ${count} ${$i18n.t(count > 1 ? 'chats' : 'chat')}`,
				error: (err) => {
					console.error('Export error:', err);
					// Check if it's the specific "no chats" error we threw
					if (err.message === $i18n.t('No chats found to export.')) {
						return err.message; // Display the specific info message as an "error" toast
					}
					return `${$i18n.t('Export failed:')} ${err.message || err}`;
				},
				finally: () => {
					isExportingJson = false; // Reset the flag regardless of success or failure
				}
			}
		);
	};

	const exportChatsAsZip = async () => {
		if (isExporting) {
			toast.error($i18n.t('Export already in progress'));
			return;
		}

		let toastId = null; // Initialize toastId
		try {
			isExporting = true;
			// Use loading toast immediately, this will be updated
			toastId = toast.loading($i18n.t('Preparing export, please wait...'));

			const allChats = await getAllChats(localStorage.token);

			if (!allChats || allChats.length === 0) {
				toast.info($i18n.t('No chats found to export.'), { id: toastId }); // Update the loading toast
				isExporting = false; // Reset flag early
				return; // Exit if no chats
			}

			const zip = new JSZip();

			// Create a folder for the chats
			const chatsFolder = zip.folder('chats');

			// Process chats in batches to prevent memory issues and update progress
			const BATCH_SIZE = 50;
			const totalBatches = Math.ceil(allChats.length / BATCH_SIZE);

			// Update toast to show initial progress
			toast.loading(`${$i18n.t('Export progress:')} 0%`, { id: toastId });

			for (let i = 0; i < totalBatches; i++) {
				const start = i * BATCH_SIZE;
				const end = Math.min(start + BATCH_SIZE, allChats.length);
				const batchChats = allChats.slice(start, end);

				// Add each chat in this batch as an individual JSON file
				batchChats.forEach((chat) => {
					// Use chat.id if available, otherwise generate a fallback based on index
					const chatId = chat.id || `generated-${start + batchChats.indexOf(chat)}`;
					const chatTitle = chat.title || `chat`;
					// Create a safer filename - replace invalid characters
					const safeTitle = chatTitle
						.replace(/[<>:"/\\|?*]/g, '_') // Replace forbidden characters
						.replace(/\s+/g, '_') // Replace whitespace with underscore
						.replace(/__/g, '_') // Replace double underscores
						.substring(0, 50); // Limit length to avoid issues

					const fileName = `${safeTitle}-${chatId}.json`;

					// Use stringify with spacing for better readability,
					// but minimize if we have a lot of chats
					const spacing = allChats.length > 100 ? 0 : 2;
					chatsFolder.file(fileName, JSON.stringify(chat, null, spacing));
				});

				// Update progress
				const progress = Math.min(100, Math.round(((i + 1) / totalBatches) * 100));
				// Update the existing loading toast
				toast.loading(`${$i18n.t('Export progress:')} ${progress}%`, { id: toastId });

				// Yield to the event loop if processing many batches
				if (totalBatches > 2) {
					await new Promise((resolve) => setTimeout(resolve, 0));
				}
			}

			// Update toast for compression phase
			toast.loading($i18n.t('Compressing files...'), { id: toastId });

			// Use compression level based on number of chats
			const compressionLevel = allChats.length > 200 ? 3 : 9; // Lower compression for many files (faster)

			// Generate the zip file with appropriate options
			const content = await zip.generateAsync({
				type: 'blob',
				compression: 'DEFLATE',
				compressionOptions: {
					level: compressionLevel
				},
				streamFiles: allChats.length > 100 // Use streaming for large number of files
			});

			// Save the zip file
			saveAs(content, `chats-export-${Date.now()}.zip`);

			// Update the loading toast to success
			toast.success($i18n.t('Export completed successfully'), { id: toastId });
		} catch (error) {
			console.error('Export error:', error);
			const errorMsg = `${$i18n.t('Failed to create zip:')} ${error.message}`;
			// Update the loading toast to error, or show new error if toastId wasn't set
			if (toastId) {
				toast.error(errorMsg, { id: toastId });
			} else {
				toast.error(errorMsg);
			}
		} finally {
			isExporting = false;
			// No need to dismiss toast here, success/error update handled it via ID
		}
	};

	const archiveAllChatsHandler = async () => {
		await goto('/');
		await archiveAllChats(localStorage.token).catch((error) => {
			toast.error(`${error}`);
		});

		currentChatPage.set(1);
		await chats.set(await getChatList(localStorage.token, $currentChatPage));
		scrollPaginationEnabled.set(true);
	};

	const deleteAllChatsHandler = async () => {
		await goto('/');
		await deleteAllChats(localStorage.token).catch((error) => {
			toast.error(`${error}`);
		});

		currentChatPage.set(1);
		await chats.set(await getChatList(localStorage.token, $currentChatPage));
		scrollPaginationEnabled.set(true);
	};

	const handleArchivedChatsChange = async () => {
		currentChatPage.set(1);
		await chats.set(await getChatList(localStorage.token, $currentChatPage));
		scrollPaginationEnabled.set(true);
	};
</script>

<ArchivedChatsModal bind:show={showArchivedChatsModal} on:change={handleArchivedChatsChange} />

<div class="flex flex-col h-full justify-between space-y-3 text-sm">
	<div class=" space-y-2 overflow-y-scroll max-h-[28rem] lg:max-h-full">
		<div class="flex flex-col">
			<!-- JSON Import -->
			<input
				id="chat-import-input"
				bind:this={chatImportInputElement}
				bind:files={importFiles}
				type="file"
				accept=".json"
				hidden
			/>
			<button
				class=" flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={() => {
					chatImportInputElement.click();
				}}
				disabled={isImporting}
			>
				<div class=" self-center mr-3">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="w-4 h-4"
					>
						<path
							fill-rule="evenodd"
							d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 9.5a.75.75 0 0 1-.75-.75V8.06l-.72.72a.75.75 0 0 1-1.06-1.06l2-2a.75.75 0 0 1 1.06 0l2 2a.75.75 0 1 1-1.06 1.06l-.72-.72v2.69a.75.75 0 0 1-.75.75Z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
				<div class=" self-center text-sm font-medium">
					{isImporting ? $i18n.t('Importing...') : $i18n.t('Import Chats')}
				</div>
			</button>

			<!-- ZIP Import -->
			<input
				id="chat-import-zip-input"
				bind:this={chatImportZipInputElement}
				bind:files={importZipFiles}
				type="file"
				accept=".zip"
				hidden
			/>
			<button
				class=" flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={() => {
					chatImportZipInputElement.click();
				}}
				disabled={isImportingZip}
			>
				<div class=" self-center mr-3">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="w-4 h-4"
					>
						<path
							fill-rule="evenodd"
							d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 9.5a.75.75 0 0 1-.75-.75V8.06l-.72.72a.75.75 0 0 1-1.06-1.06l2-2a.75.75 0 0 1 1.06 0l2 2a.75.75 0 1 1-1.06 1.06l-.72-.72v2.69a.75.75 0 0 1-.75.75Z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
				<div class=" self-center text-sm font-medium">
					{isImportingZip ? $i18n.t('Importing...') : $i18n.t('Import Chats as .zip')}
				</div>
			</button>

			<!-- JSON Export -->
			<button
				class=" flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={exportChats}
				disabled={isExportingJson}
			>
				<div class=" self-center mr-3">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="w-4 h-4"
					>
						<path
							fill-rule="evenodd"
							d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 3.5a.75.75 0 0 1 .75.75v2.69l.72-.72a.75.75 0 1 1 1.06 1.06l-2 2a.75.75 0 0 1-1.06 0l-2-2a.75.75 0 0 1 1.06-1.06l.72.72V6.25A.75.75 0 0 1 8 5.5Z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
				<div class=" self-center text-sm font-medium">
					{isExportingJson ? $i18n.t('Exporting...') : $i18n.t('Export Chats')}
				</div>
			</button>

			<!-- ZIP Export -->
			<button
				class=" flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={() => {
					exportChatsAsZip();
				}}
				disabled={isExporting}
			>
				<div class=" self-center mr-3">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="w-4 h-4"
					>
						<path
							fill-rule="evenodd"
							d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 3.5a.75.75 0 0 1 .75.75v2.69l.72-.72a.75.75 0 1 1 1.06 1.06l-2 2a.75.75 0 0 1-1.06 0l-2-2a.75.75 0 0 1 1.06-1.06l.72.72V6.25A.75.75 0 0 1 8 5.5Z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
				<div class=" self-center text-sm font-medium">
					{isExporting ? $i18n.t('Exporting...') : $i18n.t('Export Chats as .zip')}
				</div>
			</button>
		</div>

		<hr class=" border-gray-100 dark:border-gray-850" />

		<div class="flex flex-col">
			<button
				class=" flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
				on:click={() => {
					showArchivedChatsModal = true;
				}}
			>
				<div class=" self-center mr-3">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 24 24"
						fill="currentColor"
						class="size-4"
					>
						<path
							d="M3.375 3C2.339 3 1.5 3.84 1.5 4.875v.75c0 1.036.84 1.875 1.875 1.875h17.25c1.035 0 1.875-.84 1.875-1.875v-.75C22.5 3.839 21.66 3 20.625 3H3.375Z"
						/>
						<path
							fill-rule="evenodd"
							d="m3.087 9 .54 9.176A3 3 0 0 0 6.62 21h10.757a3 3 0 0 0 2.995-2.824L20.913 9H3.087ZM12 10.5a.75.75 0 0 1 .75.75v4.94l1.72-1.72a.75.75 0 1 1 1.06 1.06l-3 3a.75.75 0 0 1-1.06 0l-3-3a.75.75 0 1 1 1.06-1.06l1.72 1.72v-4.94a.75.75 0 0 1 .75-.75Z"
							clip-rule="evenodd"
						/>
					</svg>
				</div>
				<div class=" self-center text-sm font-medium">{$i18n.t('Archived Chats')}</div>
			</button>

			{#if showArchiveConfirm}
				<div class="flex justify-between rounded-md items-center py-2 px-3.5 w-full transition">
					<div class="flex items-center space-x-3">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path d="M2 3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3Z" />
							<path
								fill-rule="evenodd"
								d="M13 6H3v6a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V6ZM5.72 7.47a.75.75 0 0 1 1.06 0L8 8.69l1.22-1.22a.75.75 0 1 1 1.06 1.06L9.06 9.75l1.22 1.22a.75.75 0 1 1-1.06 1.06L8 10.81l-1.22 1.22a.75.75 0 0 1-1.06-1.06l1.22-1.22-1.22-1.22a.75.75 0 0 1 0-1.06Z"
								clip-rule="evenodd"
							/>
						</svg>
						<span>{$i18n.t('Are you sure?')}</span>
					</div>

					<div class="flex space-x-1.5 items-center">
						<button
							class="hover:text-white transition"
							on:click={() => {
								archiveAllChatsHandler();
								showArchiveConfirm = false;
							}}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="w-4 h-4"
							>
								<path
									fill-rule="evenodd"
									d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
									clip-rule="evenodd"
								/>
							</svg>
						</button>
						<button
							class="hover:text-white transition"
							on:click={() => {
								showArchiveConfirm = false;
							}}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="w-4 h-4"
							>
								<path
									d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
								/>
							</svg>
						</button>
					</div>
				</div>
			{:else}
				<button
					class=" flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
					on:click={() => {
						showArchiveConfirm = true;
					}}
				>
					<div class=" self-center mr-3">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 24 24"
							fill="currentColor"
							class="size-4"
						>
							<path
								d="M3.375 3C2.339 3 1.5 3.84 1.5 4.875v.75c0 1.036.84 1.875 1.875 1.875h17.25c1.035 0 1.875-.84 1.875-1.875v-.75C22.5 3.839 21.66 3 20.625 3H3.375Z"
							/>
							<path
								fill-rule="evenodd"
								d="m3.087 9 .54 9.176A3 3 0 0 0 6.62 21h10.757a3 3 0 0 0 2.995-2.824L20.913 9H3.087Zm6.163 3.75A.75.75 0 0 1 10 12h4a.75.75 0 0 1 0 1.5h-4a.75.75 0 0 1-.75-.75Z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<div class=" self-center text-sm font-medium">{$i18n.t('Archive All Chats')}</div>
				</button>
			{/if}

			{#if showDeleteConfirm}
				<div class="flex justify-between rounded-md items-center py-2 px-3.5 w-full transition">
					<div class="flex items-center space-x-3">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path d="M2 3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3Z" />
							<path
								fill-rule="evenodd"
								d="M13 6H3v6a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V6ZM5.72 7.47a.75.75 0 0 1 1.06 0L8 8.69l1.22-1.22a.75.75 0 1 1 1.06 1.06L9.06 9.75l1.22 1.22a.75.75 0 1 1-1.06 1.06L8 10.81l-1.22 1.22a.75.75 0 0 1-1.06-1.06l1.22-1.22-1.22-1.22a.75.75 0 0 1 0-1.06Z"
								clip-rule="evenodd"
							/>
						</svg>
						<span>{$i18n.t('Are you sure?')}</span>
					</div>

					<div class="flex space-x-1.5 items-center">
						<button
							class="hover:text-white transition"
							on:click={() => {
								deleteAllChatsHandler();
								showDeleteConfirm = false;
							}}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="w-4 h-4"
							>
								<path
									fill-rule="evenodd"
									d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
									clip-rule="evenodd"
								/>
							</svg>
						</button>
						<button
							class="hover:text-white transition"
							on:click={() => {
								showDeleteConfirm = false;
							}}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="w-4 h-4"
							>
								<path
									d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
								/>
							</svg>
						</button>
					</div>
				</div>
			{:else}
				<button
					class=" flex rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition"
					on:click={() => {
						showDeleteConfirm = true;
					}}
				>
					<div class=" self-center mr-3">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path
								fill-rule="evenodd"
								d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm7 7a.75.75 0 0 1-.75.75h-4.5a.75.75 0 0 1 0-1.5h4.5A.75.75 0 0 1 11 9Z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<div class=" self-center text-sm font-medium">{$i18n.t('Delete All Chats')}</div>
				</button>
			{/if}
		</div>
	</div>
</div>
