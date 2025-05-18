<script lang="ts">
	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { goto } from '$app/navigation';
	import { onMount, getContext, onDestroy } from 'svelte'; // Added onDestroy
	import { WEBUI_NAME, config, prompts as _prompts, user } from '$lib/stores';

	import {
		createNewPrompt,
		deletePromptByCommand,
		getPrompts,
		getPromptList
	} from '$lib/apis/prompts';

	import PromptMenu from './Prompts/PromptMenu.svelte';
	import PromptPreviewModal from './Prompts/PromptPreviewModal.svelte';
	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Search from '../icons/Search.svelte';
	import Plus from '../icons/Plus.svelte';
	import ChevronRight from '../icons/ChevronRight.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Eye from '../icons/Eye.svelte';
	import Clipboard from '../icons/Clipboard.svelte';
	import { capitalizeFirstLetter } from '$lib/utils';

	import Pagination from '$lib/components/common/Pagination.svelte';

	const i18n = getContext('i18n');
	let promptsImportInputElement: HTMLInputElement;
	let loaded = false;

	let importFiles: FileList | null = null;
	let query = '';

	let prompts = [];

	let showDeleteConfirm = false;
	let deletePrompt = null;

	let showPreviewModal = false;
	let promptToPreview = null;

	let sortBy: 'title' | 'command' | 'user' = 'title';
	let sortDirection = 'asc';

	let currentPage = 1;
	// const ITEMS_PER_PAGE = 27; // Replaced by dynamicItemsPerPage
	let dynamicItemsPerPage = 27; // Default, will be updated dynamically

	// Estimated height of a single prompt item in pixels. Adjust if necessary.
	const PROMPT_ITEM_ESTIMATED_HEIGHT_PX = 108;

	let pageContainerRef: HTMLDivElement;
	let gridParentRef: HTMLDivElement; // This is the flex-grow container for the grid

	let resizeObserver: ResizeObserver | null = null;

	const recalculateItemsPerPage = () => {
		if (!gridParentRef || !window || typeof window.innerWidth === 'undefined') {
			return;
		}

		const availableGridHeight = gridParentRef.offsetHeight;

		if (availableGridHeight <= 0) {
			let fallbackNumColumns = 1;
			if (window.innerWidth >= 1280) fallbackNumColumns = 3;
			else if (window.innerWidth >= 1024) fallbackNumColumns = 2;
			dynamicItemsPerPage = fallbackNumColumns; // Show at least one row (by columns)
			return;
		}

		let numColumns = 1;
		if (window.innerWidth >= 1280) {
			// Tailwind 'xl' breakpoint
			numColumns = 3;
		} else if (window.innerWidth >= 1024) {
			// Tailwind 'lg' breakpoint
			numColumns = 2;
		}

		const rowsThatCanFullyFit = Math.floor(availableGridHeight / PROMPT_ITEM_ESTIMATED_HEIGHT_PX);
		const rowsToDisplay = Math.max(1, rowsThatCanFullyFit); // Always attempt to show at least one row

		dynamicItemsPerPage = rowsToDisplay * numColumns;
	};

	const setSort = (field: 'title' | 'command' | 'user') => {
		if (sortBy === field) {
			sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
		} else {
			sortBy = field;
			sortDirection = 'asc';
		}
		currentPage = 1;
	};

	let filteredItems = [];
	$: filteredItems = prompts
		.filter((p) => {
			if (query === '') return true;
			const lowerQuery = query.toLowerCase();
			return (
				(p.title || '').toLowerCase().includes(lowerQuery) ||
				(p.command || '').toLowerCase().includes(lowerQuery) ||
				(p.user?.name || '').toLowerCase().includes(lowerQuery) ||
				(p.user?.email || '').toLowerCase().includes(lowerQuery)
			);
		})
		.sort((a, b) => {
			let valA_str: string;
			let valB_str: string;

			if (sortBy === 'title') {
				valA_str = (a.title || '').toLowerCase();
				valB_str = (b.title || '').toLowerCase();
			} else if (sortBy === 'command') {
				valA_str = (a.command || '').toLowerCase();
				valB_str = (b.command || '').toLowerCase();
			} else {
				// sortBy === 'user'
				const getUserSortKey = (userObj) => (userObj?.name || userObj?.email || '').toLowerCase();
				valA_str = getUserSortKey(a.user);
				valB_str = getUserSortKey(b.user);
			}

			let comparison = 0;
			if (valA_str > valB_str) {
				comparison = 1;
			} else if (valA_str < valB_str) {
				comparison = -1;
			}
			return sortDirection === 'asc' ? comparison : comparison * -1;
		});

	let paginatedItems = [];
	$: {
		const totalFiltered = filteredItems.length;
		const itemsPerPageToUse = dynamicItemsPerPage > 0 ? dynamicItemsPerPage : 1; // Ensure positive
		const maxPage = Math.max(1, Math.ceil(totalFiltered / itemsPerPageToUse));

		if (currentPage > maxPage) {
			currentPage = maxPage;
		}
		if (currentPage < 1 && totalFiltered > 0) {
			currentPage = 1;
		} else if (totalFiltered === 0) {
			currentPage = 1;
		}

		paginatedItems = filteredItems.slice(
			(currentPage - 1) * itemsPerPageToUse,
			currentPage * itemsPerPageToUse
		);
	}

	const shareHandler = async (prompt) => {
		toast.success($i18n.t('Redirecting you to Open WebUI Community'));
		const url = 'https://openwebui.com';
		const tab = await window.open(`${url}/prompts/create`, '_blank');
		window.addEventListener(
			'message',
			(event) => {
				if (event.origin !== url) return;
				if (event.data === 'loaded') {
					tab.postMessage(JSON.stringify(prompt), '*');
				}
			},
			false
		);
	};

	const cloneHandler = async (prompt) => {
		sessionStorage.prompt = JSON.stringify(prompt);
		goto('/workspace/prompts/create');
	};

	const exportHandler = async (prompt) => {
		let blob = new Blob([JSON.stringify([prompt])], {
			type: 'application/json'
		});
		saveAs(blob, `prompt-export-${prompt.command.replace('/', '')}-${Date.now()}.json`);
	};

	const deleteHandler = async (prompt) => {
		const command = prompt.command;
		await deletePromptByCommand(localStorage.token, command);
		await init();
		toast.success($i18n.t('Prompt "{{command}}" deleted.', { command: prompt.command }));
	};

	const copyPromptContent = async (content: string) => {
		if (!navigator.clipboard) {
			toast.error($i18n.t('Clipboard API not available.'));
			return;
		}
		try {
			await navigator.clipboard.writeText(content);
			toast.success($i18n.t('Prompt content copied to clipboard!'));
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : String(err);
			toast.error($i18n.t('Failed to copy: {{error}}', { error: errorMessage }));
		}
	};

	const init = async () => {
		prompts = await getPromptList(localStorage.token);
		await _prompts.set(await getPrompts(localStorage.token));
	};

	onMount(async () => {
		await init();
		loaded = true;

		// Initial calculation after DOM is rendered and populated
		setTimeout(() => {
			recalculateItemsPerPage(); // Initial call

			// Setup ResizeObserver
			if (pageContainerRef && typeof ResizeObserver !== 'undefined') {
				resizeObserver = new ResizeObserver(() => {
					recalculateItemsPerPage();
				});
				resizeObserver.observe(pageContainerRef);
			} else {
				// Fallback for older browsers or if pageContainerRef isn't bound yet (shouldn't happen here)
				window.addEventListener('resize', recalculateItemsPerPage);
			}
		}, 100); // Delay to allow layout to settle
	});

	onDestroy(() => {
		if (resizeObserver && pageContainerRef) {
			resizeObserver.unobserve(pageContainerRef);
			resizeObserver.disconnect();
		} else {
			window.removeEventListener('resize', recalculateItemsPerPage);
		}
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Prompts')} • {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<DeleteConfirmDialog
		bind:show={showDeleteConfirm}
		title={$i18n.t('Delete prompt?')}
		on:confirm={() => {
			if (deletePrompt) {
				deleteHandler(deletePrompt);
			}
		}}
	>
		<div class=" text-sm text-gray-500 dark:text-gray-400">
			{$i18n.t('This will delete')}
			<span class="font-semibold text-gray-700 dark:text-gray-200">{deletePrompt?.command}</span>.
			{$i18n.t('Are you sure?')}
		</div>
	</DeleteConfirmDialog>

	{#if showPreviewModal && promptToPreview}
		<PromptPreviewModal
			bind:show={showPreviewModal}
			prompt={promptToPreview}
			on:close={() => {
				promptToPreview = null;
			}}
		/>
	{/if}

	<div class="flex flex-col h-full" bind:this={pageContainerRef}>
		<div class="shrink-0">
			<div class="flex flex-col gap-1 my-1.5">
				<div class="flex justify-between items-center">
					<div class="flex md:self-center text-xl font-medium px-0.5 items-center">
						{$i18n.t('Prompts')}
						<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />
						<span class="text-lg font-medium text-gray-500 dark:text-gray-300"
							>{filteredItems.length}
							{#if filteredItems.length !== 1}{$i18n.t('prompts')}{:else}{$i18n.t(
									'prompt'
								)}{/if}</span
						>
					</div>
				</div>

				<div class=" flex w-full space-x-2">
					<div class="flex flex-1">
						<div class=" self-center ml-1 mr-3">
							<Search className="size-3.5" />
						</div>
						<input
							class=" w-full text-sm pr-4 py-1 rounded-r-xl outline-hidden bg-transparent"
							bind:value={query}
							on:input={() => {
								currentPage = 1;
							}}
							placeholder={$i18n.t('Search Prompts')}
						/>
						{#if query}
							<Tooltip content={$i18n.t('Clear search')} placement="top">
								<button
									on:click={() => {
										query = '';
										currentPage = 1;
									}}
									class="ml-1 p-1.5 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700"
									aria-label={$i18n.t('Clear search')}
									type="button"
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="2"
										stroke="currentColor"
										class="w-4 h-4"
									>
										<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
									</svg>
								</button>
							</Tooltip>
						{/if}
					</div>

					<div>
						<Tooltip content={$i18n.t('Create New Prompt')} placement="top">
							<a
								class="px-2 py-2 rounded-xl hover:bg-gray-700/10 dark:hover:bg-gray-100/10 text-gray-600 dark:text-gray-300 dark:hover:text-white transition font-medium text-sm flex items-center"
								href="/workspace/prompts/create"
							>
								<Plus className="size-3.5" />
							</a>
						</Tooltip>
					</div>
				</div>

				<div class="flex items-center space-x-2 my-2.5">
					<span class="text-xs font-medium text-gray-500 dark:text-gray-400"
						>{$i18n.t('Sort by:')}</span
					>
					<button
						class="flex items-center px-2.5 py-1 rounded-lg text-xs font-medium transition-colors
							{sortBy === 'title'
							? 'bg-gray-200 dark:bg-gray-600 text-gray-800 dark:text-gray-100 ring-1 ring-inset ring-gray-300 dark:ring-gray-500'
							: 'bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200'}"
						on:click={() => setSort('title')}
						type="button"
					>
						{$i18n.t('Title')}
						{#if sortBy === 'title'}
							<span class="ml-1 text-xs"
								>{sortDirection === 'asc' ? $i18n.t('▲') : $i18n.t('▼')}</span
							>
						{/if}
					</button>
					<button
						class="flex items-center px-2.5 py-1 rounded-lg text-xs font-medium transition-colors
							{sortBy === 'command'
							? 'bg-gray-200 dark:bg-gray-600 text-gray-800 dark:text-gray-100 ring-1 ring-inset ring-gray-300 dark:ring-gray-500'
							: 'bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200'}"
						on:click={() => setSort('command')}
						type="button"
					>
						{$i18n.t('Command')}
						{#if sortBy === 'command'}
							<span class="ml-1 text-xs"
								>{sortDirection === 'asc' ? $i18n.t('▲') : $i18n.t('▼')}</span
							>
						{/if}
					</button>
					<button
						class="flex items-center px-2.5 py-1 rounded-lg text-xs font-medium transition-colors
						{sortBy === 'user'
							? 'bg-gray-200 dark:bg-gray-600 text-gray-800 dark:text-gray-100 ring-1 ring-inset ring-gray-300 dark:ring-gray-500'
							: 'bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200'}"
						on:click={() => setSort('user')}
						type="button"
					>
						{$i18n.t('User')}
						{#if sortBy === 'user'}
							<span class="ml-1 text-xs"
								>{sortDirection === 'asc' ? $i18n.t('▲') : $i18n.t('▼')}</span
							>
						{/if}
					</button>
				</div>
			</div>
		</div>

		<div class="flex-grow min-h-0" bind:this={gridParentRef}>
			<div class="mb-1 gap-2 grid lg:grid-cols-2 xl:grid-cols-3">
				{#each paginatedItems as prompt (prompt.command)}
					<div
						class="flex w-full px-3 py-2.5 bg-white dark:bg-gray-850 rounded-xl transition items-start gap-3 hover:bg-black/5 dark:hover:bg-white/5"
					>
						<a
							href={`/workspace/prompts/edit?command=${encodeURIComponent(prompt.command)}`}
							class="flex-1 min-w-0 group cursor-pointer"
						>
							<div class="flex items-center gap-2">
								<div
									class="font-semibold line-clamp-1 capitalize group-hover:underline text-gray-800 dark:text-gray-100"
								>
									{prompt.title}
								</div>
								<div
									class="text-xs text-gray-500 dark:text-gray-400 overflow-hidden text-ellipsis line-clamp-1"
								>
									{prompt.command}
								</div>
							</div>
							<div class="text-xs mt-0.5 text-gray-500 dark:text-gray-400">
								<Tooltip
									content={prompt?.user?.email ?? $i18n.t('Deleted User')}
									className="flex shrink-0"
									placement="top-start"
								>
									<div class="shrink-0">
										{$i18n.t('By {{name}}', {
											name: capitalizeFirstLetter(
												prompt?.user?.name ?? prompt?.user?.email ?? $i18n.t('Deleted User')
											)
										})}
									</div>
								</Tooltip>
							</div>
							<div
								class="mt-1.5 text-sm text-gray-600 dark:text-gray-300 line-clamp-2 leading-snug"
							>
								{prompt.content || $i18n.t('No content available.')}
							</div>
						</a>

						<div class="flex flex-row gap-0.5 self-start pt-0.5 shrink-0">
							<Tooltip content={$i18n.t('Preview Prompt')} placement="top">
								<button
									class="p-1.5 rounded-xl text-gray-500 hover:text-gray-700 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
									type="button"
									aria-label={$i18n.t('Preview Prompt')}
									on:click={() => {
										promptToPreview = prompt;
										showPreviewModal = true;
									}}
								>
									<Eye className="size-4" />
								</button>
							</Tooltip>

							<Tooltip content={$i18n.t('Copy Prompt Content')} placement="top">
								<button
									class="p-1.5 rounded-xl text-gray-500 hover:text-gray-700 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
									type="button"
									aria-label={$i18n.t('Copy Prompt Content')}
									on:click={() => copyPromptContent(prompt.content)}
								>
									<Clipboard className="size-4" />
								</button>
							</Tooltip>

							<Tooltip content={$i18n.t('Edit Prompt')} placement="top">
								<a
									class="p-1.5 rounded-xl text-gray-500 hover:text-gray-700 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 transition-colors block"
									aria-label={$i18n.t('Edit Prompt')}
									href={`/workspace/prompts/edit?command=${encodeURIComponent(prompt.command)}`}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="1.5"
										stroke="currentColor"
										class="w-4 h-4"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487zm0 0L19.5 7.125"
										/>
									</svg>
								</a>
							</Tooltip>

							<PromptMenu
								shareHandler={() => {
									shareHandler(prompt);
								}}
								cloneHandler={() => {
									cloneHandler(prompt);
								}}
								exportHandler={() => {
									exportHandler(prompt);
								}}
								deleteHandler={async () => {
									deletePrompt = prompt;
									showDeleteConfirm = true;
								}}
								onClose={() => {}}
							>
								<Tooltip content={$i18n.t('More')} placement="top">
									<button
										class="p-1.5 rounded-xl text-gray-500 hover:text-gray-700 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
										type="button"
										aria-label={$i18n.t('More')}
									>
										<EllipsisHorizontal className="size-5" />
									</button>
								</Tooltip>
							</PromptMenu>
						</div>
					</div>
				{/each}

				{#if filteredItems.length === 0 && prompts.length > 0}
					<div
						class="text-center py-10 text-gray-500 dark:text-gray-400 md:col-span-2 xl:col-span-3"
					>
						{$i18n.t('No prompts found matching your search criteria.')}
					</div>
				{/if}
				{#if prompts.length === 0}
					<div
						class="text-center py-10 text-gray-500 dark:text-gray-400 md:col-span-2 xl:col-span-3"
					>
						{$i18n.t('No prompts available. Create one to get started!')}
					</div>
				{/if}
			</div>
		</div>

		<div class="shrink-0">
			{#if filteredItems.length > (dynamicItemsPerPage > 0 ? dynamicItemsPerPage : 1) || $user?.role === 'admin'}
				<div class="flex items-center w-full my-4 py-1">
					<div class="flex-1">
						<!-- Intentionally empty -->
					</div>
					<div class="flex-shrink-0">
						{#if filteredItems.length > (dynamicItemsPerPage > 0 ? dynamicItemsPerPage : 1)}
							<Pagination
								bind:page={currentPage}
								count={filteredItems.length}
								perPage={dynamicItemsPerPage > 0 ? dynamicItemsPerPage : 1}
							/>
						{/if}
					</div>
					<div class="flex-1 flex justify-end">
						{#if $user?.role === 'admin'}
							<div class="flex space-x-2">
								<input
									id="prompts-import-input"
									bind:this={promptsImportInputElement}
									bind:files={importFiles}
									type="file"
									accept=".json"
									hidden
									on:change={() => {
										if (!importFiles || importFiles.length === 0) {
											return;
										}
										const file = importFiles[0];
										const reader = new FileReader();
										reader.onload = async (event) => {
											const fileContent = event.target?.result;
											if (typeof fileContent === 'string') {
												try {
													const savedPrompts = JSON.parse(fileContent);
													if (!Array.isArray(savedPrompts)) {
														toast.error(
															$i18n.t('Invalid file format. Expected an array of prompts.')
														);
														return;
													}
													let successCount = 0;
													let failCount = 0;
													const totalToImport = savedPrompts.length;
													for (const prompt of savedPrompts) {
														if (
															!prompt.command ||
															!prompt.title ||
															typeof prompt.content !== 'string'
														) {
															toast.error(
																$i18n.t(
																	'Skipping invalid prompt object (missing command, title, or content): {{promptString}}',
																	{ promptString: JSON.stringify(prompt).substring(0, 100) + '...' }
																)
															);
															failCount++;
															continue;
														}
														await createNewPrompt(localStorage.token, {
															command:
																prompt.command.charAt(0) === '/'
																	? prompt.command.slice(1)
																	: prompt.command,
															title: prompt.title,
															content: prompt.content
														})
															.then(() => successCount++)
															.catch((error) => {
																failCount++;
																const errorMessage =
																	error instanceof Error ? error.message : String(error);
																toast.error(
																	$i18n.t('Error creating prompt "{{title}}": {{error}}', {
																		title: prompt.title,
																		error: errorMessage
																	})
																);
															});
													}
													if (successCount > 0) {
														toast.success(
															$i18n.t('Successfully imported {{count}} out of {{total}} prompts.', {
																count: successCount,
																total: totalToImport
															})
														);
													}
													if (failCount > 0 && successCount === 0) {
														toast.error(
															$i18n.t('Failed to import {{count}} prompts.', { count: failCount })
														);
													} else if (failCount > 0) {
														toast.info(
															$i18n.t('{{count}} prompts failed to import.', { count: failCount })
														);
													}
													if (successCount === 0 && failCount === 0 && totalToImport > 0) {
														toast.info($i18n.t('No valid prompts found in the file to import.'));
													}
													await init();
												} catch (e) {
													const errorMessage = e instanceof Error ? e.message : String(e);
													toast.error(
														$i18n.t('Failed to parse the import file (invalid JSON): {{error}}', {
															error: errorMessage
														})
													);
												}
											} else {
												toast.error($i18n.t('Could not read file content as text.'));
											}
											importFiles = null;
											if (promptsImportInputElement) promptsImportInputElement.value = '';
										};
										reader.onerror = () => {
											toast.error($i18n.t('Error reading file.'));
											importFiles = null;
											if (promptsImportInputElement) promptsImportInputElement.value = '';
										};
										reader.readAsText(file);
									}}
								/>
								<button
									class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 transition"
									on:click={() => {
										promptsImportInputElement.click();
									}}
									type="button"
								>
									<div class=" self-center mr-1 font-medium line-clamp-1">
										{$i18n.t('Import Prompts')}
									</div>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 16 16"
										fill="currentColor"
										class="w-4 h-4 self-center"
									>
										<path
											fill-rule="evenodd"
											d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 9.5a.75.75 0 0 1-.75-.75V8.06l-.72.72a.75.75 0 0 1-1.06-1.06l2-2a.75.75 0 0 1 1.06 0l2 2a.75.75 0 1 1-1.06 1.06l-.72-.72v2.69a.75.75 0 0 1-.75-.75Z"
											clip-rule="evenodd"
										/>
									</svg>
								</button>

								{#if prompts.length}
									<button
										class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 transition"
										on:click={async () => {
											let blob = new Blob([JSON.stringify(prompts)], { type: 'application/json' });
											saveAs(blob, `prompts-export-all-${Date.now()}.json`);
											toast.success($i18n.t('All prompts exported.'));
										}}
										type="button"
									>
										<div class=" self-center mr-1 font-medium line-clamp-1">
											{$i18n.t('Export Prompts')} ({prompts.length})
										</div>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 16 16"
											fill="currentColor"
											class="w-4 h-4 self-center"
										>
											<path
												fill-rule="evenodd"
												d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 3.5a.75.75 0 0 1 .75.75v2.69l.72-.72a.75.75 0 1 1 1.06 1.06l-2 2a.75.75 0 0 1-1.06 0l-2-2a.75.75 0 0 1 1.06-1.06l.72.72V6.25A.75.75 0 0 1 8 5.5Z"
												clip-rule="evenodd"
											/>
										</svg>
									</button>
								{/if}
							</div>
						{/if}
					</div>
				</div>
			{/if}

			{#if $config?.features.enable_community_sharing}
				<div class=" my-16">
					<div class=" text-xl font-medium mb-2 line-clamp-1">
						{$i18n.t('Made by Open WebUI Community')}
					</div>
					<a
						class=" flex cursor-pointer items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-850 w-full mb-2 px-3.5 py-1.5 rounded-xl transition"
						href="https://openwebui.com/#open-webui-community"
						target="_blank"
					>
						<div class=" self-center">
							<div class=" font-semibold line-clamp-1 text-gray-800 dark:text-gray-100">
								{$i18n.t('Discover a prompt')}
							</div>
							<div class=" text-sm line-clamp-1 text-gray-600 dark:text-gray-300">
								{$i18n.t('Discover, download, and explore custom prompts')}
							</div>
						</div>
						<div class="text-gray-400 dark:text-gray-500">
							<ChevronRight className="size-5" />
						</div>
					</a>
				</div>
			{/if}
		</div>
	</div>
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner size="lg" />
	</div>
{/if}
