<script lang="ts">
	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { goto } from '$app/navigation';
	import { onMount, getContext, tick, onDestroy } from 'svelte';
	import { WEBUI_NAME, config, prompts as _prompts, user } from '$lib/stores';

	import {
		createNewPrompt,
		deletePromptById,
		getPrompts,
		getPromptItems,
		getPromptTags
	} from '$lib/apis/prompts';
	import { capitalizeFirstLetter, slugify, copyToClipboard } from '$lib/utils';

	import PromptMenu from './Prompts/PromptMenu.svelte';
	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import Clipboard from '../icons/Clipboard.svelte';
	import Check from '../icons/Check.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Search from '../icons/Search.svelte';
	import Plus from '../icons/Plus.svelte';
	import ChevronRight from '../icons/ChevronRight.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import XMark from '../icons/XMark.svelte';
	import GarbageBin from '../icons/GarbageBin.svelte';
	import ViewSelector from './common/ViewSelector.svelte';
	import TagSelector from './common/TagSelector.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import Pagination from '../common/Pagination.svelte';

	let shiftKey = false;

	const i18n = getContext('i18n');
	let promptsImportInputElement: HTMLInputElement;
	let loaded = false;

	let importFiles = null;
	let query = '';
	let searchDebounceTimer: ReturnType<typeof setTimeout>;

	let prompts = null;
	let tags = [];
	let total = null;
	let loading = false;

	let showDeleteConfirm = false;
	let deletePrompt = null;

	let tagsContainerElement: HTMLDivElement;
	let viewOption = '';
	let selectedTag = '';
	let copiedId: string | null = null;

	let page = 1;

	// Debounce only query changes
	$: if (query !== undefined) {
		loading = true;
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(() => {
			getPromptList();
		}, 300);
	}

	// Immediate response to page/filter changes
	$: if (page && selectedTag !== undefined && viewOption !== undefined) {
		getPromptList();
	}

	const getPromptList = async () => {
		if (!loaded) return;

		loading = true;
		try {
			const res = await getPromptItems(
				localStorage.token,
				query,
				viewOption,
				selectedTag,
				null,
				null,
				page
			).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (res) {
				prompts = res.items;
				total = res.total;

				// get tags
				tags = await getPromptTags(localStorage.token).catch((error) => {
					toast.error(`${error}`);
					return [];
				});
			}
		} catch (err) {
			console.error(err);
		} finally {
			loading = false;
		}
	};

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
		const clonedPrompt = { ...prompt };

		clonedPrompt.title = `${clonedPrompt.title} (Clone)`;
		const baseCommand = clonedPrompt.command.startsWith('/')
			? clonedPrompt.command.substring(1)
			: clonedPrompt.command;
		clonedPrompt.command = slugify(`${baseCommand} clone`);

		sessionStorage.prompt = JSON.stringify(clonedPrompt);
		goto('/workspace/prompts/create');
	};

	const exportHandler = async (prompt) => {
		let blob = new Blob([JSON.stringify([prompt])], {
			type: 'application/json'
		});
		saveAs(blob, `prompt-export-${Date.now()}.json`);
	};

	const copyHandler = async (prompt) => {
		const res = await copyToClipboard(prompt.content);
		if (res) {
			copiedId = prompt.command;
			setTimeout(() => {
				copiedId = null;
			}, 2000);
		}
	};

	const deleteHandler = async (prompt) => {
		const command = prompt.command;

		const res = await deletePromptById(localStorage.token, prompt.id).catch((err) => {
			toast.error(err);
			return null;
		});

		if (res) {
			toast.success($i18n.t(`Deleted {{name}}`, { name: command }));
		}

		page = 1;
		getPromptList();
		await _prompts.set(await getPrompts(localStorage.token));
	};

	onMount(async () => {
		viewOption = localStorage?.workspaceViewOption || '';
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
		window.addEventListener('blur', onBlur);

		return () => {
			clearTimeout(searchDebounceTimer);
			window.removeEventListener('keydown', onKeyDown);
			window.removeEventListener('keyup', onKeyUp);
			window.removeEventListener('blur', onBlur);
		};
	});

	onDestroy(() => {
		clearTimeout(searchDebounceTimer);
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
			deleteHandler(deletePrompt);
		}}
	>
		<div class=" text-sm text-gray-500 truncate">
			{$i18n.t('This will delete')} <span class="  font-medium">{deletePrompt.command}</span>.
		</div>
	</DeleteConfirmDialog>

	<div class="flex flex-col gap-1 px-1 mt-1.5 mb-3">
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
							command: prompt.command.charAt(0) === '/' ? prompt.command.slice(1) : prompt.command,
							title: prompt.title,
							content: prompt.content
						}).catch((error) => {
							toast.error(`${error}`);
							return null;
						});
					}

					prompts = null;
					page = 1;
					getPromptList();
					await _prompts.set(await getPrompts(localStorage.token));

					importFiles = [];
					promptsImportInputElement.value = '';
				};

				reader.readAsText(importFiles[0]);
			}}
		/>
		<div class="flex justify-between items-center">
			<div class="flex items-center md:self-center text-xl font-medium px-0.5 gap-2 shrink-0">
				<div>
					{$i18n.t('Prompts')}
				</div>

				<div class="text-lg font-medium text-gray-500 dark:text-gray-500">
					{total ?? ''}
				</div>
			</div>

			<div class="flex w-full justify-end gap-1.5">
				{#if $user?.role === 'admin' || $user?.permissions?.workspace?.prompts_import}
					<button
						class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-200 transition"
						on:click={() => {
							promptsImportInputElement.click();
						}}
					>
						<div class=" self-center font-medium line-clamp-1">
							{$i18n.t('Import')}
						</div>
					</button>
				{/if}

				{#if total && ($user?.role === 'admin' || $user?.permissions?.workspace?.prompts_export)}
					<button
						class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-200 transition"
						on:click={async () => {
							let blob = new Blob([JSON.stringify(prompts)], {
								type: 'application/json'
							});
							saveAs(blob, `prompts-export-${Date.now()}.json`);
						}}
					>
						<div class=" self-center font-medium line-clamp-1">
							{$i18n.t('Export')}
						</div>
					</button>
				{/if}
				<a
					class=" px-2 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black transition font-medium text-sm flex items-center"
					href="/workspace/prompts/create"
				>
					<Plus className="size-3" strokeWidth="2.5" />

					<div class=" hidden md:block md:ml-1 text-xs">{$i18n.t('New Prompt')}</div>
				</a>
			</div>
		</div>
	</div>

	<div
		class="py-2 bg-white dark:bg-gray-900 rounded-3xl border border-gray-100/30 dark:border-gray-850/30"
	>
		<div class=" flex w-full space-x-2 py-0.5 px-3.5 pb-2">
			<div class="flex flex-1">
				<div class=" self-center ml-1 mr-3">
					<Search className="size-3.5" />
				</div>
				<input
					class=" w-full text-sm pr-4 py-1 rounded-r-xl outline-hidden bg-transparent"
					bind:value={query}
					placeholder={$i18n.t('Search Prompts')}
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
						page = 1;
						await tick();
					}}
				/>

				{#if (tags ?? []).length > 0}
					<TagSelector
						bind:value={selectedTag}
						items={tags.map((tag) => ({ value: tag, label: tag }))}
					/>
				{/if}
			</div>
		</div>

		{#if prompts === null || loading}
			<div class="w-full h-full flex justify-center items-center my-16 mb-24">
				<Spinner className="size-5" />
			</div>
		{:else if (prompts ?? []).length !== 0}
			<!-- Before they call, I will answer; while they are yet speaking, I will hear. -->
			<div class="gap-2 grid my-2 px-3 lg:grid-cols-2">
				{#each prompts as prompt}
					<a
						class=" flex space-x-4 cursor-pointer text-left w-full px-3 py-2.5 dark:hover:bg-gray-850/50 hover:bg-gray-50 transition rounded-2xl"
						href={`/workspace/prompts/${prompt.id}`}
					>
						<div class=" flex flex-col flex-1 space-x-4 cursor-pointer w-full pl-1">
							<div class="flex items-center justify-between w-full mb-0.5">
								<div class="flex items-center gap-2">
									<div class="font-medium line-clamp-1 capitalize">{prompt.name}</div>
									<div class="text-xs overflow-hidden text-ellipsis line-clamp-1 text-gray-500">
										/{prompt.command}
									</div>
								</div>
								{#if !prompt.write_access}
									<Badge type="muted" content={$i18n.t('Read Only')} />
								{/if}
							</div>

							<div class="flex gap-1 text-xs">
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

								<div>·</div>

								{#if prompt.content}
									<Tooltip content={prompt.content} placement="top">
										<div class="line-clamp-1">
											{prompt.content}
										</div>
									</Tooltip>
								{/if}
							</div>
						</div>
						<div class="flex flex-row gap-0.5 self-center">
							{#if shiftKey}
								<Tooltip content={$i18n.t('Delete')}>
									<button
										class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
										type="button"
										on:click={() => {
											deleteHandler(prompt);
										}}
									>
										<GarbageBin />
									</button>
								</Tooltip>
							{:else}
								<Tooltip content={$i18n.t('Copy Prompt')}>
									<button
										class="self-center w-fit text-sm p-1.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
										type="button"
										on:click={(e) => {
											e.preventDefault();
											e.stopPropagation();
											copyHandler(prompt);
										}}
									>
										{#if copiedId === prompt.command}
											<Check className="size-4" strokeWidth="1.5" />
										{:else}
											<Clipboard className="size-4" strokeWidth="1.5" />
										{/if}
									</button>
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
										class="self-center w-fit text-sm p-1.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
										type="button"
									>
										<EllipsisHorizontal className="size-5" />
									</button>
								</PromptMenu>
							{/if}
						</div>
					</a>
				{/each}
			</div>

			{#if total > 30}
				<div class="flex justify-center mt-4 mb-2">
					<Pagination bind:page count={total} perPage={30} />
				</div>
			{/if}
		{:else}
			<div class=" w-full h-full flex flex-col justify-center items-center my-16 mb-24">
				<div class="max-w-md text-center">
					<div class=" text-3xl mb-3">😕</div>
					<div class=" text-lg font-medium mb-1">{$i18n.t('No prompts found')}</div>
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
				href="https://openwebui.com/prompts"
				target="_blank"
			>
				<div class=" self-center">
					<div class=" font-medium line-clamp-1">{$i18n.t('Discover a prompt')}</div>
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
	{/if}
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner className="size-5" />
	</div>
{/if}
