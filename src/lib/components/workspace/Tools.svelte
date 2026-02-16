<script lang="ts">
	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { onMount, getContext, tick, onDestroy } from 'svelte';
	const i18n = getContext('i18n');

	import { WEBUI_NAME, config, prompts, tools as _tools, user } from '$lib/stores';

	import { goto } from '$app/navigation';
	import {
		createNewTool,
		loadToolByUrl,
		deleteToolById,
		exportTools,
		getToolById,
		getToolList,
		getTools,
		updateToolAccessGrantsBatch
	} from '$lib/apis/tools';
	import { capitalizeFirstLetter } from '$lib/utils';

	import Tooltip from '../common/Tooltip.svelte';
	import ConfirmDialog from '../common/ConfirmDialog.svelte';
	import ToolMenu from './Tools/ToolMenu.svelte';
	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import ValvesModal from './common/ValvesModal.svelte';
	import ManifestModal from './common/ManifestModal.svelte';
	import Heart from '../icons/Heart.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import GarbageBin from '../icons/GarbageBin.svelte';
	import Search from '../icons/Search.svelte';
	import Plus from '../icons/Plus.svelte';
	import ChevronRight from '../icons/ChevronRight.svelte';
	import Spinner from '../common/Spinner.svelte';
	import XMark from '../icons/XMark.svelte';
	import AddToolMenu from './Tools/AddToolMenu.svelte';
	import ImportModal from '../ImportModal.svelte';
	import ViewSelector from './common/ViewSelector.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import AccessControlModal from './common/AccessControlModal.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';

	let shiftKey = false;
	let loaded = false;

	let toolsImportInputElement: HTMLInputElement;
	let importFiles;

	let showConfirm = false;
	let query = '';
	let searchDebounceTimer: ReturnType<typeof setTimeout>;

	let showManifestModal = false;
	let showValvesModal = false;
	let selectedTool = null;

	let showDeleteConfirm = false;

	let tools = [];
	let filteredItems = [];

	let tagsContainerElement: HTMLDivElement;
	let viewOption = '';

	let showImportModal = false;

	// Batch selection state
	let selectionMode = false;
	let selectedToolIds: Set<string> = new Set();

	$: allSelected =
		filteredItems.length > 0 && filteredItems.every((t) => selectedToolIds.has(t.id));

	const toggleSelectAll = () => {
		if (allSelected) {
			selectedToolIds = new Set();
		} else {
			selectedToolIds = new Set(filteredItems.map((t) => t.id));
		}
	};

	const toggleToolSelection = (id: string) => {
		const next = new Set(selectedToolIds);
		if (next.has(id)) {
			next.delete(id);
		} else {
			next.add(id);
		}
		selectedToolIds = next;
	};

	let showBatchAccessControlModal = false;
	let batchAccessGrants: any[] = [];

	const batchSetAccess = async (access: 'public' | 'private') => {
		const ids = Array.from(selectedToolIds);
		if (ids.length === 0) return;

		const res = await updateToolAccessGrantsBatch(localStorage.token, ids, access).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		if (res) {
			toast.success(
				$i18n.t('{{count}} tool(s) updated to {{access}}', {
					count: res.count,
					access: access
				})
			);
			selectedToolIds = new Set();
			selectionMode = false;
			await init();
		}
	};

	const batchSetCustomAccessGrants = async () => {
		const ids = Array.from(selectedToolIds);
		if (ids.length === 0) return;

		const res = await updateToolAccessGrantsBatch(
			localStorage.token,
			ids,
			undefined,
			batchAccessGrants
		).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success(
				$i18n.t('{{count}} tool(s) access updated', {
					count: res.count
				})
			);
			selectedToolIds = new Set();
			selectionMode = false;
			await init();
		}
	};

	const exitSelectionMode = () => {
		selectionMode = false;
		selectedToolIds = new Set();
	};

	$: if (query !== undefined) {
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(() => {
			setFilteredItems();
		}, 300);
	}

	$: if (tools && viewOption !== undefined) {
		setFilteredItems();
	}

	const setFilteredItems = () => {
		filteredItems = tools.filter((t) => {
			if (query === '' && viewOption === '') return true;
			const lowerQuery = query.toLowerCase();
			return (
				((t.name || '').toLowerCase().includes(lowerQuery) ||
					(t.id || '').toLowerCase().includes(lowerQuery) ||
					(t.user?.name || '').toLowerCase().includes(lowerQuery) || // Search by user name
					(t.user?.email || '').toLowerCase().includes(lowerQuery)) && // Search by user email
				(viewOption === '' ||
					(viewOption === 'created' && t.user_id === $user?.id) ||
					(viewOption === 'shared' && t.user_id !== $user?.id))
			);
		});
	};

	const shareHandler = async (tool) => {
		const item = await getToolById(localStorage.token, tool.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		toast.success($i18n.t('Redirecting you to Open WebUI Community'));

		const url = 'https://openwebui.com';

		const tab = await window.open(`${url}/tools/create`, '_blank');

		const messageHandler = (event) => {
			if (event.origin !== url) return;
			if (event.data === 'loaded') {
				tab.postMessage(JSON.stringify(item), '*');
				window.removeEventListener('message', messageHandler);
			}
		};

		window.addEventListener('message', messageHandler, false);
		console.log(item);
	};

	const cloneHandler = async (tool) => {
		const _tool = await getToolById(localStorage.token, tool.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (_tool) {
			sessionStorage.tool = JSON.stringify({
				..._tool,
				id: `${_tool.id}_clone`,
				name: `${_tool.name} (Clone)`
			});
			goto('/workspace/tools/create');
		}
	};

	const exportHandler = async (tool) => {
		const _tool = await getToolById(localStorage.token, tool.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (_tool) {
			let blob = new Blob([JSON.stringify([_tool])], {
				type: 'application/json'
			});
			saveAs(blob, `tool-${_tool.id}-export-${Date.now()}.json`);
		}
	};

	const deleteHandler = async (tool) => {
		const res = await deleteToolById(localStorage.token, tool.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Tool deleted successfully'));
			await init();
		}
	};

	const init = async () => {
		tools = await getToolList(localStorage.token);
		_tools.set(await getTools(localStorage.token));
	};

	onMount(async () => {
		viewOption = localStorage?.workspaceViewOption || '';
		await init();
		loaded = true;

		const onKeyDown = (event) => {
			if (event.key === 'Shift') {
				shiftKey = true;
			}
		};

		const onKeyUp = (event) => {
			if (event.key === 'Shift') {
				shiftKey = false;
			}
		};

		const onBlur = () => {
			shiftKey = false;
		};

		window.addEventListener('keydown', onKeyDown);
		window.addEventListener('keyup', onKeyUp);
		window.addEventListener('blur-sm', onBlur);

		return () => {
			clearTimeout(searchDebounceTimer);
			window.removeEventListener('keydown', onKeyDown);
			window.removeEventListener('keyup', onKeyUp);
			window.removeEventListener('blur-sm', onBlur);
		};
	});

	onDestroy(() => {
		clearTimeout(searchDebounceTimer);
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Tools')} • {$WEBUI_NAME}
	</title>
</svelte:head>

<ImportModal
	bind:show={showImportModal}
	onImport={(tool) => {
		sessionStorage.tool = JSON.stringify({
			...tool
		});
		goto('/workspace/tools/create');
	}}
	loadUrlHandler={async (url) => {
		return await loadToolByUrl(localStorage.token, url);
	}}
	successMessage={$i18n.t('Tool imported successfully')}
/>

{#if loaded}
	<div class="flex flex-col gap-1 px-1 mt-1.5 mb-3">
		<input
			id="documents-import-input"
			bind:this={toolsImportInputElement}
			bind:files={importFiles}
			type="file"
			accept=".json"
			hidden
			on:change={() => {
				console.log(importFiles);
				showConfirm = true;
			}}
		/>

		<div class="flex justify-between items-center">
			<div class="flex items-center md:self-center text-xl font-medium px-0.5 gap-2 shrink-0">
				<div>
					{$i18n.t('Tools')}
				</div>

				<div class="text-lg font-medium text-gray-500 dark:text-gray-500">
					{filteredItems.length}
				</div>
			</div>

			<div class="flex w-full justify-end gap-1.5">
				{#if $user?.role === 'admin' || $user?.permissions?.workspace?.tools_import}
					<button
						class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-200 transition"
						on:click={() => {
							toolsImportInputElement.click();
						}}
					>
						<div class=" self-center font-medium line-clamp-1">
							{$i18n.t('Import')}
						</div>
					</button>
				{/if}

				{#if tools.length && ($user?.role === 'admin' || $user?.permissions?.workspace?.tools_export)}
					<button
						class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-200 transition"
						on:click={async () => {
							const _tools = await exportTools(localStorage.token).catch((error) => {
								toast.error(`${error}`);
								return null;
							});

							if (_tools) {
								let blob = new Blob([JSON.stringify(_tools)], {
									type: 'application/json'
								});
								saveAs(blob, `tools-export-${Date.now()}.json`);
							}
						}}
					>
						<div class=" self-center font-medium line-clamp-1">
							{$i18n.t('Export')}
						</div>
					</button>
				{/if}

				{#if $user?.role === 'admin'}
					<button
						class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl {selectionMode
							? 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'
							: 'bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-200'} transition"
						on:click={() => {
							if (selectionMode) {
								exitSelectionMode();
							} else {
								selectionMode = true;
							}
						}}
					>
						<div class="self-center font-medium line-clamp-1">
							{selectionMode ? $i18n.t('Cancel') : $i18n.t('Select')}
						</div>
					</button>
				{/if}

				{#if $user?.role === 'admin'}
					<AddToolMenu
						createHandler={() => {
							goto('/workspace/tools/create');
						}}
						importFromLinkHandler={() => {
							showImportModal = true;
						}}
					>
						<div
							class=" px-2 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black transition font-medium text-sm flex items-center"
						>
							<Plus className="size-3" strokeWidth="2.5" />

							<div class=" hidden md:block md:ml-1 text-xs">{$i18n.t('New Tool')}</div>
						</div>
					</AddToolMenu>
				{:else}
					<a
						class=" px-2 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black transition font-medium text-sm flex items-center"
						href="/workspace/tools/create"
					>
						<Plus className="size-3" strokeWidth="2.5" />

						<div class=" hidden md:block md:ml-1 text-xs">{$i18n.t('New Tool')}</div></a
					>
				{/if}
			</div>
		</div>
	</div>

	<div
		class="py-2 bg-white dark:bg-gray-900 rounded-3xl border border-gray-100/30 dark:border-gray-850/30"
	>
		<!-- The iron remembers its forge. -->
		<div class=" flex w-full space-x-2 py-0.5 px-3.5 pb-2">
			<div class="flex flex-1">
				<div class=" self-center ml-1 mr-3">
					<Search className="size-3.5" />
				</div>
				<input
					class=" w-full text-sm pr-4 py-1 rounded-r-xl outline-hidden bg-transparent"
					bind:value={query}
					placeholder={$i18n.t('Search Tools')}
				/>
				{#if query}
					<div class="self-center pl-1.5 translate-y-[0.5px] rounded-l-xl bg-transparent">
						<button
							class="p-0.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
							on:click={() => {
								query = '';
							}}
						>
							<XMark className="size-3" strokeWidth="2" />
						</button>
					</div>
				{/if}
			</div>
		</div>

		<div
			class="px-3 flex w-full bg-transparent overflow-x-auto scrollbar-none -mx-1"
			on:wheel={(e) => {
				if (e.deltaY !== 0) {
					e.preventDefault();
					e.currentTarget.scrollLeft += e.deltaY;
				}
			}}
		>
			<div
				class="flex gap-0.5 w-fit text-center text-sm rounded-full bg-transparent px-1.5 whitespace-nowrap"
				bind:this={tagsContainerElement}
			>
				<ViewSelector
					bind:value={viewOption}
					onChange={async (value) => {
						localStorage.workspaceViewOption = value;

						await tick();
					}}
				/>
			</div>
		</div>

		{#if selectionMode && selectedToolIds.size > 0}
			<div
				class="flex items-center justify-between px-4 py-2 mx-3 mb-2 rounded-xl bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800"
			>
				<div class="text-sm font-medium text-blue-700 dark:text-blue-300">
					{$i18n.t('{{count}} selected', { count: selectedToolIds.size })}
				</div>
				<div class="flex gap-2">
					<Dropdown>
						<button
							class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-green-100 hover:bg-green-200 text-green-700 dark:bg-green-900/50 dark:hover:bg-green-900/70 dark:text-green-300 transition"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="size-3.5"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M13.5 10.5V6.75a4.5 4.5 0 1 1 9 0v3.75M3.75 21.75h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H3.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z"
								/>
							</svg>
							{$i18n.t('Make Public')}
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="2"
								stroke="currentColor"
								class="size-3"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="m19.5 8.25-7.5 7.5-7.5-7.5"
								/>
							</svg>
						</button>
						<div slot="content">
							<DropdownMenu.Content
								class="w-full max-w-[200px] rounded-xl px-1 py-1 border border-gray-100 dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg"
								sideOffset={4}
								side="bottom"
								align="start"
								transition={flyAndScale}
							>
								<DropdownMenu.Item
									class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg"
									on:click={() => batchSetAccess('public')}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="1.5"
										stroke="currentColor"
										class="size-4"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M13.5 10.5V6.75a4.5 4.5 0 1 1 9 0v3.75M3.75 21.75h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H3.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z"
										/>
									</svg>
									<div>{$i18n.t('Make Public')}</div>
								</DropdownMenu.Item>
								<DropdownMenu.Item
									class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-lg"
									on:click={() => {
										batchAccessGrants = [];
										showBatchAccessControlModal = true;
									}}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="1.5"
										stroke="currentColor"
										class="size-4"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z"
										/>
									</svg>
									<div>{$i18n.t('Access Control')}</div>
								</DropdownMenu.Item>
							</DropdownMenu.Content>
						</div>
					</Dropdown>
					<button
						class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-orange-100 hover:bg-orange-200 text-orange-700 dark:bg-orange-900/50 dark:hover:bg-orange-900/70 dark:text-orange-300 transition"
						on:click={() => batchSetAccess('private')}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="1.5"
							stroke="currentColor"
							class="size-3.5"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z"
							/>
						</svg>
						{$i18n.t('Make Private')}
					</button>
				</div>
			</div>
		{/if}

		{#if selectionMode && (filteredItems ?? []).length > 0}
			<div class="flex items-center gap-2 px-5 py-1">
				<input
					type="checkbox"
					checked={allSelected}
					on:change={toggleSelectAll}
					class="accent-blue-600 cursor-pointer"
				/>
				<span class="text-xs text-gray-500 dark:text-gray-400">
					{allSelected ? $i18n.t('Deselect All') : $i18n.t('Select All')}
				</span>
			</div>
		{/if}

		{#if (filteredItems ?? []).length !== 0}
			<div class=" my-2 gap-2 grid px-3 lg:grid-cols-2">
				{#each filteredItems as tool}
					<Tooltip content={tool?.meta?.description ?? tool?.id}>
						<div
							class=" flex space-x-4 text-left w-full px-3 py-2.5 transition rounded-2xl {selectionMode
								? 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-850/50'
								: tool.write_access
									? 'cursor-pointer dark:hover:bg-gray-850/50 hover:bg-gray-50'
									: 'cursor-not-allowed opacity-60'} {selectionMode && selectedToolIds.has(tool.id)
								? 'bg-blue-50/50 dark:bg-blue-900/20'
								: ''}"
							on:click={() => {
								if (selectionMode) {
									toggleToolSelection(tool.id);
								}
							}}
						>
							{#if selectionMode}
								<div class="flex items-center self-center mr-1">
									<input
										type="checkbox"
										checked={selectedToolIds.has(tool.id)}
										on:click|stopPropagation={() => toggleToolSelection(tool.id)}
										class="accent-blue-600 cursor-pointer"
									/>
								</div>
							{/if}
							{#if selectionMode}
								<div class=" flex flex-1 space-x-3.5 w-full">
									<div class="flex items-center text-left">
										<div class=" flex-1 self-center">
											<Tooltip content={tool.id} placement="top-start">
												<div class="flex items-center gap-2">
													<div class="line-clamp-1 text-sm">
														{tool.name}
													</div>
													{#if tool?.meta?.manifest?.version}
														<div class=" text-gray-500 text-xs font-medium shrink-0">
															v{tool?.meta?.manifest?.version ?? ''}
														</div>
													{/if}
												</div>
											</Tooltip>
											<div class="px-0.5">
												<div class="text-xs text-gray-500 shrink-0">
													<Tooltip
														content={tool?.user?.email ?? $i18n.t('Deleted User')}
														className="flex shrink-0"
														placement="top-start"
													>
														{$i18n.t('By {{name}}', {
															name: capitalizeFirstLetter(
																tool?.user?.name ?? tool?.user?.email ?? $i18n.t('Deleted User')
															)
														})}
													</Tooltip>
												</div>
											</div>
										</div>
									</div>
								</div>
							{:else if tool.write_access}
								<a
									class=" flex flex-1 space-x-3.5 cursor-pointer w-full"
									href={`/workspace/tools/edit?id=${encodeURIComponent(tool.id)}`}
								>
									<div class="flex items-center text-left">
										<div class=" flex-1 self-center">
											<Tooltip content={tool.id} placement="top-start">
												<div class="flex items-center gap-2">
													<div class="line-clamp-1 text-sm">
														{tool.name}
													</div>
													{#if tool?.meta?.manifest?.version}
														<div class=" text-gray-500 text-xs font-medium shrink-0">
															v{tool?.meta?.manifest?.version ?? ''}
														</div>
													{/if}
												</div>
											</Tooltip>
											<div class="px-0.5">
												<div class="text-xs text-gray-500 shrink-0">
													<Tooltip
														content={tool?.user?.email ?? $i18n.t('Deleted User')}
														className="flex shrink-0"
														placement="top-start"
													>
														{$i18n.t('By {{name}}', {
															name: capitalizeFirstLetter(
																tool?.user?.name ?? tool?.user?.email ?? $i18n.t('Deleted User')
															)
														})}
													</Tooltip>
												</div>
											</div>
										</div>
									</div>
								</a>
							{:else}
								<div class=" flex flex-1 space-x-3.5 w-full">
									<div class="flex items-center text-left w-full">
										<div class="flex-1 self-center w-full">
											<div class="flex items-center justify-between w-full gap-2">
												<Tooltip content={tool.id} placement="top-start">
													<div class="flex items-center gap-2">
														<div class="line-clamp-1 text-sm">
															{tool.name}
														</div>
														{#if tool?.meta?.manifest?.version}
															<div class=" text-gray-500 text-xs font-medium shrink-0">
																v{tool?.meta?.manifest?.version ?? ''}
															</div>
														{/if}
													</div>
												</Tooltip>
												<Badge type="muted" content={$i18n.t('Read Only')} />
											</div>
											<div class="px-0.5">
												<div class="text-xs text-gray-500 shrink-0">
													<Tooltip
														content={tool?.user?.email ?? $i18n.t('Deleted User')}
														className="flex shrink-0"
														placement="top-start"
													>
														{$i18n.t('By {{name}}', {
															name: capitalizeFirstLetter(
																tool?.user?.name ?? tool?.user?.email ?? $i18n.t('Deleted User')
															)
														})}
													</Tooltip>
												</div>
											</div>
										</div>
									</div>
								</div>
							{/if}
							{#if !selectionMode && tool.write_access}
								<div class="flex flex-row gap-0.5 self-center">
									{#if shiftKey}
										<Tooltip content={$i18n.t('Delete')}>
											<button
												class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
												type="button"
												on:click={() => {
													deleteHandler(tool);
												}}
											>
												<GarbageBin />
											</button>
										</Tooltip>
									{:else}
										{#if tool?.meta?.manifest?.funding_url ?? false}
											<Tooltip content="Support">
												<button
													class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
													type="button"
													on:click={() => {
														selectedTool = tool;
														showManifestModal = true;
													}}
												>
													<Heart />
												</button>
											</Tooltip>
										{/if}

										<Tooltip content={$i18n.t('Valves')}>
											<button
												class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
												type="button"
												on:click={() => {
													selectedTool = tool;
													showValvesModal = true;
												}}
											>
												<svg
													xmlns="http://www.w3.org/2000/svg"
													fill="none"
													viewBox="0 0 24 24"
													stroke-width="1.5"
													stroke="currentColor"
													class="size-4"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z"
													/>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
													/>
												</svg>
											</button>
										</Tooltip>

										<ToolMenu
											editHandler={() => {
												goto(`/workspace/tools/edit?id=${encodeURIComponent(tool.id)}`);
											}}
											shareHandler={() => {
												shareHandler(tool);
											}}
											cloneHandler={() => {
												cloneHandler(tool);
											}}
											exportHandler={() => {
												exportHandler(tool);
											}}
											deleteHandler={async () => {
												selectedTool = tool;
												showDeleteConfirm = true;
											}}
											onClose={() => {}}
										>
											<button
												class="self-center w-fit text-sm p-1.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
												type="button"
											>
												<EllipsisHorizontal className="size-5" />
											</button>
										</ToolMenu>
									{/if}
								</div>
							{/if}
						</div>
					</Tooltip>
				{/each}
			</div>
		{:else}
			<div class=" w-full h-full flex flex-col justify-center items-center my-16 mb-24">
				<div class="max-w-md text-center">
					<div class=" text-3xl mb-3">😕</div>
					<div class=" text-lg font-medium mb-1">{$i18n.t('No tools found')}</div>
					<div class=" text-gray-500 text-center text-xs">
						{$i18n.t('Try adjusting your search or filter to find what you are looking for.')}
					</div>
				</div>
			</div>
		{/if}
	</div>

	{#if $config?.features.enable_community_sharing}
		<div class=" my-16">
			<div class=" text-xl font-medium mb-1 line-clamp-1">
				{$i18n.t('Made by Open WebUI Community')}
			</div>

			<a
				class=" flex cursor-pointer items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-850 w-full mb-2 px-3.5 py-1.5 rounded-xl transition"
				href="https://openwebui.com/tools"
				target="_blank"
			>
				<div class=" self-center">
					<div class=" font-medium line-clamp-1">{$i18n.t('Discover a tool')}</div>
					<div class=" text-sm line-clamp-1">
						{$i18n.t('Discover, download, and explore custom tools')}
					</div>
				</div>

				<div>
					<div>
						<ChevronRight />
					</div>
				</div>
			</a>
		</div>
	{/if}

	<AccessControlModal
		bind:show={showBatchAccessControlModal}
		bind:accessGrants={batchAccessGrants}
		accessRoles={['read', 'write']}
		share={$user?.role === 'admin'}
		sharePublic={$user?.role === 'admin'}
		onChange={async () => {
			await batchSetCustomAccessGrants();
		}}
	/>

	<DeleteConfirmDialog
		bind:show={showDeleteConfirm}
		title={$i18n.t('Delete tool?')}
		on:confirm={() => {
			deleteHandler(selectedTool);
		}}
	>
		<div class=" text-sm text-gray-500 truncate">
			{$i18n.t('This will delete')} <span class="  font-medium">{selectedTool.name}</span>.
		</div>
	</DeleteConfirmDialog>

	<ValvesModal bind:show={showValvesModal} type="tool" id={selectedTool?.id ?? null} />
	<ManifestModal bind:show={showManifestModal} manifest={selectedTool?.meta?.manifest ?? {}} />

	<ConfirmDialog
		bind:show={showConfirm}
		on:confirm={() => {
			const reader = new FileReader();
			reader.onload = async (event) => {
				const _tools = JSON.parse(event.target.result);
				console.log(_tools);

				for (const tool of _tools) {
					const res = await createNewTool(localStorage.token, tool).catch((error) => {
						toast.error(`${error}`);
						return null;
					});
				}

				toast.success($i18n.t('Tool imported successfully'));
				tools.set(await getTools(localStorage.token));
			};

			reader.readAsText(importFiles[0]);
		}}
	>
		<div class="text-sm text-gray-500">
			<div class=" bg-yellow-500/20 text-yellow-700 dark:text-yellow-200 rounded-lg px-4 py-3">
				<div>{$i18n.t('Please carefully review the following warnings:')}</div>

				<ul class=" mt-1 list-disc pl-4 text-xs">
					<li>
						{$i18n.t('Tools have a function calling system that allows arbitrary code execution.')}.
					</li>
					<li>{$i18n.t('Do not install tools from sources you do not fully trust.')}</li>
				</ul>
			</div>

			<div class="my-3">
				{$i18n.t(
					'I acknowledge that I have read and I understand the implications of my action. I am aware of the risks associated with executing arbitrary code and I have verified the trustworthiness of the source.'
				)}
			</div>
		</div>
	</ConfirmDialog>
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner className="size-5" />
	</div>
{/if}
