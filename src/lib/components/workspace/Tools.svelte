<script lang="ts">
	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { onMount, getContext } from 'svelte';
	import { WEBUI_NAME, prompts, tools } from '$lib/stores';
	import { createNewPrompt, deletePromptByCommand, getPrompts } from '$lib/apis/prompts';

	import { goto } from '$app/navigation';
	import {
		createNewTool,
		deleteToolById,
		exportTools,
		getToolById,
		getTools
	} from '$lib/apis/tools';
	import ArrowDownTray from '../icons/ArrowDownTray.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import ConfirmDialog from '../common/ConfirmDialog.svelte';

	const i18n = getContext('i18n');

	let toolsImportInputElement: HTMLInputElement;
	let importFiles;

	let showConfirm = false;
	let query = '';
</script>

<svelte:head>
	<title>
		{$i18n.t('Tools')} | {$WEBUI_NAME}
	</title>
</svelte:head>

<div class="mb-3 flex justify-between items-center">
	<div class=" text-lg font-semibold self-center">{$i18n.t('Tools')}</div>
</div>

<div class=" flex w-full space-x-2">
	<div class="flex flex-1">
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
			placeholder={$i18n.t('Search Tools')}
		/>
	</div>

	<div>
		<a
			class=" px-2 py-2 rounded-xl border border-gray-200 dark:border-gray-600 dark:border-0 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 transition font-medium text-sm flex items-center space-x-1"
			href="/workspace/tools/create"
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 16 16"
				fill="currentColor"
				class="w-4 h-4"
			>
				<path
					d="M8.75 3.75a.75.75 0 0 0-1.5 0v3.5h-3.5a.75.75 0 0 0 0 1.5h3.5v3.5a.75.75 0 0 0 1.5 0v-3.5h3.5a.75.75 0 0 0 0-1.5h-3.5v-3.5Z"
				/>
			</svg>
		</a>
	</div>
</div>
<hr class=" dark:border-gray-850 my-2.5" />

<div class="my-3 mb-5">
	{#each $tools.filter((t) => query === '' || t.name
				.toLowerCase()
				.includes(query.toLowerCase()) || t.id.toLowerCase().includes(query.toLowerCase())) as tool}
		<button
			class=" flex space-x-4 cursor-pointer w-full px-3 py-2 dark:hover:bg-white/5 hover:bg-black/5 rounded-xl"
			type="button"
			on:click={() => {
				goto(`/workspace/tools/edit?id=${encodeURIComponent(tool.id)}`);
			}}
		>
			<div class=" flex flex-1 space-x-4 cursor-pointer w-full">
				<a
					href={`/workspace/tools/edit?id=${encodeURIComponent(tool.id)}`}
					class="flex items-center text-left"
				>
					<div class=" flex-1 self-center pl-5">
						<div class=" font-semibold flex items-center gap-1.5">
							<div>
								{tool.name}
							</div>
							<div class=" text-gray-500 text-xs font-medium">{tool.id}</div>
						</div>
						<div class=" text-xs overflow-hidden text-ellipsis line-clamp-1">
							{tool.meta.description}
						</div>
					</div>
				</a>
			</div>
			<div class="flex flex-row space-x-1 self-center">
				<Tooltip content="Edit">
					<a
						class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
						type="button"
						href={`/workspace/tools/edit?id=${encodeURIComponent(tool.id)}`}
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

				<Tooltip content="Clone">
					<button
						class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
						type="button"
						on:click={async (e) => {
							e.stopPropagation();

							const _tool = await getToolById(localStorage.token, tool.id).catch((error) => {
								toast.error(error);
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
						}}
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
								d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 0 1-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 0 1 1.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 0 0-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 0 1-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 0 0-3.375-3.375h-1.5a1.125 1.125 0 0 1-1.125-1.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H9.75"
							/>
						</svg>
					</button>
				</Tooltip>

				<Tooltip content="Export">
					<button
						class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
						type="button"
						on:click={async (e) => {
							e.stopPropagation();

							const _tool = await getToolById(localStorage.token, tool.id).catch((error) => {
								toast.error(error);
								return null;
							});

							if (_tool) {
								let blob = new Blob([JSON.stringify([_tool])], {
									type: 'application/json'
								});
								saveAs(blob, `tool-${_tool.id}-export-${Date.now()}.json`);
							}
						}}
					>
						<ArrowDownTray />
					</button>
				</Tooltip>

				<Tooltip content="Delete">
					<button
						class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
						type="button"
						on:click={async (e) => {
							e.stopPropagation();

							const res = await deleteToolById(localStorage.token, tool.id).catch((error) => {
								toast.error(error);
								return null;
							});

							if (res) {
								toast.success('Tool deleted successfully');
								tools.set(await getTools(localStorage.token));
							}
						}}
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
								d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"
							/>
						</svg>
					</button>
				</Tooltip>
			</div>
		</button>
	{/each}
</div>

<div class=" text-gray-500 text-xs mt-1 mb-2">
	ⓘ {$i18n.t(
		'Admins have access to all tools at all times; users need tools assigned per model in the workspace.'
	)}
</div>

<div class=" flex justify-end w-full mb-2">
	<div class="flex space-x-2">
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
			class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-200 transition"
			on:click={() => {
				toolsImportInputElement.click();
			}}
		>
			<div class=" self-center mr-2 font-medium">{$i18n.t('Import Tools')}</div>

			<div class=" self-center">
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
		</button>

		<button
			class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-200 transition"
			on:click={async () => {
				const _tools = await exportTools(localStorage.token).catch((error) => {
					toast.error(error);
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
			<div class=" self-center mr-2 font-medium">{$i18n.t('Export Tools')}</div>

			<div class=" self-center">
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
		</button>
	</div>
</div>

<ConfirmDialog
	bind:show={showConfirm}
	on:confirm={() => {
		const reader = new FileReader();
		reader.onload = async (event) => {
			const _tools = JSON.parse(event.target.result);
			console.log(_tools);

			for (const tool of _tools) {
				const res = await createNewTool(localStorage.token, tool).catch((error) => {
					toast.error(error);
					return null;
				});
			}

			toast.success('Tool imported successfully');
			tools.set(await getTools(localStorage.token));
		};

		reader.readAsText(importFiles[0]);
	}}
>
	<div class="text-sm text-gray-500">
		<div class=" bg-yellow-500/20 text-yellow-700 dark:text-yellow-200 rounded-lg px-4 py-3">
			<div>Please carefully review the following warnings:</div>

			<ul class=" mt-1 list-disc pl-4 text-xs">
				<li>Tools have a function calling system that allows arbitrary code execution.</li>
				<li>Do not install tools from sources you do not fully trust.</li>
			</ul>
		</div>

		<div class="my-3">
			I acknowledge that I have read and I understand the implications of my action. I am aware of
			the risks associated with executing arbitrary code and I have verified the trustworthiness of
			the source.
		</div>
	</div>
</ConfirmDialog>
