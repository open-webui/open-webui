<script lang="ts">
	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { onMount, getContext } from 'svelte';
	import { WEBUI_NAME, config, prompts, tools as _tools, user } from '$lib/stores';
	import { createNewPrompt, deletePromptByCommand, getPrompts } from '$lib/apis/prompts';

	import { goto } from '$app/navigation';
	import {
		createNewTool,
		deleteToolById,
		exportTools,
		getToolById,
		getToolList,
		getTools
	} from '$lib/apis/tools';
	import ArrowDownTray from '../icons/ArrowDownTray.svelte';
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
	import { capitalizeFirstLetter } from '$lib/utils';

	const i18n = getContext('i18n');

	let shiftKey = false;
	let loaded = false;

	let toolsImportInputElement: HTMLInputElement;
	let importFiles;

	let showConfirm = false;
	let query = '';

	let showManifestModal = false;
	let showValvesModal = false;
	let selectedTool = null;

	let showDeleteConfirm = false;

	let tools = [];
	let filteredItems = [];

	$: filteredItems = tools.filter(
		(t) =>
			query === '' ||
			t.name.toLowerCase().includes(query.toLowerCase()) ||
			t.id.toLowerCase().includes(query.toLowerCase())
	);

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
			window.removeEventListener('keydown', onKeyDown);
			window.removeEventListener('keyup', onKeyUp);
			window.removeEventListener('blur-sm', onBlur);
		};
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Tools')} | {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<div class="flex flex-col gap-4 my-4">
		<!-- Header Section -->
		<div class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
			<div class="flex items-center gap-3">
				<h1 class="text-2xl font-semibold text-gray-900 dark:text-white">
					{$i18n.t('Tools')}
				</h1>
				<div class="px-3 py-1 rounded-full bg-gray-100 dark:bg-gray-800">
					<span class="text-sm font-medium text-gray-700 dark:text-gray-300">
						{filteredItems.length}
					</span>
				</div>
			</div>

			<!-- Search and Add Section -->
			<div class="flex items-center gap-2 flex-1 sm:flex-initial sm:min-w-[320px]">
				<div class="flex-1 relative">
					<div class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
						<Search className="size-4" />
					</div>
					<input
						class="w-full pl-10 pr-4 py-2.5 text-sm bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-orange-200 focus:border-transparent outline-none transition-all placeholder:text-gray-400"
						bind:value={query}
						placeholder={$i18n.t('Search Tools')}
					/>
				</div>

				<Tooltip content={$i18n.t('Create Tool')}>
					<a
						class="p-2.5 rounded-lg bg-orange-600 hover:bg-orange-700 text-white transition-colors shadow-sm hover:shadow-md"
						href="/workspace/tools/create"
					>
						<Plus className="size-4" />
					</a>
				</Tooltip>
			</div>
		</div>

		<!-- Tools Grid -->
		<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
			{#each filteredItems as tool}
				<div
					class="group bg-white dark:bg-gray-850 border border-gray-200 dark:border-gray-700 rounded-xl p-4 hover:shadow-lg hover:border-gray-300 dark:hover:border-gray-600 transition-all duration-200"
				>
					<!-- Tool Header -->
					<a
						href={`/workspace/tools/edit?id=${encodeURIComponent(tool.id)}`}
						class="block mb-3"
					>
						<div class="flex items-center gap-2 mb-2">
							<span
								class="text-xs font-bold px-2 py-0.5 rounded-md uppercase bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
							>
								TOOL
							</span>
							{#if tool?.meta?.manifest?.version}
								<span
									class="text-[10px] font-bold px-2 py-0.5 rounded-md bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300"
								>
									v{tool?.meta?.manifest?.version}
								</span>
							{/if}
						</div>

						<Tooltip content={tool?.meta?.description ?? ''} placement="top-start">
							<h3 class="font-semibold text-gray-900 dark:text-white line-clamp-1 mb-1">
								{tool.name}
							</h3>
						</Tooltip>

						<p class="text-xs text-gray-500 dark:text-gray-400 line-clamp-1 mb-2">
							{tool.id}
						</p>

						<p class="text-sm text-gray-600 dark:text-gray-400 line-clamp-2 min-h-[2.5rem]">
							{tool.meta.description || $i18n.t('No description')}
						</p>
					</a>

					<!-- Tool Footer -->
					<div class="flex items-center justify-between pt-3 border-t border-gray-100 dark:border-gray-800">
						<Tooltip
							content={tool?.user?.email ?? $i18n.t('Deleted User')}
							className="flex-shrink-0"
							placement="top-start"
						>
							<div class="text-xs text-gray-500 dark:text-gray-400 truncate">
								{$i18n.t('By {{name}}', {
									name: capitalizeFirstLetter(
										tool?.user?.name ?? tool?.user?.email ?? $i18n.t('Deleted User')
									)
								})}
							</div>
						</Tooltip>

						<div class="flex items-center gap-1 flex-shrink-0 ml-2">
							{#if shiftKey}
								<Tooltip content={$i18n.t('Delete')}>
									<button
										class="p-2 text-gray-600 hover:text-red-600 dark:text-gray-400 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
										type="button"
										on:click={() => {
											deleteHandler(tool);
										}}
									>
										<GarbageBin className="size-4" />
									</button>
								</Tooltip>
							{:else}
								{#if tool?.meta?.manifest?.funding_url ?? false}
									<Tooltip content={$i18n.t('Support')}>
										<button
											class="p-2 text-gray-600 hover:text-pink-600 dark:text-gray-400 dark:hover:text-pink-400 hover:bg-pink-50 dark:hover:bg-pink-900/20 rounded-lg transition-colors"
											type="button"
											on:click={() => {
												selectedTool = tool;
												showManifestModal = true;
											}}
										>
											<Heart className="size-4" />
										</button>
									</Tooltip>
								{/if}

								<Tooltip content={$i18n.t('Valves')}>
									<button
										class="p-2 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
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
										class="p-2 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
										type="button"
									>
										<EllipsisHorizontal className="size-4" />
									</button>
								</ToolMenu>
							{/if}
						</div>
					</div>
				</div>
			{/each}
		</div>

		<!-- Import/Export Section -->
		{#if $user?.role === 'admin'}
			<div class="flex justify-end gap-2">
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

				<button
					class="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-700 rounded-lg transition-colors"
					on:click={() => {
						toolsImportInputElement.click();
					}}
				>
					<span>{$i18n.t('Import Tools')}</span>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="size-4"
					>
						<path
							fill-rule="evenodd"
							d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 9.5a.75.75 0 0 1-.75-.75V8.06l-.72.72a.75.75 0 0 1-1.06-1.06l2-2a.75.75 0 0 1 1.06 0l2 2a.75.75 0 1 1-1.06 1.06l-.72-.72v2.69a.75.75 0 0 1-.75.75Z"
							clip-rule="evenodd"
						/>
					</svg>
				</button>

				{#if tools.length}
					<button
						class="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-700 rounded-lg transition-colors"
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
						<span>{$i18n.t('Export Tools')}</span>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="size-4"
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

		<!-- Community Section -->
		{#if $config?.features.enable_community_sharing}
			<div class="mt-12 pt-8 border-t border-gray-200 dark:border-gray-700">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-4">
					{$i18n.t('Made by Open WebUI Community')}
				</h2>

				<a
					class="flex items-center justify-between p-4 bg-gradient-to-r from-blue-50 to-blue-50 dark:from-blue-900/20 dark:to-emerald-900/20 border border-blue-200 dark:border-blue-800 rounded-xl hover:shadow-md transition-all group"
					href="https://openwebui.com/#open-webui-community"
					target="_blank"
				>
					<div>
						<h3 class="font-semibold text-gray-900 dark:text-white mb-1">
							{$i18n.t('Discover a tool')}
						</h3>
						<p class="text-sm text-gray-600 dark:text-gray-400">
							{$i18n.t('Discover, download, and explore custom tools')}
						</p>
					</div>

					<div
						class="p-2 bg-white dark:bg-gray-800 rounded-lg group-hover:translate-x-1 transition-transform"
					>
						<ChevronRight className="size-5 text-green-600 dark:text-green-400" />
					</div>
				</a>
			</div>
		{/if}
	</div>

	<!-- Modals -->
	<DeleteConfirmDialog
		bind:show={showDeleteConfirm}
		title={$i18n.t('Delete tool?')}
		on:confirm={() => {
			deleteHandler(selectedTool);
		}}
	>
		<div class="text-sm text-gray-500">
			{$i18n.t('This will delete')} <span class="font-semibold">{selectedTool?.name}</span>.
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
			<div class="bg-yellow-50 dark:bg-yellow-900/20 text-yellow-800 dark:text-yellow-200 rounded-lg px-4 py-3 border border-yellow-200 dark:border-yellow-800">
				<div class="font-semibold mb-2">{$i18n.t('Please carefully review the following warnings:')}</div>

				<ul class="mt-1 list-disc pl-4 text-sm space-y-1">
					<li>
						{$i18n.t('Tools have a function calling system that allows arbitrary code execution')}.
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
	<div class="w-full h-full flex justify-center items-center py-12">
		<Spinner className="size-8" />
	</div>
{/if}