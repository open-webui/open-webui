<script lang="ts">
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { toast } from 'svelte-sonner';
	import { onMount, getContext, tick, onDestroy } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');

	import { WEBUI_NAME, user, workspaceActions } from '$lib/stores';
	import {
		deleteKnowledgeById,
		searchKnowledgeBases,
		exportKnowledgeById
	} from '$lib/apis/knowledge';

	import { goto } from '$app/navigation';
	import { capitalizeFirstLetter } from '$lib/utils';

	import DeleteConfirmDialog from '../common/ConfirmDialog.svelte';
	import ItemMenu from './Knowledge/ItemMenu.svelte';
	import CreateKnowledgeBase from './Knowledge/CreateKnowledgeBase.svelte';
	import Badge from '../common/Badge.svelte';
	import Modal from '../common/Modal.svelte';
	import Search from '../icons/Search.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import XMark from '../icons/XMark.svelte';
	import ViewSelector from './common/ViewSelector.svelte';
	import TagSelector from './common/TagSelector.svelte';
	import Loader from '../common/Loader.svelte';

	type KnowledgeListItem = {
		id: string;
		name: string;
		description?: string;
		updated_at: number;
		file_count?: number;
		write_access?: boolean;
		meta?: any;
		user?: {
			name?: string;
			email?: string;
		};
	};

	export let showCreateOnMount = false;
	export let createModalCloseHref = '';

	let loaded = false;
	let showDeleteConfirm = false;
	let showCreateModal = false;
	let tagsContainerElement: HTMLDivElement;

	let selectedItem: KnowledgeListItem | null = null;

	let page = 1;
	let query = '';
	let searchDebounceTimer: ReturnType<typeof setTimeout>;
	let viewOption = '';
	let sourceOption = '';

	let items: KnowledgeListItem[] | null = null;
	let total: number | null = null;

	let allItemsLoaded = false;
	let itemsLoading = false;

	$: if (loaded) {
		workspaceActions.set([
			{
				id: 'knowledge-new',
				label: $i18n.t('Create'),
				onClick: () => {
					showCreateModal = true;
				}
			}
		]);
	}

	const handleSearchInput = () => {
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(() => {
			init();
		}, 300);
	};

	onDestroy(() => {
		clearTimeout(searchDebounceTimer);
	});

	$: if (loaded && viewOption !== undefined && sourceOption !== undefined) {
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
		const res = await searchKnowledgeBases(
			localStorage.token,
			query,
			viewOption,
			page,
			sourceOption
		).catch(() => {
			return [];
		});

		if (res) {
			console.log(res);
			total = res.total;
			const pageItems: KnowledgeListItem[] = res.items ?? [];

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

	const deleteHandler = async (item: KnowledgeListItem | null) => {
		if (!item) return;

		const res = await deleteKnowledgeById(localStorage.token, item.id).catch((e) => {
			toast.error(`${e}`);
		});

		if (res) {
			toast.success($i18n.t('Knowledge deleted successfully.'));
			init();
		}
	};

	const closeCreateModal = async () => {
		showCreateModal = false;

		if (createModalCloseHref) {
			await goto(createModalCloseHref);
		}
	};

	const exportHandler = async (item: KnowledgeListItem) => {
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

	const openKnowledge = (item: KnowledgeListItem) => {
		if (item?.meta?.document) {
			toast.error(
				$i18n.t(
					'Only collections can be edited, create a new knowledge base to edit/add documents.'
				)
			);
			return;
		}

		goto(`/workspace/knowledge/${item.id}`);
	};

	const shouldIgnoreRowClick = (target: EventTarget | null) => {
		return target instanceof Element && !!target.closest('button, a, input, [role="menu"]');
	};

	const getKnowledgeMetaPreview = (item: KnowledgeListItem) => {
		const fileCount =
			item.file_count !== undefined
				? item.file_count === 1
					? $i18n.t('1 file')
					: $i18n.t('{{count}} files', { count: item.file_count })
				: null;

		if (!item?.meta) return [fileCount, item.description].filter(Boolean).join(' · ');

		if (item.meta.source === 'external') {
			return [
				fileCount,
				item.meta.external?.provider,
				item.meta.external?.source?.name,
				item.meta.external?.auth_mode,
				item.description
			]
				.filter(Boolean)
				.join(' · ');
		}

		const metadata = Object.entries(item.meta)
			.filter(([, value]) => value !== null && value !== undefined && value !== '')
			.map(([key, value]) => {
				if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
					return `${key}: ${value}`;
				}

				return key;
			})
			.join(' · ');

		return [fileCount, metadata, item.description].filter(Boolean).join(' · ');
	};

	onMount(async () => {
		viewOption = localStorage?.workspaceViewOption || '';
		sourceOption = localStorage?.workspaceKnowledgeSourceOption || '';
		loaded = true;

		if (showCreateOnMount) {
			showCreateModal = true;
		}
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

	<Modal bind:show={showCreateModal} size="md">
		<CreateKnowledgeBase
			modal={true}
			onBack={() => {
				closeCreateModal();
			}}
		/>
	</Modal>

	<div class="space-y-1">
		<div class="flex h-8 w-full items-center gap-2">
			<div class="flex min-w-0 flex-1">
				<div class=" self-center ml-1 mr-3">
					<Search className="size-3.5" />
				</div>
				<input
					class=" w-full text-sm py-1 rounded-r-xl outline-hidden bg-transparent"
					bind:value={query}
					on:input={handleSearchInput}
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

							await tick();
						}}
					/>

					<TagSelector
						bind:value={sourceOption}
						align="end"
						placeholder={$i18n.t('All Sources')}
						items={[
							{ value: 'local', label: $i18n.t('Local') },
							{ value: 'external', label: $i18n.t('Connected') }
						]}
						onChange={async () => {
							localStorage.workspaceKnowledgeSourceOption = sourceOption;
							await tick();
						}}
					/>
				</div>
			</div>
		</div>

		{#if items !== null && total !== null}
			{#if (items ?? []).length !== 0}
				<div class="my-1">
					<div
						class="flex w-full items-center gap-2 px-1.5 pb-0.5 text-xs text-gray-400 dark:text-gray-600"
					>
						<div class="flex min-w-0 flex-1 items-center gap-1 py-0.5 text-left">
							{$i18n.t('Title')}
						</div>

						<div class="hidden w-44 shrink-0 md:block"></div>

						<div class="flex w-36 shrink-0 items-center justify-end gap-1 py-0.5 text-right">
							{$i18n.t('Updated at')}
						</div>
					</div>

					<div class="grid gap-y-0.5">
						{#each items as item}
							{@const metaPreview = getKnowledgeMetaPreview(item)}
							<div
								class="group flex min-h-8 w-full cursor-pointer items-center gap-2 overflow-hidden rounded-xl px-2 py-1 text-left"
								role="button"
								tabindex="0"
								on:click={(e) => {
									if (shouldIgnoreRowClick(e.target)) return;
									openKnowledge(item);
								}}
								on:keydown={(e) => {
									if (e.currentTarget !== e.target) return;
									if (e.key === 'Enter' || e.key === ' ') {
										e.preventDefault();
										openKnowledge(item);
									}
								}}
							>
								<div class="flex min-w-0 flex-1 items-center gap-1 overflow-hidden">
									<div class="flex min-w-0 flex-1 flex-col overflow-hidden">
										<div class="flex min-w-0 items-center gap-2 overflow-hidden">
											<div class="flex min-w-0 flex-1 items-center gap-2 overflow-hidden">
												<Tooltip
													content={item?.description ?? item.name}
													className="min-w-0"
													placement="top-start"
												>
													<div
														class="truncate text-[13px] leading-5 text-gray-800 group-hover:underline dark:text-gray-200"
													>
														{item.name}
													</div>
												</Tooltip>

												{#if item?.meta?.source === 'external'}
													<Badge
														type="muted"
														content={item?.meta?.external?.provider ?? $i18n.t('Connected')}
													/>
													<Badge type="muted" content={$i18n.t('Read Only')} />
												{/if}

												{#if !item?.write_access && item?.meta?.source !== 'external'}
													<Badge type="muted" content={$i18n.t('Read Only')} />
												{/if}

												<Tooltip content={dayjs(item.updated_at * 1000).format('LLLL')}>
													<div
														class="shrink-0 truncate text-[11px] leading-5 text-gray-400 dark:text-gray-600"
													>
														{dayjs(item.updated_at * 1000).fromNow()}
													</div>
												</Tooltip>
											</div>
										</div>

										{#if metaPreview}
											<Tooltip content={metaPreview} className="min-w-0" placement="top-start">
												<div
													class="mt-0.5 truncate text-[0.6875rem] leading-4 text-gray-400 dark:text-gray-600"
												>
													{metaPreview}
												</div>
											</Tooltip>
										{/if}
									</div>
								</div>

								<div
									class="hidden max-w-44 shrink-0 self-center truncate text-right text-[11px] leading-5 text-gray-500 dark:text-gray-500 md:block"
								>
									<Tooltip
										content={item?.user?.email ?? $i18n.t('Deleted User')}
										className="min-w-0"
										placement="top-start"
									>
										<div class="truncate">
											{capitalizeFirstLetter(
												item?.user?.name ?? item?.user?.email ?? $i18n.t('Deleted User')
											)}
										</div>
									</Tooltip>
								</div>

								{#if item?.write_access || $user?.role === 'admin'}
									<div class="ml-2 flex shrink-0 flex-row items-center self-center">
										<ItemMenu
											onExport={$user?.role === 'admin'
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
						{/each}
					</div>
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
						<div class=" text-lg font-normal mb-1">{$i18n.t('No knowledge found')}</div>
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
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner className="size-5" />
	</div>
{/if}
