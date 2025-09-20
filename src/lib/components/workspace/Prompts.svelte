<script lang="ts">
	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { goto } from '$app/navigation';
	import { onMount, getContext } from 'svelte';
	import { WEBUI_NAME, config, prompts as _prompts, user } from '$lib/stores';

	import {
		createNewPrompt,
		deletePromptByCommand,
		getPrompts,
		getPromptList
	} from '$lib/apis/prompts';

	import PromptMenu from './Prompts/PromptMenu.svelte';
	import PencilSquare from '../icons/PencilSquare.svelte';
	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Search from '../icons/Search.svelte';
	import Plus from '../icons/Plus.svelte';
	import ChevronRight from '../icons/ChevronRight.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import { capitalizeFirstLetter } from '$lib/utils';

	const i18n = getContext('i18n');
	let promptsImportInputElement: HTMLInputElement;
	let loaded = false;

	let importFiles = '';
	let query = '';

	let prompts = [];

	let showDeleteConfirm = false;
	let deletePrompt = null;

	let filteredItems = [];
	$: filteredItems = prompts.filter((p) => query === '' || p.command.includes(query));

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
		saveAs(blob, `prompt-export-${Date.now()}.json`);
	};

	const deleteHandler = async (prompt) => {
		const command = prompt.command;
		await deletePromptByCommand(localStorage.token, command);
		await init();
	};

	const init = async () => {
		prompts = await getPromptList(localStorage.token);
		await _prompts.set(await getPrompts(localStorage.token));
	};

	onMount(async () => {
		await init();
		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Prompts')} | {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<DeleteConfirmDialog
		bind:show={showDeleteConfirm}
		title={$i18n.t('Delete prompt?')}
		on:confirm={() => {
			deleteHandler(deletePrompt);
		}}
	>
		<div class=" text-sm text-gray-500">
			{$i18n.t('This will delete')} <span class="  font-semibold">{deletePrompt.command}</span>.
		</div>
	</DeleteConfirmDialog>

	<div class="flex flex-col gap-1 my-1.5">
		<div class="flex justify-between items-center mb-4">
			<div class="flex items-center md:self-center text-2xl font-semibold px-0.5">
				{$i18n.t('Prompts')}
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
					placeholder={$i18n.t('Search Prompts')}
				/>
			</div>

			<!-- 功能按钮组 - 紧凑排列 -->
			<div class="flex items-center space-x-2">
				<!-- Import Prompts 按钮 -->
				<button
					class="flex text-sm items-center space-x-1 px-3 py-3 rounded-lg bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-200 transition"
					on:click={() => {
						promptsImportInputElement.click();
					}}
				>
					<div class=" self-center mr-2 font-medium line-clamp-1">{$i18n.t('Import Prompts')}</div>
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

				<!-- Export Prompts 按钮 -->
				{#if filteredItems.length}
					<button
						class="flex text-sm items-center space-x-1 px-3 py-3 rounded-lg bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-200 transition"
						on:click={async () => {
							downloadPrompts(filteredItems);
						}}
					>
						<div class=" self-center mr-2 font-medium line-clamp-1">{$i18n.t('Export Prompts')}</div>
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
					href="/workspace/prompts/create"
				>
					<Plus className="size-5" />
				</a>
			</div>
		</div>
	</div>

	<div class=" my-6 mb-5 gap-5 grid lg:grid-cols-2 xl:grid-cols-3">
		{#each filteredItems as prompt}
			<div
				class=" flex flex-col cursor-pointer w-full px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-800 dark:hover:bg-gray-700 hover:bg-gray-100 transition"
			>
				<div class="flex flex-col w-full overflow-hidden mt-0.5 mb-0.5">
					<div class="text-left w-full">
						<div class="flex flex-col w-full overflow-hidden">
							<!-- 第一行：图标 + 名称 -->
							<div class="flex items-center gap-2 mb-1">
								<svg class="w-5 h-5 text-gray-900 dark:text-gray-100 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
								</svg>
								<div class=" text-base font-medium line-clamp-1 text-gray-900 dark:text-gray-100">
									{prompt.title}
								</div>
							</div>
							
							<!-- 第二行：Command -->
							<div class=" text-xs text-gray-400 dark:text-gray-500 line-clamp-1">
								{prompt.command}
							</div>
						</div>
					</div>

					<div class="flex justify-between items-center -mb-0.5 px-0.5 mt-1">
						<div class=" text-xs">
							<Tooltip
								content={prompt?.user?.email ?? $i18n.t('Deleted User')}
								className="flex shrink-0"
								placement="top-start"
							>
								<div class="shrink-0 text-gray-500">
									{$i18n.t('By {{name}}', {
										name: capitalizeFirstLetter(
											prompt?.user?.name ?? prompt?.user?.email ?? $i18n.t('Deleted User')
										)
									})}
								</div>
							</Tooltip>
						</div>

						<div class="flex flex-row gap-0.5 items-center">
							<!-- 编辑按钮 -->
							<a
								class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
								href={`/workspace/prompts/edit?command=${encodeURIComponent(prompt.command)}`}
							>
								<PencilSquare className="w-4 h-4" strokeWidth="1.5" />
							</a>

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
						<button
							class="self-center w-fit text-sm p-1.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
							type="button"
						>
							<EllipsisHorizontal className="size-5" />
						</button>
					</PromptMenu>
						</div>
					</div>
				</div>
			</div>
		{/each}
	</div>

	{#if $user?.role === 'admin'}
		<div class=" flex justify-end w-full mb-3">
			<div class="flex space-x-2">
				<input
					id="prompts-import-input"
					bind:this={promptsImportInputElement}
					bind:files={importFiles}
					type="file"
					accept=".json"
					hidden
					on:change={() => {
						console.log(importFiles);

						const reader = new FileReader();
						reader.onload = async (event) => {
							const savedPrompts = JSON.parse(event.target.result);
							console.log(savedPrompts);

							for (const prompt of savedPrompts) {
								await createNewPrompt(localStorage.token, {
									command:
										prompt.command.charAt(0) === '/' ? prompt.command.slice(1) : prompt.command,
									title: prompt.title,
									content: prompt.content
								}).catch((error) => {
									toast.error(`${error}`);
									return null;
								});
							}

							prompts = await getPromptList(localStorage.token);
							await _prompts.set(await getPrompts(localStorage.token));

							importFiles = [];
							promptsImportInputElement.value = '';
						};

						reader.readAsText(importFiles[0]);
					}}
				/>

			</div>
		</div>
	{/if}

	<!-- {#if $config?.features.enable_community_sharing}
		<div class=" my-16">
			<div class=" text-xl font-medium mb-1 line-clamp-1">
				{$i18n.t('Made by Open WebUI Community')}
			</div>

			<a
				class=" flex cursor-pointer items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-850 w-full mb-2 px-3.5 py-1.5 rounded-xl transition"
				href="https://openwebui.com/#open-webui-community"
				target="_blank"
			>
				<div class=" self-center">
					<div class=" font-semibold line-clamp-1">{$i18n.t('Discover a prompt')}</div>
					<div class=" text-sm line-clamp-1">
						{$i18n.t('Discover, download, and explore custom prompts')}
					</div>
				</div>

				<div>
					<div>
						<ChevronRight />
					</div>
				</div>
			</a>
		</div>
	{/if} -->
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner />
	</div>
{/if}
