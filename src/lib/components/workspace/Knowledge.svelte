<script lang="ts">
	import Fuse from 'fuse.js';

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { WEBUI_NAME, knowledge } from '$lib/stores';
	import {
		getKnowledgeBases,
		deleteKnowledgeById,
		getKnowledgeBaseList
	} from '$lib/apis/knowledge';

	import { goto } from '$app/navigation';

	import DeleteConfirmDialog from '../common/ConfirmDialog.svelte';
	import ItemMenu from './Knowledge/ItemMenu.svelte';
	import Badge from '../common/Badge.svelte';
	import Search from '../icons/Search.svelte';
	import Plus from '../icons/Plus.svelte';
	import Spinner from '../common/Spinner.svelte';
	import { capitalizeFirstLetter } from '$lib/utils';
	import Tooltip from '../common/Tooltip.svelte';

	let loaded = false;

	let query = '';
	let selectedItem = null;
	let showDeleteConfirm = false;

	let fuse = null;

	let knowledgeBases = [];
	let filteredItems = [];

	$: if (knowledgeBases) {
		fuse = new Fuse(knowledgeBases, {
			keys: ['name', 'description']
		});
	}

	$: if (fuse) {
		filteredItems = query
			? fuse.search(query).map((e) => {
					return e.item;
				})
			: knowledgeBases;
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
		knowledgeBases = await getKnowledgeBaseList(localStorage.token);
		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Knowledge')} | {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<DeleteConfirmDialog
		bind:show={showDeleteConfirm}
		on:confirm={() => {
			deleteHandler(selectedItem);
		}}
	/>

	<div class="flex flex-col gap-4 my-4">
		<!-- Header Section -->
		<div class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
			<div class="flex items-center gap-3">
				<h1 class="text-2xl font-semibold text-gray-900 dark:text-white">
					{$i18n.t('Knowledge')}
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
						placeholder={$i18n.t('Search Knowledge')}
					/>
				</div>

				<Tooltip content={$i18n.t('Create Knowledge')}>
					<button
						class="p-2.5 rounded-lg bg-orange-600 hover:bg-orange-700 text-white transition-colors shadow-sm hover:shadow-md"
						aria-label={$i18n.t('Create Knowledge')}
						on:click={() => {
							goto('/workspace/knowledge/create');
						}}
					>
						<Plus className="size-4" />
					</button>
				</Tooltip>
			</div>
		</div>

		<!-- Knowledge Grid -->
		<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
			{#each filteredItems as item}
				<button
					class="group bg-white dark:bg-gray-850 border border-gray-200 dark:border-gray-700 rounded-xl p-4 hover:shadow-lg hover:border-gray-300 dark:hover:border-gray-600 transition-all duration-200 text-left"
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
					<!-- Card Header -->
					<div class="flex items-center justify-between mb-3">
						{#if item?.meta?.document}
							<Badge type="muted" content={$i18n.t('Document')} />
						{:else}
							<Badge type="success" content={$i18n.t('Collection')} />
						{/if}

						<div class="opacity-0 group-hover:opacity-100 transition-opacity">
							<ItemMenu
								on:delete={() => {
									selectedItem = item;
									showDeleteConfirm = true;
								}}
							/>
						</div>
					</div>

					<!-- Card Content -->
					<div class="space-y-2">
						<h3 class="font-semibold text-gray-900 dark:text-white line-clamp-1">
							{item.name}
						</h3>

						<p class="text-sm text-gray-600 dark:text-gray-400 line-clamp-2 min-h-[2.5rem]">
							{item.description || $i18n.t('No description')}
						</p>
					</div>

					<!-- Card Footer -->
					<div class="flex items-center justify-between mt-4 pt-3 border-t border-gray-100 dark:border-gray-800">
						<Tooltip
							content={item?.user?.email ?? $i18n.t('Deleted User')}
							className="flex-shrink-0"
							placement="top-start"
						>
							<div class="text-xs text-gray-500 dark:text-gray-400 truncate">
								{$i18n.t('By {{name}}', {
									name: capitalizeFirstLetter(
										item?.user?.name ?? item?.user?.email ?? $i18n.t('Deleted User')
									)
								})}
							</div>
						</Tooltip>

						<div class="text-xs text-gray-500 dark:text-gray-400 flex-shrink-0 ml-2">
							{dayjs(item.updated_at * 1000).fromNow()}
						</div>
					</div>
				</button>
			{/each}
		</div>

		<!-- Info Message -->
		<div class="flex items-start gap-2 p-3 bg-orange-50 dark:bg-orange-900/20 border border-gray-200 dark:border-orange-800 rounded-lg">
			<div class="flex-shrink-0 mt-0.5">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="size-4 text-black-600 dark:text-blue-400"
				>
					<path
						fill-rule="evenodd"
						d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Zm-7-4a1 1 0 1 1-2 0 1 1 0 0 1 2 0ZM9 9a.75.75 0 0 0 0 1.5h.253a.25.25 0 0 1 .244.304l-.459 2.066A1.75 1.75 0 0 0 10.747 15H11a.75.75 0 0 0 0-1.5h-.253a.25.25 0 0 1-.244-.304l.459-2.066A1.75 1.75 0 0 0 9.253 9H9Z"
						clip-rule="evenodd"
					/>
				</svg>
			</div>
			<p class="text-sm text-black-800 dark:text-blue-300">
				{$i18n.t("Use '#' in the prompt input to load and include your knowledge.")}
			</p>
		</div>
	</div>
{:else}
	<div class="w-full h-full flex justify-center items-center py-12">
		<Spinner className="size-8" />
	</div>
{/if}