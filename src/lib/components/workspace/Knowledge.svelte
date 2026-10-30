<script lang="ts">
	import Comments from '$lib/components/comments/Comments.svelte';
	import type { CommentsRequest } from '$lib/components/comments/CommentsPanel.svelte';
	let comments: CommentsRequest | null = null;
	import CommentButton from '$lib/components/comments/CommentButton.svelte';
	import WorkspaceAccessModal from './common/WorkspaceAccessModal.svelte';
	let accessModal: WorkspaceAccessModal;
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { toast } from 'svelte-sonner';
	import { onMount, getContext, tick, onDestroy } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');

	import { WEBUI_NAME, user, workspaceActions, workspaceCounts } from '$lib/stores';
	import {
		deleteKnowledgeById,
		searchKnowledgeBases,
		exportKnowledgeById
	} from '$lib/apis/knowledge';

	import { goto } from '$app/navigation';
	import { capitalizeFirstLetter } from '$lib/utils';

	import DeleteConfirmDialog from '../common/ConfirmDialog.svelte';
	import ItemMenu from './Knowledge/ItemMenu.svelte';
	import KnowledgeEditor from './Knowledge/KnowledgeEditor.svelte';
	import Badge from '../common/Badge.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';
	import ChevronUp from '../icons/ChevronUp.svelte';
	import Modal from '../common/Modal.svelte';
	import Search from '../icons/Search.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import ProfilePreview from '$lib/components/channel/Messages/Message/ProfilePreview.svelte';
	import ProfileImage from '$lib/components/chat/Messages/ProfileImage.svelte';
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
	let searchController: AbortController;
	let viewOption = '';
	let sourceOption = '';
	let sortKey = 'updated_at';
	let sortDirection = 'desc';

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
		searchController?.abort();
		itemsLoading = true;
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(() => {
			init();
		}, 300);
	};

	onDestroy(() => {
		searchController?.abort();
		clearTimeout(searchDebounceTimer);
	});

	$: if (
		loaded &&
		viewOption !== undefined &&
		sourceOption !== undefined &&
		sortKey !== undefined &&
		sortDirection !== undefined
	) {
		init();
	}

	const setSortKey = (key: string) => {
		if (sortKey === key) {
			sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
		} else {
			sortKey = key;
			sortDirection = key === 'updated_at' ? 'desc' : 'asc';
		}
	};

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
		clearTimeout(searchDebounceTimer);
		searchController?.abort();
		searchController = new AbortController();
		const { signal } = searchController;

		itemsLoading = true;
		const res = await searchKnowledgeBases(
			localStorage.token,
			query,
			viewOption,
			page,
			sourceOption,
			sortKey,
			sortDirection,
			signal
		).catch(() => {
			return [];
		});

		if (signal.aborted) return;

		if (res) {
			console.log(res);
			total = res.total;
			workspaceCounts.update((counts) => ({ ...counts, knowledge: total }));
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
		await tick();

		if (items === null && !itemsLoading) {
			await init();
		}

		if (showCreateOnMount) {
			showCreateModal = true;
		}
	});
</script>

<WorkspaceAccessModal bind:this={accessModal} resourceType="knowledge" onUpdated={init} />

<svelte:head>
	<!-- LICENSE covers this Open WebUI browser-title identifier.
	Do not alter, remove, obscure, or replace it except as LICENSE permits:
	https://docs.openwebui.com/license. -->
	<title>
		{$i18n.t('Knowledge')} / {$WEBUI_NAME}
	</title>
</svelte:head>

<h1 class="sr-only">{$i18n.t('Knowledge')}</h1>

