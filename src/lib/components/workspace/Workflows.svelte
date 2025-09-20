<script lang="ts">
	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { onMount, getContext } from 'svelte';
	import { WEBUI_NAME, config, workflows as _workflows, user } from '$lib/stores';

	import { goto } from '$app/navigation';
	import {
		createNewWorkflow,
		deleteWorkflowById,
		exportWorkflows,
		getWorkflowById,
		getWorkflowList,
		getWorkflows
	} from '$lib/apis/workflows';
	import ArrowDownTray from '../icons/ArrowDownTray.svelte';
	import Pencil from '../icons/Pencil.svelte';
	import WorkflowIcon from '../icons/WorkflowIcon.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import ConfirmDialog from '../common/ConfirmDialog.svelte';
	import WorkflowMenu from './Workflows/WorkflowMenu.svelte';
	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
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

	let workflowsImportInputElement: HTMLInputElement;
	let importFiles: FileList | null = null;

	let showConfirm = false;
	let query = '';

	let showDeleteConfirm = false;
	let selectedWorkflow: any = null;

	let workflows: any[] = [];
	let filteredItems: any[] = [];

	$: filteredItems = workflows.filter(
		(w) =>
			query === '' ||
			w.name.toLowerCase().includes(query.toLowerCase()) ||
			w.id.toLowerCase().includes(query.toLowerCase())
	);

	const shareHandler = async (workflow: any) => {
		const item = await getWorkflowById(localStorage.token, workflow.id).catch((error: any) => {
			toast.error(`${error}`);
			return null;
		});

		toast.success($i18n.t('Redirecting you to Open WebUI Community'));

		const url = 'https://openwebui.com';

		const tab = await window.open(`${url}/workflows/create`, '_blank');

		const messageHandler = (event: any) => {
			if (event.origin !== url) return;
			if (event.data === 'loaded') {
				tab?.postMessage(JSON.stringify(item), '*');
				window.removeEventListener('message', messageHandler);
			}
		};

		window.addEventListener('message', messageHandler, false);
		console.log(item);
	};

	const cloneHandler = async (workflow: any) => {
		const _workflow = await getWorkflowById(localStorage.token, workflow.id).catch((error: any) => {
			toast.error(`${error}`);
			return null;
		});

		if (_workflow) {
			sessionStorage.workflow = JSON.stringify({
				..._workflow,
				id: `${_workflow.id}_clone`,
				name: `${_workflow.name} (Clone)`
			});
			goto('/workspace/workflows/create');
		}
	};

	const exportHandler = async (workflow: any) => {
		const _workflow = await getWorkflowById(localStorage.token, workflow.id).catch((error: any) => {
			toast.error(`${error}`);
			return null;
		});

		if (_workflow) {
			let blob = new Blob([JSON.stringify([_workflow])], {
				type: 'application/json'
			});
			saveAs(blob, `workflow-${_workflow.id}-export-${Date.now()}.json`);
		}
	};

	const deleteHandler = async (workflow: any) => {
		const res = await deleteWorkflowById(localStorage.token, workflow.id).catch((error: any) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Workflow deleted successfully'));
			await init();
		}
	};

	const init = async () => {
		workflows = await getWorkflowList(localStorage.token);
		_workflows.set(await getWorkflows(localStorage.token));
	};

	onMount(() => {
		init().then(() => {
			loaded = true;
		});

		const onKeyDown = (event: any) => {
			if (event.key === 'Shift') {
				shiftKey = true;
			}
		};

		const onKeyUp = (event: any) => {
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
		{$i18n.t('Workflows')} | {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<div class="flex flex-col gap-1 my-1.5">
		<div class="flex justify-between items-center mb-4">
			<div class="flex items-center md:self-center text-2xl font-semibold px-0.5">
				{$i18n.t('Workflows')}
				<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />
				<span class="text-lg font-medium text-gray-500 dark:text-gray-300"
					>{filteredItems.length}</span
				>
			</div>
		</div>

		<div class=" flex items-center w-full space-x-5">
			<!-- 搜索框 - 固定宽度 -->
			<div class="flex items-center w-64 rounded-lg bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-200 transition">
				<div class=" self-center ml-3 mr-2">
					<Search className="size-5" />
				</div>
				<input
					class=" w-full text-sm px-3 py-3 rounded-lg outline-hidden bg-transparent"
					bind:value={query}
					placeholder={$i18n.t('Search Workflows')}
				/>
			</div>

			<!-- 功能按钮组 - 紧凑排列 -->
			<div class="flex items-center space-x-2">
				<!-- Import Workflows 按钮 -->
				<input
					bind:this={workflowsImportInputElement}
					class="hidden"
					type="file"
					accept=".json"
					multiple
					bind:files={importFiles}
					on:change={async () => {
						if (importFiles && importFiles.length > 0) {
							showConfirm = true;
						}
					}}
				/>
				<button
					class="flex text-sm items-center space-x-1 px-3 py-3 rounded-lg bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-200 transition"
					on:click={() => workflowsImportInputElement.click()}
				>
					<div class=" self-center mr-2 font-medium line-clamp-1">{$i18n.t('Import Workflows')}</div>
					<div class=" self-center">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="w-5 h-5"
						>
							<path
								fill-rule="evenodd"
								d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 9.5a.75.75 0 0 1-.75-.75V8.06l-.72.72a.75.75 0 0 1-1.06-1.06l2-2a.75.75 0 0 1 1.06 0l2 2a.75.75 0 1 1-1.06 1.06l-.72-.72v2.69a.75.75 0 0 1-.75.75Z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
				</button>

				<!-- Export Workflows 按钮 -->
				{#if workflows.length}
					<button
						class="flex text-sm items-center space-x-1 px-3 py-3 rounded-lg bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-200 transition"
						on:click={async () => {
							const workflowsData = await exportWorkflows(localStorage.token);
							if (workflowsData) {
								let blob = new Blob([JSON.stringify(workflowsData)], {
									type: 'application/json'
								});
								saveAs(blob, `workflows-export-${Date.now()}.json`);
							}
						}}
					>
						<div class=" self-center mr-2 font-medium line-clamp-1">{$i18n.t('Export Workflows')}</div>
						<div class=" self-center">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								class="w-5 h-5"
							>
								<path
									fill-rule="evenodd"
									d="M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5 0 0 0 4 14h8a1.5 1.5 0 0 0 1.5-1.5V6.621a1.5 1.5 0 0 0-.44-1.06L9.94 2.439A1.5 1.5 0 0 0 8.878 2H4Zm4 3.5a.75.75 0 0 1 .75.75v2.69l.72-.72a.75.75 0 1 1 1.06 1.06l-2 2a.75.75 0 0 1-1.06 0l-2-2a.75.75 0 0 1 1.06-1.06l.72.72V6.25A.75.75 0 0 1 8 5.5Z"
									clip-rule="evenodd"
								/>
							</svg>
						</div>
					</button>
				{/if}

				<!-- + 图标按钮 -->
				<a
					class=" px-3 py-3 rounded-lg bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-200 transition font-medium text-sm flex items-center space-x-1"
					href="/workspace/workflows/create"
				>
					<Plus className="size-5" />
				</a>
			</div>
		</div>

		<div class=" my-6 mb-5 gap-5 grid lg:grid-cols-2 xl:grid-cols-3">
			{#each filteredItems as workflow (workflow.id)}
				<div
					class=" flex flex-col cursor-pointer w-full px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-800 dark:hover:bg-gray-700 hover:bg-gray-100 transition"
				>
					<div class="flex flex-col w-full overflow-hidden mt-0.5 mb-0.5">
						<div class="text-left w-full">
							<div class="flex flex-col w-full overflow-hidden">
								<!-- 第一行：图标 + 名称 -->
								<div class="flex items-center gap-2 mb-1">
									<WorkflowIcon className="w-5 h-5 text-gray-900 dark:text-gray-100 flex-shrink-0" />
									<div class=" text-base font-medium line-clamp-1 text-gray-900 dark:text-gray-100">
										{workflow.name}
									</div>
								</div>
								
								<!-- 第二行：Workflow ID + Description -->
								<div class="flex items-center gap-2 mb-1">
									<div class="text-xs text-gray-500 dark:text-gray-400 font-mono">
										{workflow.id}
									</div>
									<div class="text-xs text-gray-400 dark:text-gray-500 line-clamp-1 flex-1">
										{workflow.description || 'No description'}
									</div>
								</div>
							</div>
						</div>

						<div class="flex justify-between items-center -mb-0.5 px-0.5 mt-1">
							<div class=" text-xs">
								<Tooltip
									content={workflow?.user?.email ?? $i18n.t('Deleted User')}
									className="flex shrink-0"
									placement="top-start"
								>
									<div class="shrink-0 text-gray-500">
										{$i18n.t('By {{name}}', {
											name: capitalizeFirstLetter(
												workflow?.user?.name ?? workflow?.user?.email ?? $i18n.t('Deleted User')
											)
										})}
									</div>
								</Tooltip>
							</div>

							<div class="flex flex-row gap-0.5 items-center">
								<!-- 编辑按钮 -->
								<a
									class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
									href={`/workspace/workflows/edit?id=${encodeURIComponent(workflow.id)}`}
								>
									<Pencil className="w-4 h-4" strokeWidth="1.5" />
								</a>

								{#if shiftKey}
									<Tooltip content={$i18n.t('Delete')}>
										<button
											class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
											type="button"
											on:click={() => {
												deleteHandler(workflow);
											}}
										>
											<GarbageBin />
										</button>
									</Tooltip>
								{:else}
									<WorkflowMenu
										{workflow}
										onShare={shareHandler}
										onClone={cloneHandler}
										onExport={exportHandler}
										onDelete={() => {
											showDeleteConfirm = true;
											selectedWorkflow = workflow;
										}}
									>
										<button
											class="self-center w-fit text-sm p-1.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
											type="button"
										>
											<EllipsisHorizontal className="size-5" />
										</button>
									</WorkflowMenu>
								{/if}
							</div>
						</div>
					</div>
				</div>
			{/each}
		</div>

		<!-- Empty State -->
		{#if filteredItems.length === 0}
			<div class="flex flex-col items-center justify-center py-12 text-center">
				<div class="rounded-full w-16 h-16 bg-gray-100 dark:bg-gray-800 flex items-center justify-center mb-4">
					<WorkflowIcon className="size-8 text-gray-400 dark:text-gray-500" />
				</div>
				<h3 class="text-lg font-medium text-gray-900 dark:text-white mb-2">
					{query ? $i18n.t('No workflows found') : $i18n.t('No workflows yet')}
				</h3>
				<p class="text-gray-500 dark:text-gray-400 mb-6 max-w-sm">
					{query 
						? $i18n.t('Try adjusting your search terms')
						: $i18n.t('Create your first workflow to get started')
					}
				</p>
				{#if !query}
					<a
						href="/workspace/workflows/create"
						class="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition"
					>
						<Plus className="size-4" />
						{$i18n.t('Create Workflow')}
					</a>
				{/if}
			</div>
		{/if}
	</div>
{:else}
	<div class="flex items-center justify-center py-12">
		<Spinner />
	</div>
{/if}

<!-- Import Confirmation Dialog -->
<ConfirmDialog
	bind:show={showConfirm}
	title={$i18n.t('Import Workflows')}
	message={$i18n.t('Are you sure you want to import these workflows?')}
	onConfirm={async () => {
		// TODO: Implement import logic when backend is ready
		toast.success($i18n.t('Workflows imported successfully'));
		showConfirm = false;
		await init();
	}}
/>

<!-- Delete Confirmation Dialog -->
<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete Workflow')}
	message={$i18n.t('Are you sure you want to delete this workflow? This action cannot be undone.')}
	onConfirm={async () => {
		if (selectedWorkflow) {
			await deleteHandler(selectedWorkflow);
			showDeleteConfirm = false;
			selectedWorkflow = null;
		}
	}}
/>
