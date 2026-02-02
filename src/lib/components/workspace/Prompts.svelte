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
		<div class="text-sm text-gray-500">
			{$i18n.t('This will delete')} <span class="font-semibold">{deletePrompt.command}</span>.
		</div>
	</DeleteConfirmDialog>

	<div class="flex flex-col gap-4 my-4">
		<!-- Header Section -->
		<div class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
			<div class="flex items-center gap-3">
				<h1 class="text-2xl font-semibold text-gray-900 dark:text-white">
					{$i18n.t('Prompts')}
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
						placeholder={$i18n.t('Search Prompts')}
					/>
				</div>

				<Tooltip content={$i18n.t('Create Prompt')}>
					<a
						class="p-2.5 rounded-lg bg-orange-600 hover:bg-orange-700 text-white transition-colors shadow-sm hover:shadow-md"
						href="/workspace/prompts/create"
					>
						<Plus className="size-4" />
					</a>
				</Tooltip>
			</div>
		</div>

		<!-- Prompts Grid -->
		<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
			{#each filteredItems as prompt}
				<div
					class="group bg-white dark:bg-gray-850 border border-gray-200 dark:border-gray-700 rounded-xl p-4 hover:shadow-lg hover:border-gray-300 dark:hover:border-gray-600 transition-all duration-200"
				>
					<span
						class="text-xs font-bold px-2 py-0.5 rounded-md uppercase bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 margin-bottom-2 inline-block mb-2"
					>
						Prompt
					</span>
					<!-- Prompt Content -->
					<a
						href={`/workspace/prompts/edit?command=${encodeURIComponent(prompt.command)}`}
						class="block mb-3"
					>
						<h3 class="font-semibold text-gray-900 dark:text-white line-clamp-1 capitalize mb-1">
							{prompt.title}
						</h3>
						<p class="text-sm text-gray-600 dark:text-gray-400 line-clamp-1">
							{prompt.command}
						</p>
					</a>

					<!-- Prompt Footer -->
					<div
						class="flex items-center justify-between pt-3 border-t border-gray-100 dark:border-gray-800"
					>
						<Tooltip
							content={prompt?.user?.email ?? $i18n.t('Deleted User')}
							className="flex-shrink-0"
							placement="top-start"
						>
							<div class="text-xs text-gray-500 dark:text-gray-400 truncate">
								{$i18n.t('By {{name}}', {
									name: capitalizeFirstLetter(
										prompt?.user?.name ?? prompt?.user?.email ?? $i18n.t('Deleted User')
									)
								})}
							</div>
						</Tooltip>

						<div class="flex items-center gap-1 flex-shrink-0 ml-2">
							<Tooltip content={$i18n.t('Edit')}>
								<a
									class="p-2 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
									href={`/workspace/prompts/edit?command=${encodeURIComponent(prompt.command)}`}
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
								<button
									class="p-2 text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
									type="button"
								>
									<EllipsisHorizontal className="size-4" />
								</button>
							</PromptMenu>
						</div>
					</div>
				</div>
			{/each}
		</div>

		<!-- Import/Export Section -->
		{#if $user?.role === 'admin'}
			<div class="flex justify-end gap-2">
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

				<button
					class="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-700 rounded-lg transition-colors"
					on:click={() => {
						promptsImportInputElement.click();
					}}
				>
					<span>{$i18n.t('Import Prompts')}</span>
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

				{#if prompts.length}
					<button
						class="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 border border-gray-200 dark:border-gray-700 rounded-lg transition-colors"
						on:click={async () => {
							let blob = new Blob([JSON.stringify(prompts)], {
								type: 'application/json'
							});
							saveAs(blob, `prompts-export-${Date.now()}.json`);
						}}
					>
						<span>{$i18n.t('Export Prompts')}</span>
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
							{$i18n.t('Discover a prompt')}
						</h3>
						<p class="text-sm text-gray-600 dark:text-gray-400">
							{$i18n.t('Discover, download, and explore custom prompts')}
						</p>
					</div>

					<div
						class="p-2 bg-white dark:bg-gray-800 rounded-lg group-hover:translate-x-1 transition-transform"
					>
						<ChevronRight className="size-5 text-purple-600 dark:text-purple-400" />
					</div>
				</a>
			</div>
		{/if}
	</div>
{:else}
	<div class="w-full h-full flex justify-center items-center py-12">
		<Spinner className="size-8" />
	</div>
{/if}
