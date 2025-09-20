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
	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import PencilSquare from '../icons/PencilSquare.svelte';
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

	<div class="flex flex-col gap-1 my-1.5">
		<div class="flex justify-between items-center mb-4">
			<div class="flex md:self-center text-2xl font-semibold px-0.5 items-center">
				{$i18n.t('Knowledge')}
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
					placeholder={$i18n.t('Search Knowledge')}
				/>
			</div>

			<!-- 功能按钮组 - 紧凑排列 -->
			<div class="flex items-center space-x-2">
				<!-- + 图标按钮 -->
				<button
					class=" px-3 py-3 rounded-lg bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 dark:text-gray-200 transition font-medium text-sm flex items-center space-x-1"
					aria-label={$i18n.t('Create Knowledge')}
					on:click={() => {
						goto('/workspace/knowledge/create');
					}}
				>
					<Plus className="size-5" />
				</button>
			</div>
		</div>
	</div>

	<div class=" my-6 mb-5 gap-5 grid lg:grid-cols-2 xl:grid-cols-3">
		{#each filteredItems as item}
			<div
				class=" flex flex-col cursor-pointer w-full px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-800 dark:hover:bg-gray-700 hover:bg-gray-100 transition"
			>
				<div class="flex flex-col w-full overflow-hidden mt-0.5 mb-0.5">
					<div class="text-left w-full">
						<div class="flex flex-col w-full overflow-hidden">
							<!-- 第一行：图标 + 名称 -->
							<div class="flex items-center gap-2 mb-1">
								{#if item?.meta?.document}
									<svg class="w-5 h-5 text-gray-900 dark:text-gray-100 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
									</svg>
								{:else}
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="none" class="w-5 h-5 text-gray-900 dark:text-gray-100 flex-shrink-0" stroke="currentColor" stroke-width="1.8">
										<path d="M2.08301 2.5H16.2497C16.2497 2.5 17.9163 3.33333 17.9163 5.41667C17.9163 7.5 16.2497 8.33333 16.2497 8.33333H2.08301C2.08301 8.33333 3.74967 7.5 3.74967 5.41667C3.74967 3.33333 2.08301 2.5 2.08301 2.5Z" stroke-linecap="round" stroke-linejoin="round"/>
										<path d="M17.9163 11.6667H3.74967C3.74967 11.6667 2.08301 12.5001 2.08301 14.5834C2.08301 16.6667 3.74967 17.5001 3.74967 17.5001H17.9163C17.9163 17.5001 16.2497 16.6667 16.2497 14.5834C16.2497 12.5001 17.9163 11.6667 17.9163 11.6667Z" stroke-linecap="round" stroke-linejoin="round"/>
									</svg>
								{/if}
								<div class=" text-base font-medium line-clamp-1 text-gray-900 dark:text-gray-100">
									{item.name}
								</div>
							</div>
							
							<!-- 第二行：Description -->
							<div class=" text-xs text-gray-400 dark:text-gray-500 line-clamp-1">
								{item.description}
							</div>
						</div>
					</div>

					<div class="flex justify-between items-center -mb-0.5 px-0.5 mt-1">
						<div class=" text-xs">
							<Tooltip
								content={item?.user?.email ?? $i18n.t('Deleted User')}
								className="flex shrink-0"
								placement="top-start"
							>
								<div class="shrink-0 text-gray-500">
									{$i18n.t('By {{name}}', {
										name: capitalizeFirstLetter(
											item?.user?.name ?? item?.user?.email ?? $i18n.t('Deleted User')
										)
									})}
								</div>
							</Tooltip>
						</div>

						<div class="flex flex-row gap-0.5 items-center">
							{#if !item?.meta?.document}
								<a
									class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
									href={`/workspace/knowledge/${item.id}`}
								>
									<PencilSquare className="w-4 h-4" strokeWidth="1.5" />
								</a>
							{/if}
							<ItemMenu
								on:delete={() => {
									selectedItem = item;
									showDeleteConfirm = true;
								}}
							>
								<button
									class="self-center w-fit text-sm p-1.5 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
									type="button"
								>
									<EllipsisHorizontal className="size-5" />
								</button>
							</ItemMenu>
						</div>
					</div>
				</div>
			</div>
		{/each}
	</div>

	<div class=" text-gray-500 text-xs mt-1 mb-2">
		ⓘ {$i18n.t("Use '#' in the prompt input to load and include your knowledge.")}
	</div>
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner />
	</div>
{/if}
