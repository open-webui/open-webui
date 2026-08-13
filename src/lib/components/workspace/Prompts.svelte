<script lang="ts">
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	dayjs.extend(relativeTime);

	import { goto } from '$app/navigation';
	import { onMount, getContext, tick, onDestroy } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { WEBUI_NAME, config, user, workspaceActions } from '$lib/stores';

	import {
		createNewPrompt,
		deletePromptById,
		togglePromptById,
		getPromptItems,
		getPromptTags
	} from '$lib/apis/prompts';
	import { capitalizeFirstLetter, slugify, copyToClipboard } from '$lib/utils';

	import PromptMenu from './Prompts/PromptMenu.svelte';
	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import Clipboard from '../icons/Clipboard.svelte';
	import Check from '../icons/Check.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Modal from '../common/Modal.svelte';
	import PromptEditor from './Prompts/PromptEditor.svelte';
	import Search from '../icons/Search.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import XMark from '../icons/XMark.svelte';
	import GarbageBin from '../icons/GarbageBin.svelte';
	import ViewSelector from './common/ViewSelector.svelte';
	import TagSelector from './common/TagSelector.svelte';
	import CommunityDiscover from './common/CommunityDiscover.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import Switch from '../common/Switch.svelte';
	import Pagination from '../common/Pagination.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';
	import ChevronUp from '../icons/ChevronUp.svelte';

	type PromptDraft = {
		id?: string;
		name: string;
		command: string;
		content: string;
		tags: string[];
		access_grants: any[];
		commit_message?: string;
		is_production?: boolean;
	};

	export let showCreateOnMount = false;
	export let createModalCloseHref = '';

	let shiftKey = false;

	const i18n = getContext<Writable<i18nType>>('i18n');
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
	let showCreateModal = false;
	let createPrompt: PromptDraft | null = null;
	let deletePrompt = null;

	let tagsContainerElement: HTMLDivElement;
	let viewOption = '';
	let selectedTag = '';
	let copiedId: string | null = null;
	let sortKey = 'updated_at';
	let sortDirection = 'desc';
	let openPromptMenuId: string | null = null;

	let page = 1;

	$: if (loaded) {
		workspaceActions.set([
			{
				id: 'prompts-new',
				label: $i18n.t('Create'),
				onClick: () => {
					createPrompt = null;
					showCreateModal = true;
				}
			},
			{
				id: 'prompts-import',
				label: $i18n.t('Import JSON'),
				onClick: () => promptsImportInputElement?.click(),
				visible: $user?.role === 'admin' || $user?.permissions?.workspace?.prompts_import
			},
			{
				id: 'prompts-export',
				label: $i18n.t('Export JSON'),
				onClick: async () => {
					let blob = new Blob([JSON.stringify(prompts)], {
						type: 'application/json'
					});
					saveAs(blob, `prompts-export-${Date.now()}.json`);
				},
				visible: $user?.role === 'admin' || $user?.permissions?.workspace?.prompts_export
			}
		]);
	}

	const handleSearchInput = () => {
		loading = true;
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(() => {
			if (page !== 1) {
				page = 1;
			} else {
				getPromptList();
			}
		}, 300);
	};

	// Immediate response to page/filter changes
	$: if (
		loaded &&
		page &&
		selectedTag !== undefined &&
		viewOption !== undefined &&
		sortKey !== undefined &&
		sortDirection !== undefined
	) {
		getPromptList();
	}

	const setSortKey = (key: string) => {
		if (sortKey === key) {
			sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
		} else {
			sortKey = key;
			sortDirection = key === 'updated_at' ? 'desc' : 'asc';
		}
	};

	const openPrompt = (prompt) => {
		goto(`/workspace/prompts/${prompt.id}`);
	};

	const shouldIgnoreRowClick = (target: EventTarget | null) => {
		return target instanceof Element && !!target.closest('button, a, input, [role="menu"]');
	};

	const getPromptList = async () => {
		if (!loaded) return;

		loading = true;
		try {
			const res = await getPromptItems(
				localStorage.token,
				query,
				viewOption,
				selectedTag,
				sortKey,
				sortDirection,
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

	const toPromptDraft = (prompt: any): PromptDraft => ({
		name: prompt.name || prompt.title || 'Prompt',
		command: prompt.command || '',
		content: prompt.content || '',
		tags: prompt.tags || [],
		access_grants: prompt.access_grants !== undefined ? prompt.access_grants : []
	});

	const openCreateModal = (prompt: PromptDraft | null = null) => {
		createPrompt = prompt;
		showCreateModal = true;
	};

	const closeCreateModal = async () => {
		showCreateModal = false;
		createPrompt = null;

		if (createModalCloseHref) {
			await goto(createModalCloseHref);
		}
	};

	const createPromptHandler = async (prompt: PromptDraft) => {
		const res = await createNewPrompt(localStorage.token, prompt).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Prompt created successfully'));
			page = 1;
			await getPromptList();
			await closeCreateModal();
		}
	};

	const cloneHandler = async (prompt) => {
		const clonedPrompt = { ...prompt };

		clonedPrompt.name = `${clonedPrompt.name} (Clone)`;
		const baseCommand = clonedPrompt.command.startsWith('/')
			? clonedPrompt.command.substring(1)
			: clonedPrompt.command;
		clonedPrompt.command = slugify(`${baseCommand} clone`);

		openCreateModal(toPromptDraft(clonedPrompt));
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
	};

	onMount(async () => {
		viewOption = localStorage?.workspaceViewOption || '';
		loaded = true;

		const onMessage = async (event: MessageEvent) => {
			if (
				!['https://openwebui.com', 'https://www.openwebui.com', 'http://localhost:9999'].includes(
					event.origin
				)
			) {
				return;
			}

			openCreateModal(toPromptDraft(JSON.parse(event.data)));
		};

		window.addEventListener('message', onMessage);

		if (window.opener ?? false) {
			window.opener.postMessage('loaded', '*');
		}

		if (sessionStorage.prompt) {
			const prompt = JSON.parse(sessionStorage.prompt);
			sessionStorage.removeItem('prompt');
			openCreateModal(toPromptDraft(prompt));
		} else if (showCreateOnMount) {
			openCreateModal();
		}

		const onKeyDown = (event: KeyboardEvent) => {
			if (event.key === 'Shift') {
				shiftKey = true;
			}
		};

		const onKeyUp = (event: KeyboardEvent) => {
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
			window.removeEventListener('message', onMessage);
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
		{$i18n.t('Prompts')} / {$WEBUI_NAME}
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
			{$i18n.t('This will delete')} <span class="  font-normal">{deletePrompt.command}</span>.
		</div>
	</DeleteConfirmDialog>

	<Modal
		bind:show={showCreateModal}
		size="full"
		className="!w-[calc(100vw-2rem)] sm:!w-[calc(100vw-3rem)] lg:!w-[calc(100vw-4rem)] !max-w-[80rem] h-[min(54rem,calc(100dvh-4rem))] max-h-[calc(100dvh-4rem)] flex flex-col bg-white dark:bg-gray-900 rounded-4xl"
	>
		{#key createPrompt}
			<PromptEditor
				modal={true}
				prompt={createPrompt}
				clone={createPrompt !== null}
				onSubmit={createPromptHandler}
				onCancel={() => {
					closeCreateModal();
				}}
			/>
		{/key}
	</Modal>

	<input
		id="prompts-import-input"
		bind:this={promptsImportInputElement}
		bind:files={importFiles}
		type="file"
		accept=".json"
		hidden
		on:change={() => {
			console.log(importFiles);
			if (!importFiles || importFiles.length === 0) return;

			const reader = new FileReader();
			reader.onload = async (event) => {
				const savedPrompts = JSON.parse(event.target.result);
				console.log(savedPrompts);

				try {
					for (const prompt of savedPrompts) {
						await createNewPrompt(localStorage.token, {
							command: prompt.command,
							name: prompt.name,
							content: prompt.content
						}).catch((error) => {
							toast.error(typeof error === 'string' ? error : JSON.stringify(error));
							return null;
						});
					}

					page = 1;
					await getPromptList();
				} finally {
					importFiles = null;
					promptsImportInputElement.value = '';
				}
			};

			reader.readAsText(importFiles[0]);
		}}
	/>

	<div class="space-y-1">
		<div class="flex h-8 w-full items-center gap-2">
			<div class="flex min-w-0 flex-1">
				<div class=" self-center ml-1 mr-3">
					<Search className="size-3.5" />
				</div>
				<input
					class=" w-full text-sm pr-4 py-1 rounded-r-xl outline-hidden bg-transparent"
					bind:value={query}
					on:input={handleSearchInput}
					aria-label={$i18n.t('Search Prompts')}
					placeholder={$i18n.t('Search Prompts')}
				/>

				{#if query}
					<div class="self-center pl-1.5 translate-y-[0.5px] rounded-l-xl bg-transparent">
						<button
							class="p-0.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
							aria-label={$i18n.t('Clear search')}
							on:click={() => {
								query = '';
								handleSearchInput();
							}}
						>
							<XMark className="size-3" strokeWidth="2" />
						</button>
					</div>
				{/if}
			</div>

			<div
				class="flex max-w-[55%] shrink-0 overflow-x-auto scrollbar-none"
				bind:this={tagsContainerElement}
				on:wheel={(e) => {
					if (e.deltaY !== 0) {
						e.preventDefault();
						e.currentTarget.scrollLeft += e.deltaY;
					}
				}}
			>
				<div
					class="flex w-fit gap-0.5 text-center text-sm rounded-full bg-transparent whitespace-nowrap"
				>
					<ViewSelector
						bind:value={viewOption}
						align="end"
						onChange={async (value) => {
							localStorage.workspaceViewOption = value;
							page = 1;
							await tick();
						}}
					/>

					{#if (tags ?? []).length > 0}
						<TagSelector
							bind:value={selectedTag}
							align="end"
							items={tags.map((tag) => ({ value: tag, label: tag }))}
						/>
					{/if}
				</div>
			</div>
		</div>

		{#if prompts === null || loading}
			<div class="w-full h-full flex justify-center items-center my-16 mb-24">
				<Spinner className="size-5" />
			</div>
		{:else if (prompts ?? []).length !== 0}
			<div class="my-1">
				<div
					class="flex w-full items-center gap-2 px-1.5 pb-0.5 text-xs text-gray-400 dark:text-gray-600"
				>
					<button
						class="flex min-w-0 flex-1 items-center gap-1 py-0.5 text-left"
						type="button"
						on:click={() => setSortKey('name')}
					>
						{$i18n.t('Title')}
						{#if sortKey === 'name'}
							{#if sortDirection === 'asc'}
								<ChevronUp className="size-2" />
							{:else}
								<ChevronDown className="size-2" />
							{/if}
						{/if}
					</button>

					<div class="hidden w-44 shrink-0 md:block"></div>

					<button
						class="flex w-36 shrink-0 items-center justify-end gap-1 py-0.5 text-right"
						type="button"
						on:click={() => setSortKey('updated_at')}
					>
						{$i18n.t('Updated at')}
						{#if sortKey === 'updated_at'}
							{#if sortDirection === 'asc'}
								<ChevronUp className="size-2" />
							{:else}
								<ChevronDown className="size-2" />
							{/if}
						{/if}
					</button>
				</div>

				<div class="grid gap-y-0.5">
					{#each prompts as prompt (prompt.id)}
						<div
							class="group flex min-h-8 w-full cursor-pointer items-center gap-2 overflow-hidden rounded-xl px-2 py-1 text-left"
							role="button"
							tabindex="0"
							on:click={(e) => {
								if (shouldIgnoreRowClick(e.target)) return;
								openPrompt(prompt);
							}}
							on:keydown={(e) => {
								if (e.currentTarget !== e.target) return;
								if (e.key === 'Enter' || e.key === ' ') {
									e.preventDefault();
									openPrompt(prompt);
								}
							}}
						>
							<div class="flex min-w-0 flex-1 items-center gap-1 overflow-hidden">
								<div class="flex min-w-0 flex-1 flex-col overflow-hidden">
									<div class="flex min-w-0 items-center gap-2 overflow-hidden">
										<div class="flex min-w-0 flex-1 items-center gap-2 overflow-hidden">
											<Tooltip content={prompt.name} className="min-w-0" placement="top-start">
												<div
													class="truncate text-[13px] leading-5 text-gray-800 group-hover:underline dark:text-gray-200"
												>
													{prompt.name}
												</div>
											</Tooltip>

											<div
												class="min-w-0 max-w-[40%] shrink-0 truncate text-[11px] leading-5 text-gray-500"
											>
												/{prompt.command}
											</div>

											<Tooltip
												content={dayjs((prompt.updated_at ?? prompt.created_at) * 1000).format(
													'LLLL'
												)}
											>
												<div
													class="shrink-0 truncate text-[11px] leading-5 text-gray-400 dark:text-gray-600"
												>
													{dayjs((prompt.updated_at ?? prompt.created_at) * 1000).fromNow()}
												</div>
											</Tooltip>

											{#if !prompt.write_access}
												<Badge type="muted" content={$i18n.t('Read Only')} />
											{/if}
										</div>
									</div>

									{#if prompt.content}
										<Tooltip content={prompt.content} className="min-w-0" placement="top-start">
											<div
												class="mt-0.5 truncate text-[0.6875rem] leading-4 text-gray-400 dark:text-gray-600"
											>
												{prompt.content}
											</div>
										</Tooltip>
									{/if}
								</div>
							</div>

							<div
								class="hidden max-w-44 shrink-0 self-center truncate text-right text-[11px] leading-5 text-gray-500 dark:text-gray-500 md:block"
							>
								<Tooltip
									content={prompt?.user?.email ?? $i18n.t('Deleted User')}
									className="min-w-0"
									placement="top-start"
								>
									<div class="truncate">
										{capitalizeFirstLetter(
											prompt?.user?.name ?? prompt?.user?.email ?? $i18n.t('Deleted User')
										)}
									</div>
								</Tooltip>
							</div>

							<div class="ml-2 flex shrink-0 flex-row items-center self-center">
								{#if shiftKey}
									<Tooltip content={$i18n.t('Delete')}>
										<button
											class="flex size-6 items-center justify-center rounded-lg text-gray-400 transition dark:text-gray-500"
											type="button"
											aria-label={$i18n.t('Delete')}
											on:click={(e) => {
												e.preventDefault();
												e.stopPropagation();
												deleteHandler(prompt);
											}}
										>
											<GarbageBin className="size-4" />
										</button>
									</Tooltip>
								{:else}
									<Tooltip content={$i18n.t('Copy Prompt')}>
										<button
											class="flex size-6 items-center justify-center rounded-lg text-gray-400 transition dark:text-gray-500"
											type="button"
											aria-label={$i18n.t('Copy Prompt')}
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

									<div class="ml-0.5 flex shrink-0 flex-row items-center gap-1.5 self-center">
										<PromptMenu
											show={openPromptMenuId === prompt.id}
											editHandler={() => {
												goto(`/workspace/prompts/${prompt.id}`);
											}}
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
											onClose={() => {
												openPromptMenuId = null;
											}}
										>
											<button
												class="flex size-6 items-center justify-center rounded-lg text-gray-400 transition dark:text-gray-500"
												type="button"
												aria-label={$i18n.t('Prompt Menu')}
												on:click={(e) => {
													e.preventDefault();
													e.stopPropagation();
													openPromptMenuId = openPromptMenuId === prompt.id ? null : prompt.id;
												}}
											>
												<EllipsisHorizontal className="size-4" />
											</button>
										</PromptMenu>

										<button
											class="flex h-6 items-center"
											type="button"
											on:click={(e) => {
												e.stopPropagation();
												e.preventDefault();
											}}
										>
											<Tooltip
												content={prompt.is_active !== false
													? $i18n.t('Enabled')
													: $i18n.t('Disabled')}
											>
												<Switch
													bind:state={prompt.is_active}
													on:change={async () => {
														togglePromptById(localStorage.token, prompt.id);
													}}
												/>
											</Tooltip>
										</button>
									</div>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			</div>

			{#if total > 30}
				<div class="flex justify-center mt-4 mb-2">
					<Pagination bind:page count={total} perPage={30} />
				</div>
			{/if}
		{:else}
			<div class="flex w-full flex-col items-center justify-center py-16 pb-24">
				<div class="max-w-sm text-center text-gray-900 dark:text-gray-100">
					<div class="mb-1.5 text-sm">{$i18n.t('No prompts found')}</div>
					<div class="text-center text-xs leading-5 text-gray-500">
						{$i18n.t('Try adjusting your search or filter to find what you are looking for.')}
					</div>
				</div>
			</div>
		{/if}
	</div>

	{#if $config?.features.enable_community_sharing}
		<CommunityDiscover
			href="https://openwebui.com/prompts"
			title={$i18n.t('Discover a prompt')}
			description={$i18n.t('Discover, download, and explore custom prompts')}
		/>
	{/if}
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner className="size-5" />
	</div>
{/if}
