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
		// getAllUserChats,
		getChatList
	} from '$lib/apis/chats';
	import { getImportOrigin, convertOpenAIChats } from '$lib/utils';
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import ArchivedChatsModal from '$lib/components/layout/Sidebar/ArchivedChatsModal.svelte';

	const i18n = getContext('i18n');

	export let saveSettings: Function;

	let importJsonFiles: FileList | null = null;
	let importZipFiles: FileList | null = null;

	let showArchiveConfirm = false;
	let showDeleteConfirm = false;
	let showArchivedChatsModal = false;

	let isImportingJson = false;
	let isImportingZip = false;
	let isExportingJson = false;
	let isExportingZip = false;

	let chatImportJsonInputElement: HTMLInputElement;
	let chatImportZipInputElement: HTMLInputElement;
	
	$: isAnyOperationInProgress =
		isImportingJson || isImportingZip || isExportingJson || isExportingZip;

	$: if (importJsonFiles) {
		handleImportJson(importJsonFiles);
		if (chatImportJsonInputElement) chatImportJsonInputElement.value = '';
		importJsonFiles = null;
	}

	$: if (importZipFiles) {
		handleImportZipFileSelect(importZipFiles);
		if (chatImportZipInputElement) chatImportZipInputElement.value = '';
		importZipFiles = null;
	}

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
		const validChats = (Array.isArray(chatsToImport) ? chatsToImport : [chatsToImport]).filter(
			(c) => c !== null
		);

		if (validChats.length === 0) return;

		for (const chat of validChats) {
			const chatData = chat.chat && typeof chat.chat === 'object' ? chat.chat : chat;
			if (chatData && (chatData.id || chatData.title || chatData.messages?.length > 0)) {
				try {
					await createNewChat(localStorage.token, chatData);
				} catch (error) {
					console.error(
						`Failed to import chat: ${chatData.title || chatData.id || 'Unknown'}`,
						error
					);
					// Optionally show a toast for individual chat import failures, but might be too noisy
					// toast.error(`${$i18n.t('Failed to import chat:')} ${chatData.title || chatData.id || 'Unknown'}`);
				}
			} else {
				console.warn('Skipping potentially empty or invalid chat object during import:', chat);
			}
		}

		currentChatPage.set(1);
		await chats.set(await getChatList(localStorage.token, 1));
		scrollPaginationEnabled.set(true);
	};

	const formatError = (prefixKey: string, err: any): string => {
		const prefix = $i18n.t(prefixKey);
		const message = err?.message || (typeof err === 'string' ? err : JSON.stringify(err));
		return `${prefix} ${message}`;
	};

	const handleImportJson = async (files: FileList) => {
		if (files.length === 0) return;
		const file = files[0];

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
			const fileContent = await readFileAsText(file);
			const parsedData = JSON.parse(fileContent);

			let chatsToImport: any[] = [];
			let origin = 'unknown';

			try {
				origin = getImportOrigin(parsedData);
			} catch (error: any) {
				console.warn(
					`Could not determine import origin for ${file.name}, assuming standard format. Error: ${error?.message}`
				);
			}

			if (origin === 'openai') {
				try {
					chatsToImport = convertOpenAIChats(parsedData);
				} catch (conversionError) {
					console.error('OpenAI conversion failed:', conversionError);
					throw new Error(formatError('Failed to convert OpenAI chats:', conversionError));
				}
			} else {
				if (typeof parsedData === 'object' && parsedData !== null) {
					chatsToImport = Array.isArray(parsedData) ? parsedData : [parsedData];
				} else {
					throw new Error($i18n.t('Parsed JSON data is not a valid object or array.'));
				}
			}

			const validChatsToImport = chatsToImport.filter((chat) => chat && typeof chat === 'object');

			if (validChatsToImport.length === 0) {
				return 0;
			}

			await importChats(validChatsToImport);
			return validChatsToImport.length;
		};

		toast.promise(importPromise(), {
			loading: $i18n.t('Importing chats from JSON...'),
			success: (count) => {
				isImportingJson = false;
				if (count === 0) {
					return $i18n.t('No valid chats found in the file.');
				}
				return `${$i18n.t('Successfully imported')} ${count} ${$i18n.t(count > 1 ? 'chats' : 'chat')}`;
			},
			error: (err) => {
				isImportingJson = false;
				console.error('JSON Import error:', err);
				if (err instanceof Error && err.message.startsWith($i18n.t('Failed to'))) {
					return err.message;
				}
				return formatError('Failed to import JSON:', err);
			}
		});
	};

	const handleImportZipFileSelect = async (files: FileList) => {
		if (files.length === 0) return;
		const file = files[0];

		if (!file.name.toLowerCase().endsWith('.zip')) {
			toast.error($i18n.t('Invalid file type. Please select a .zip file.'));
			return;
		}

		if (isAnyOperationInProgress) {
			toast.error($i18n.t('Another operation is already in progress.'));
			return;
		}

		await handleImportZip(file);
	};

	const handleImportZip = async (zipFile: File) => {
		isImportingZip = true;
		let toastId = toast.loading($i18n.t('Processing ZIP file...'));

		try {
			const zip = await JSZip.loadAsync(zipFile);
			const chatFiles: JSZip.JSZipObject[] = [];
			const chatsFolder = zip.folder('chats');

			if (!chatsFolder) {
				throw new Error($i18n.t('No "chats" folder found in the ZIP archive.'));
			}

			chatsFolder.forEach((relativePath, file) => {
				if (!file.dir && relativePath.endsWith('.json') && !relativePath.includes('/')) {
					chatFiles.push(file);
				}
			});

			if (chatFiles.length === 0) {
				toast.info($i18n.t('No valid .json chat files found directly in the /chats folder.'), {
					id: toastId
				});
				isImportingZip = false;
				return;
			}

			toast.info(
				`${$i18n.t('Found')} ${chatFiles.length} ${$i18n.t('potential chat files. Starting import...')}`,
				{ id: toastId }
			);
			toastId = toast.loading(`${$i18n.t('Import Progress:')} 0%`);

			const BATCH_SIZE = 25;
			const totalBatches = Math.ceil(chatFiles.length / BATCH_SIZE);
			let totalImportedCount = 0;
			let totalSkippedCount = 0;

			for (let i = 0; i < totalBatches; i++) {
				const start = i * BATCH_SIZE;
				const end = Math.min(start + BATCH_SIZE, chatFiles.length);
				const batchFiles = chatFiles.slice(start, end);
				const currentBatchNum = i + 1;

				const progressPercent = Math.round((i / totalBatches) * 100);
				toast.loading(
					`${$i18n.t('Import Progress:')} ${progressPercent}% (${$i18n.t('Batch')} ${currentBatchNum}/${totalBatches})`,
					{ id: toastId }
				);

				const batchParsePromises = batchFiles.map(async (file) => {
					try {
						const content = await file.async('text');
						const chatData = JSON.parse(content);
						return chatData;
					} catch (e) {
						console.error(`Error processing file ${file.name}:`, e);
						toast.warning(`${$i18n.t('Skipped invalid JSON file:')} ${file.name}`);
						totalSkippedCount++;
						return null;
					}
				});

				const parsedChatsInBatch = await Promise.all(batchParsePromises);
				const validChatsInBatch = parsedChatsInBatch.filter((chat) => chat !== null);

				if (validChatsInBatch.length > 0) {
					await importChats(validChatsInBatch);
					totalImportedCount += validChatsInBatch.length;
				}

				if (totalBatches > 5) {
					await new Promise((resolve) => setTimeout(resolve, 0));
				}
			}

			toast.loading(`${$i18n.t('Import Progress:')} 100% - ${$i18n.t('Finalizing...')}`, {
				id: toastId
			});

			let successMessage = `${$i18n.t('Successfully imported')} ${totalImportedCount} ${$i18n.t(totalImportedCount !== 1 ? 'chats' : 'chat')}.`;
			if (totalSkippedCount > 0) {
				successMessage += ` ${$i18n.t('Skipped')} ${totalSkippedCount} ${$i18n.t(totalSkippedCount !== 1 ? 'files' : 'file')}.`;
			}
			toast.success(successMessage, { id: toastId });
		} catch (error) {
			console.error('ZIP Import Error:', error);
			toast.error(formatError('Failed to import ZIP:', error), { id: toastId });
		} finally {
			isImportingZip = false;
		}
	};

	const exportChats = async () => {
		if (isAnyOperationInProgress) {
			toast.error($i18n.t('Another operation is already in progress.'));
			return;
		}
		isExportingJson = true;
		const fetchToastId = toast.loading($i18n.t('Fetching chats...'));

		try {
			const allChats = await getAllChats(localStorage.token);

			if (!allChats || allChats.length === 0) {
				toast.info($i18n.t('No chats found to export.'), { id: fetchToastId });
				isExportingJson = false;
				return;
			}

			toast.dismiss(fetchToastId);

			const exportPromise = new Promise((resolve, reject) => {
				try {
					const blob = new Blob([JSON.stringify(allChats, null, 2)], {
						type: 'application/json;charset=utf-8'
					});
					saveAs(blob, `chats-export-${Date.now()}.json`);
					resolve(allChats.length);
				} catch (err) {
					reject(err);
				}
			});

			toast.promise(exportPromise, {
				loading: $i18n.t('Saving JSON file...'),
				success: (count) => {
					isExportingJson = false;
					return `${$i18n.t('Successfully exported')} ${count} ${$i18n.t(count !== 1 ? 'chats' : 'chat')}`;
				},
				error: (err) => {
					isExportingJson = false;
					console.error('JSON Export error:', err);
					return formatError('Failed to save JSON file:', err);
				}
			});
		} catch (fetchError) {
			console.error('Failed to fetch chats for export:', fetchError);
			toast.error(formatError('Failed to fetch chats:', fetchError), { id: fetchToastId });
			isExportingJson = false;
		}
	};

	const exportChatsAsZip = async () => {
		if (isAnyOperationInProgress) {
			toast.error($i18n.t('Another operation is already in progress.'));
			return;
		}
		isExportingZip = true;
		let toastId = toast.loading($i18n.t('Fetching chats...'));

		try {
			const allChats = await getAllChats(localStorage.token);

			if (!allChats || allChats.length === 0) {
				toast.info($i18n.t('No chats found to export.'), { id: toastId });
				isExportingZip = false;
				return;
			}

			toast.loading(
				`${$i18n.t('Found')} ${allChats.length} ${$i18n.t('chats. Preparing ZIP...')}`,
				{ id: toastId }
			);

			const zip = new JSZip();
			const chatsFolder = zip.folder('chats');

			if (!chatsFolder) {
				// Should not happen with JSZip, but defensive check
				throw new Error("Failed to create 'chats' folder in ZIP.");
			}

			const BATCH_SIZE = 50;
			const totalBatches = Math.ceil(allChats.length / BATCH_SIZE);
			const totalChats = allChats.length;

			for (let i = 0; i < totalBatches; i++) {
				const start = i * BATCH_SIZE;
				const end = Math.min(start + BATCH_SIZE, totalChats);
				const batchChats = allChats.slice(start, end);
				const currentBatchNum = i + 1;

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

					const spacing = totalChats > 200 ? 0 : 2;
					chatsFolder.file(fileName, JSON.stringify(chat, null, spacing));
				});

				if (totalBatches > 4) {
					await new Promise((resolve) => setTimeout(resolve, 5));
				}
			}

			toast.loading($i18n.t('Compressing files... (May take some time)'), {
				id: toastId
			});

			const compressionLevel = totalChats > 200 ? 1 : 6;
			const content = await zip.generateAsync(
				{
					type: 'blob',
					compression: 'DEFLATE',
					compressionOptions: { level: compressionLevel },
					streamFiles: totalChats > 100
				}
				// Optional progress callback during compression:
				// (metadata) => {
				// 	toast.loading(`${$i18n.t('Compressing:')} ${Math.round(metadata.percent)}%`, { id: toastId });
				// }
			);

			saveAs(content, `chats-export-${Date.now()}.zip`);

			toast.success(
				`${$i18n.t('Successfully exported')} ${totalChats} ${$i18n.t(totalChats !== 1 ? 'chats' : 'chat')} ${$i18n.t('as ZIP')}.`,
				{ id: toastId }
			);
		} catch (error) {
			console.error('ZIP Export error:', error);
			toast.error(formatError('Failed to export ZIP:', error), { id: toastId });
		} finally {
			isExportingZip = false;
		}
	};

	const archiveAllChatsHandler = async () => {
		showArchiveConfirm = false;

		if (isAnyOperationInProgress) {
			toast.error($i18n.t('Another operation is already in progress.'));
			return;
		}

		await goto('/');

		let fetchToastId = toast.loading($i18n.t('Checking active chats...'));

		try {
			const activeChats = await getAllChats(localStorage.token);
			const count = activeChats.length;

			if (count === 0) {
				toast.info($i18n.t('No active chats to archive.'), { id: fetchToastId });
				return;
			}

			toast.dismiss(fetchToastId);

			const archivePromise = async () => {
				await archiveAllChats(localStorage.token);
				currentChatPage.set(1);
				const updatedChats = await getChatList(localStorage.token, 1);
				chats.set(updatedChats);
				scrollPaginationEnabled.set(true);
				return count;
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
		showDeleteConfirm = false;

		if (isAnyOperationInProgress) {
			toast.error($i18n.t('Another operation is already in progress.'));
			return;
		}

		await goto('/');

		let fetchToastId = toast.loading($i18n.t('Checking active chats...'));

		try {
			const activeChats = await getAllChats(localStorage.token);
			const count = activeChats.length;

			if (count === 0) {
				toast.info($i18n.t('No active chats to delete.'), { id: fetchToastId });
				return;
			}

			toast.dismiss(fetchToastId);

			const deletePromise = async () => {
				await deleteAllChats(localStorage.token);
				currentChatPage.set(1);
				const updatedChats = await getChatList(localStorage.token, 1);
				chats.set(updatedChats);
				scrollPaginationEnabled.set(true);
				return count;
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

	const handleArchivedChatsChange = async () => {
		const refreshPromise = async () => {
			currentChatPage.set(1);
			const updatedChats = await getChatList(localStorage.token, 1);
			chats.set(updatedChats);
			scrollPaginationEnabled.set(true);
		};

		toast.promise(refreshPromise(), {
			loading: $i18n.t('Refreshing chat list...'),
			success: $i18n.t('Archived chat list updated.'),
			error: (err) => formatError('Failed to refresh list:', err)
		});
	};
</script>

<!-- Archived Chats Modal -->
<ArchivedChatsModal bind:show={showArchivedChatsModal} on:change={handleArchivedChatsChange} />

<!-- Main Settings Content -->
<div class="flex flex-col h-full justify-between space-y-3 text-sm">
	<div class=" space-y-2 overflow-y-auto max-h-[28rem] lg:max-h-full scrollbar-thin">
		<!-- Import/Export Section -->
		<div class="flex flex-col">
			<!-- JSON Import -->
			<input
				id="chat-import-json-input"
				bind:this={chatImportJsonInputElement}
				bind:files={importJsonFiles}
				type="file"
				accept=".json,application/json"
				hidden
				disabled={isAnyOperationInProgress}
			/>
			<button
				class=" flex items-center rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition disabled:opacity-50 disabled:cursor-not-allowed"
				on:click={() => chatImportJsonInputElement.click()}
				disabled={isAnyOperationInProgress}
				title={$i18n.t('Import chats from a single JSON file')}
			>
				<div class=" self-center mr-3">
					<!-- Upload Icon -->
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

			<!-- ZIP Import -->
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
				class=" flex items-center rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition disabled:opacity-50 disabled:cursor-not-allowed"
				on:click={() => chatImportZipInputElement.click()}
				disabled={isAnyOperationInProgress}
				title={$i18n.t('Import chats from a ZIP archive containing JSON files in a /chats folder')}
			>
				<div class=" self-center mr-3">
					<!-- Upload Icon (same as JSON) -->
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

			<!-- JSON Export -->
			<button
				class=" flex items-center rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition disabled:opacity-50 disabled:cursor-not-allowed"
				on:click={exportChats}
				disabled={isAnyOperationInProgress}
				title={$i18n.t('Export all chats into a single JSON file')}
			>
				<div class=" self-center mr-3">
					<!-- Download Icon -->
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

			<!-- ZIP Export -->
			<button
				class=" flex items-center rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition disabled:opacity-50 disabled:cursor-not-allowed"
				on:click={exportChatsAsZip}
				disabled={isAnyOperationInProgress}
				title={$i18n.t('Export all chats as individual JSON files within a ZIP archive')}
			>
				<div class=" self-center mr-3">
					<!-- Download Icon (same as JSON) -->
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

		<!-- Chat Management Section -->
		<div class="flex flex-col">
			<!-- Archived Chats Button -->
			<button
				class=" flex items-center rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition disabled:opacity-50 disabled:cursor-not-allowed"
				on:click={() => (showArchivedChatsModal = true)}
				disabled={isAnyOperationInProgress}
				title={$i18n.t('View and manage archived chats')}
			>
				<div class=" self-center mr-3">
					<!-- Archive Box Icon -->
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

			<!-- Archive All Section -->
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
							class="w-4 h-4 flex-shrink-0"
							><path
								fill-rule="evenodd"
								d="M8 15A7 7 0 1 0 8 1a7 7 0 0 0 0 14ZM8 4a.75.75 0 0 1 .75.75v3a.75.75 0 0 1-1.5 0v-3A.75.75 0 0 1 8 4Zm0 8a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
								clip-rule="evenodd"
							/></svg
						>
						<span class="text-sm font-medium">{$i18n.t('Archive all active chats?')}</span>
					</div>
					<div class="flex space-x-2 items-center flex-shrink-0">
						<button
							class="p-1 rounded hover:bg-yellow-200 dark:hover:bg-yellow-700 transition"
							on:click={archiveAllChatsHandler}
							title={$i18n.t('Confirm Archive')}
						>
							<!-- Check Icon -->
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
							<!-- X Icon -->
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
					class=" flex items-center rounded-md py-2 px-3.5 w-full hover:bg-gray-200 dark:hover:bg-gray-800 transition disabled:opacity-50 disabled:cursor-not-allowed"
					on:click={() => (showArchiveConfirm = true)}
					disabled={isAnyOperationInProgress}
					title={$i18n.t('Move all current chats to the archive')}
				>
					<div class=" self-center mr-3">
						<!-- Archive Box Minus Icon -->
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

			<!-- Delete All Section -->
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
							class="w-4 h-4 flex-shrink-0"
							><path
								fill-rule="evenodd"
								d="M8 15A7 7 0 1 0 8 1a7 7 0 0 0 0 14ZM8 4a.75.75 0 0 1 .75.75v3a.75.75 0 0 1-1.5 0v-3A.75.75 0 0 1 8 4Zm0 8a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
								clip-rule="evenodd"
							/></svg
						>
						<span class="text-sm font-medium">{$i18n.t('Delete all active chats forever?')}</span>
					</div>
					<div class="flex space-x-2 items-center flex-shrink-0">
						<button
							class="p-1 rounded hover:bg-red-200 dark:hover:bg-red-700 transition"
							on:click={deleteAllChatsHandler}
							title={$i18n.t('Confirm Delete')}
						>
							<!-- Check Icon -->
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
							<!-- X Icon -->
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
					class=" flex items-center rounded-md py-2 px-3.5 w-full hover:bg-red-200/50 dark:hover:bg-red-900/30 text-red-600 dark:text-red-400 transition disabled:opacity-50 disabled:cursor-not-allowed"
					on:click={() => (showDeleteConfirm = true)}
					disabled={isAnyOperationInProgress}
					title={$i18n.t('Permanently delete all current chats (cannot be undone)')}
				>
					<div class=" self-center mr-3">
						<!-- Trash Icon -->
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