<Comments modal bind:view={comments} resourceType="knowledge">
{#if loaded}
	<DeleteConfirmDialog
		bind:show={showDeleteConfirm}
		on:confirm={() => {
			deleteHandler(selectedItem);
		}}
	/>

	<Modal bind:show={showCreateModal} size="md" ariaLabel={$i18n.t('Create a knowledge base')}>
		<KnowledgeEditor
			modal={true}
			onBack={() => {
				closeCreateModal();
			}}
		/>
	</Modal>

	<div class="space-y-0">
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
							class="py-0.5 rounded-full transition hover:text-gray-900 dark:hover:text-gray-100 text-gray-500 dark:text-gray-400 px-0"
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
				<div class="@container">
					<div
						class="grid grid-cols-[minmax(0,1fr)_9rem_8rem_7.5rem] items-center gap-x-4 px-2 @max-[48rem]:grid-cols-[minmax(0,1fr)_7rem_7.5rem] @max-[48rem]:gap-x-3 @max-[36rem]:grid-cols-[minmax(0,1fr)_7.5rem] @max-[36rem]:gap-x-2 min-h-6 text-xs text-gray-500 dark:text-gray-400"
					>
						<button
							class="flex min-w-0 flex-1 items-center gap-1 py-0.5 text-left"
							type="button"
							on:click={() => setSortKey('name')}
						>
							{$i18n.t('Name')}
							{#if sortKey === 'name'}
								{#if sortDirection === 'asc'}
									<ChevronUp className="size-2" />
								{:else}
									<ChevronDown className="size-2" />
								{/if}
							{/if}
						</button>

						<div class="@max-[48rem]:hidden">{$i18n.t('Owner')}</div>

						<button
							class="@max-[36rem]:hidden flex min-w-0 items-center gap-1 py-0.5 text-left"
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
						<span class="sr-only">{$i18n.t('Actions')}</span>
					</div>

					<div class="grid gap-y-0.5">
						{#each items as item}
							{@const metaPreview = getKnowledgeMetaPreview(item)}
							<div
								class="grid grid-cols-[minmax(0,1fr)_9rem_8rem_7.5rem] items-center gap-x-4 px-2 @max-[48rem]:grid-cols-[minmax(0,1fr)_7rem_7.5rem] @max-[48rem]:gap-x-3 @max-[36rem]:grid-cols-[minmax(0,1fr)_7.5rem] @max-[36rem]:gap-x-2 min-h-12 rounded-lg py-1.5 hover:bg-black/[0.03] dark:hover:bg-white/[0.03] group cursor-pointer text-left"
								role="presentation"
								on:click={(e) => {
									if (shouldIgnoreRowClick(e.target)) return;
									openKnowledge(item);
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
													{#if !item?.meta?.document}
														<a
															href={`/workspace/knowledge/${item.id}`}
															class="focus-ring block truncate rounded text-[0.8125rem] leading-5 text-gray-800 group-hover:underline focus-visible:underline dark:text-gray-200"
															>{item.name}</a
														>
													{:else}
														<span
															class="block truncate text-[0.8125rem] leading-5 text-gray-800 group-hover:underline dark:text-gray-200"
															>{item.name}</span
														>
													{/if}
												</Tooltip>
												{#if !item?.write_access || item?.meta?.source === 'external'}
													<Badge type="subtle" content={$i18n.t('Read Only')} />
												{/if}

												{#if item?.meta?.source === 'external'}
													<Badge
														type="muted"
														content={item?.meta?.external?.provider ?? $i18n.t('Connected')}
													/>
												{/if}
											</div>
										</div>

										<div class="mt-0.5 min-w-0">
											{#if metaPreview}
												<Tooltip content={metaPreview} className="min-w-0" placement="top-start">
													<div class="truncate text-xs leading-4 text-gray-500 dark:text-gray-400">
														{metaPreview}
													</div>
												</Tooltip>
											{/if}
										</div>
									</div>
								</div>

								<div
									class="@max-[48rem]:hidden min-w-0 text-xs text-gray-600 dark:text-gray-400"
								>
									<ProfilePreview
										user={item?.user ?? null}
										side="bottom"
										className="w-full min-w-0"
									>
										<span class="flex w-full min-w-0 items-center gap-2">
											<ProfileImage
												src={item?.user?.id
													? `/api/v1/users/${item.user.id}/profile/image`
													: '/user.png'}
												className="size-5 shrink-0 rounded-full!"
											/>
											<span class="min-w-0 truncate">
												{capitalizeFirstLetter(
													item?.user?.name ?? item?.user?.email ?? $i18n.t('Deleted User')
												)}
											</span>
										</span>
									</ProfilePreview>
								</div>
								<Tooltip
									content={dayjs(item.updated_at * 1000)
										.locale($i18n.language)
										.format('LLLL')}
									className="@max-[36rem]:hidden min-w-0"
								>
									<div class="shrink-0 truncate text-xs leading-5 text-gray-500 dark:text-gray-400">
										{dayjs(item.updated_at * 1000)
											.locale($i18n.language)
											.fromNow()}
									</div>
								</Tooltip>
								<div
									class="flex min-w-0 items-center justify-end gap-1.5"
								>
									<CommentButton onComment={(request) => (comments = request)}
										modal
										className="flex size-6 shrink-0 items-center justify-center rounded-lg text-gray-400 transition dark:text-gray-500"
										resource={{ resource_type: 'knowledge', resource_id: item.id }}
									/>
									{#if item?.write_access || $user?.role === 'admin'}
										<div class="flex shrink-0 flex-row items-center self-center">
											<ItemMenu onComment={(request) => (comments = request)}
												resourceId={item.id}
												accessHandler={$user?.permissions?.sharing?.knowledge ||
												$user?.role === 'admin'
													? () => accessModal.open(item.id)
													: null}
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
				<div class="flex w-full flex-col items-center justify-center py-16 pb-24">
					<div class="max-w-sm text-center text-gray-900 dark:text-gray-100">
						<div class="mb-1.5 text-sm">{$i18n.t('No knowledge found')}</div>
						<div class="text-center text-xs leading-5 text-gray-500">
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
</Comments>
