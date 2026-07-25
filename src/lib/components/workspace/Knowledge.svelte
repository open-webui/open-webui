<script lang="ts">
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { toast } from 'svelte-sonner';
	import { onMount, getContext, tick, onDestroy } from 'svelte';
	const i18n = getContext('i18n');

	import { WEBUI_NAME, knowledge, user } from '$lib/stores';
	import {
		deleteKnowledgeById,
		searchKnowledgeBases,
		exportKnowledgeById
	} from '$lib/apis/knowledge';

	import { goto } from '$app/navigation';
	import { capitalizeFirstLetter } from '$lib/utils';

	import DeleteConfirmDialog from '../common/ConfirmDialog.svelte';
	import ItemMenu from './Knowledge/ItemMenu.svelte';
	import Badge from '../common/Badge.svelte';
	import Search from '../icons/Search.svelte';
	import Plus from '../icons/Plus.svelte';
	import InfoCircle from '../icons/InfoCircle.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import XMark from '../icons/XMark.svelte';
	import ViewSelector from './common/ViewSelector.svelte';
	import Loader from '../common/Loader.svelte';

	let loaded = false;
	let showDeleteConfirm = false;
	let tagsContainerElement: HTMLDivElement;

	let selectedItem = null;

	let page = 1;
	let query = '';
	let searchDebounceTimer: ReturnType<typeof setTimeout>;
	let viewOption = '';

	let items = null;
	let total = null;

	let allItemsLoaded = false;
	let itemsLoading = false;

	$: if (query !== undefined) {
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(() => {
			init();
		}, 300);
	}

	onDestroy(() => {
		clearTimeout(searchDebounceTimer);
	});

	$: if (viewOption !== undefined) {
		init();
	}

	const reset = () => {
		page = 1;
		items = null;
		total = null;
		allItemsLoaded = false;
		itemsLoading = false;
	};

	const loadMoreItems = async () => {
		if (allItemsLoaded) return;
		page += 1;
		await getItemsPage();
	};

	const init = async () => {
		if (!loaded) return;

		reset();
		await getItemsPage();
	};

	const getItemsPage = async () => {
		itemsLoading = true;
		const res = await searchKnowledgeBases(localStorage.token, query, viewOption, page).catch(
			() => {
				return [];
			}
		);

		if (res) {
			console.log(res);
			total = res.total;
			const pageItems = res.items;

			if ((pageItems ?? []).length === 0) {
				allItemsLoaded = true;
			} else {
				allItemsLoaded = false;
			}

			if (items) {
				const existingIds = new Set(items.map((item) => item.id));
				const newItems = pageItems.filter((item) => !existingIds.has(item.id));
				items = [...items, ...newItems];
			} else {
				items = pageItems;
			}
		}

		itemsLoading = false;
		return res;
	};

	const deleteHandler = async (item) => {
		const res = await deleteKnowledgeById(localStorage.token, item.id).catch((e) => {
			toast.error(`${e}`);
		});

		if (res) {
			toast.success($i18n.t('Knowledge deleted successfully.'));
			init();
		}
	};

	// Escape + preserve line breaks for the AI-overview tooltip (DOMPurify also
	// sanitizes the rendered content).
	const overviewHtml = (text: string) =>
		(text ?? '')
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;')
			.replace(/\n/g, '<br/>');

	const exportHandler = async (item) => {
		try {
			const blob = await exportKnowledgeById(localStorage.token, item.id);
			if (blob) {
				const url = URL.createObjectURL(blob);
				const a = document.createElement('a');
				a.href = url;
				a.download = `${item.name}.zip`;
				document.body.appendChild(a);
				a.click();
				document.body.removeChild(a);
				URL.revokeObjectURL(url);
				toast.success($i18n.t('Knowledge exported successfully'));
			}
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	onMount(async () => {
		viewOption = localStorage?.workspaceViewOption || '';
		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Knowledge')} • {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<DeleteConfirmDialog
		bind:show={showDeleteConfirm}
		on:confirm={() => {
			deleteHandler(selectedItem);
		}}
	/>

	<div class="flex flex-col gap-1 px-1 mt-1.5 mb-3">
		<div class="flex justify-between items-center">
			<div class="flex items-center md:self-center text-xl font-medium px-0.5 gap-2 shrink-0">
				<div>
					{$i18n.t('Knowledge')}
				</div>

				<div class="text-lg font-medium text-gray-500 dark:text-gray-500">
					{total}
				</div>
			</div>

			<div class="flex w-full justify-end gap-1.5">
				<a
					class=" px-2 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black transition font-medium text-sm flex items-center"
					href="/workspace/knowledge/create"
				>
					<Plus className="size-3" strokeWidth="2.5" />

					<div class=" hidden md:block md:ml-1 text-xs">{$i18n.t('New Knowledge')}</div>
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
					class=" w-full text-sm py-1 rounded-r-xl outline-hidden bg-transparent"
					bind:value={query}
					aria-label={$i18n.t('Search Knowledge')}
					placeholder={$i18n.t('Search Knowledge')}
				/>
				{#if query}
					<div class="self-center pl-1.5 translate-y-[0.5px] rounded-l-xl bg-transparent">
						<button
							class="p-0.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
							aria-label={$i18n.t('Clear search')}
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

		{#if items !== null && total !== null}
			{#if (items ?? []).length !== 0}
				<!-- The Aleph dreams itself into being, and the void learns its own name -->
				<div class=" my-2 px-3 grid grid-cols-1 gap-0">
					{#each items as item}
						<button
							class=" flex space-x-4 cursor-pointer text-left w-full px-3 py-2.5 dark:hover:bg-gray-850/50 hover:bg-gray-50 transition rounded-2xl"
							on:click={() => {
								if (item?.meta?.document) {
									toast.error(
										$i18n.t(
											'Only collections can be edited, create a new knowledge base to edit/add documents.'
										)
									);
								} else {
									goto(`/workspace/knowledge/${item.id}`);
								}
							}}
						>
							<div class=" w-full">
								<div class=" self-center flex-1 justify-between">
									<div
										class=" grid grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)_auto] items-center gap-4 px-1.5 h-8"
									>
										<!-- Name -->
										<div class=" flex items-center gap-1.5 min-w-0">
											<Tooltip content={item?.description ?? item.name} className="min-w-0">
												<div class=" flex items-center gap-2 min-w-0">
													<div
														class=" text-sm font-medium line-clamp-1 capitalize text-green-700 dark:text-green-200"
													>
														{item.name}
													</div>
													{#if !item?.write_access}
														<Badge type="muted" content={$i18n.t('Read Only')} />
													{/if}
												</div>
											</Tooltip>

											{#if item?.ai_overwiew}
												<Tooltip
													content={overviewHtml(item.ai_overwiew)}
													placement="top"
													className="flex shrink-0"
												>
													<InfoCircle
														className="size-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
													/>
												</Tooltip>
											{/if}
										</div>

										<!-- Registration number -->
										<div class=" text-xs text-gray-500 line-clamp-1">
											{item?.registration_number ?? ''}
										</div>

										<!-- Registration date -->
										<div class=" text-xs text-gray-500 line-clamp-1">
											{item?.registration_date ? dayjs(item.registration_date).format('YYYY-MM-DD') : ''}
										</div>

										<!-- Menu -->
										<div class=" flex justify-end">
											{#if item?.write_access || $user?.role === 'admin'}
												<div class=" flex self-center">
													<ItemMenu
														onExport={$user.role === 'admin'
															? () => {
																	exportHandler(item);
																}
															: null}
														on:delete={() => {
															selectedItem = item;
															showDeleteConfirm = true;
														}}
													/>
												</div>
											{/if}
										</div>
									</div>
								</div>
							</div>
						</button>
					{/each}
				</div>

				{#if !allItemsLoaded}
					<Loader
						on:visible={(e) => {
							if (!itemsLoading) {
								loadMoreItems();
							}
						}}
					>
						<div class="w-full flex justify-center py-4 text-xs animate-pulse items-center gap-2">
							<Spinner className=" size-4" />
							<div class=" ">{$i18n.t('Loading...')}</div>
						</div>
					</Loader>
				{/if}
			{:else}
				<div class=" w-full h-full flex flex-col justify-center items-center my-16 mb-24">
					<div class="max-w-md text-center">
						<div class=" text-3xl mb-3">😕</div>
						<div class=" text-lg font-medium mb-1">{$i18n.t('No knowledge found')}</div>
						<div class=" text-gray-500 text-center text-xs">
							{$i18n.t('Try adjusting your search or filter to find what you are looking for.')}
						</div>
					</div>
				</div>
			{/if}
		{:else}
			<div class="w-full h-full flex justify-center items-center py-10">
				<Spinner className="size-4" />
			</div>
		{/if}
	</div>

	<div class=" text-gray-500 text-xs m-2">
		ⓘ {$i18n.t("Use '#' in the prompt input to load and include your knowledge.")}
	</div>
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner className="size-5" />
	</div>
{/if}
