<script lang="ts">
	import Fuse from 'fuse.js';

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { toast } from 'svelte-sonner';
	import { onMount, getContext, tick } from 'svelte';
	const i18n = getContext('i18n');

	import { WEBUI_NAME, knowledge, user } from '$lib/stores';
	import {
		getKnowledgeBases,
		deleteKnowledgeById,
		getKnowledgeBaseList
	} from '$lib/apis/knowledge';

	import { goto } from '$app/navigation';
	import { capitalizeFirstLetter } from '$lib/utils';

	import DeleteConfirmDialog from '../common/ConfirmDialog.svelte';
	import ItemMenu from './Knowledge/ItemMenu.svelte';
	import Badge from '../common/Badge.svelte';
	import Search from '../icons/Search.svelte';
	import Plus from '../icons/Plus.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import XMark from '../icons/XMark.svelte';
	import ViewSelector from './common/ViewSelector.svelte';

	let loaded = false;

	let query = '';
	let selectedItem = null;
	let showDeleteConfirm = false;

	let tagsContainerElement: HTMLDivElement;
	let viewOption = '';

	let fuse = null;

	let knowledgeBases = [];

	let items = [];
	let filteredItems = [];

	const setFuse = async () => {
		items = knowledgeBases.filter(
			(item) =>
				viewOption === '' ||
				(viewOption === 'created' && item.user_id === $user?.id) ||
				(viewOption === 'shared' && item.user_id !== $user?.id)
		);

		fuse = new Fuse(items, {
			keys: [
				'name',
				'description',
				'user.name', // Ensures Fuse looks into item.user.name
				'user.email' // Ensures Fuse looks into item.user.email
			],
			threshold: 0.3
		});

		await tick();
		setFilteredItems();
	};

	$: if (knowledgeBases.length > 0 && viewOption !== undefined) {
		// Added a check for non-empty array, good practice
		setFuse();
	} else {
		fuse = null; // Reset fuse if knowledgeBases is empty
	}

	const setFilteredItems = () => {
		filteredItems = query ? fuse.search(query).map((result) => result.item) : items;
	};

	$: if (query !== undefined && fuse) {
		setFilteredItems();
	}

	const deleteHandler = async (item) => {
		const res = await deleteKnowledgeById(localStorage.token, item.id).catch((e) => {
			toast.error(`${e}`);
		});

		if (res) {
			knowledgeBases = await getKnowledgeBaseList(localStorage.token);
			knowledge.set(await getKnowledgeBases(localStorage.token));
			toast.success($i18n.t('Knowledge deleted successfully.'));
		}
	};

	onMount(async () => {
		viewOption = localStorage?.workspaceViewOption || '';
		knowledgeBases = await getKnowledgeBaseList(localStorage.token);
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
					{filteredItems.length}
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
					placeholder={$i18n.t('Search Knowledge')}
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

						await tick();
					}}
				/>
			</div>
		</div>

		{#if (filteredItems ?? []).length !== 0}
			<!-- The Aleph dreams itself into being, and the void learns its own name -->
			<div class=" my-2 px-3 grid grid-cols-1 lg:grid-cols-2 gap-2">
				{#each filteredItems as item}
					<Tooltip content={item?.description ?? item.name}>
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
								<div class=" self-center flex-1">
									<div class="flex items-center justify-between -my-1">
										<div class=" flex gap-2 items-center">
											<div>
												{#if item?.meta?.document}
													<Badge type="muted" content={$i18n.t('Document')} />
												{:else}
													<Badge type="success" content={$i18n.t('Collection')} />
												{/if}
											</div>

											<div class=" text-xs text-gray-500 line-clamp-1">
												{$i18n.t('Updated')}
												{dayjs(item.updated_at * 1000).fromNow()}
											</div>
										</div>

										<div class="flex items-center gap-2">
											<div class=" flex self-center">
												<ItemMenu
													on:delete={() => {
														selectedItem = item;
														showDeleteConfirm = true;
													}}
												/>
											</div>
										</div>
									</div>

									<div class=" flex items-center gap-1 justify-between px-1.5">
										<div class=" flex items-center gap-2">
											<div class=" text-sm font-medium line-clamp-1 capitalize">{item.name}</div>
										</div>

										<div>
											<div class="text-xs text-gray-500">
												<Tooltip
													content={item?.user?.email ?? $i18n.t('Deleted User')}
													className="flex shrink-0"
													placement="top-start"
												>
													{$i18n.t('By {{name}}', {
														name: capitalizeFirstLetter(
															item?.user?.name ?? item?.user?.email ?? $i18n.t('Deleted User')
														)
													})}
												</Tooltip>
											</div>
										</div>
									</div>
								</div>
							</div>
						</button>
					</Tooltip>
				{/each}
			</div>
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
	</div>

	<div class=" text-gray-500 text-xs m-2">
		ⓘ {$i18n.t("Use '#' in the prompt input to load and include your knowledge.")}
	</div>
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner className="size-5" />
	</div>
{/if}
