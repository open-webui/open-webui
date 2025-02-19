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

	<div class="flex flex-col gap-10 my-1.5">
		<div class="flex justify-center items-center">
			<div class="text-2xl font-medium px-0.5">
				{$i18n.t('Knowledge')}
			</div>
		</div>

		<div class="flex flex-1 items-center w-full space-x-2 justify-center">
			<div class="flex items-center max-w-md w-full fr-background-contrast--grey rounded-md">
				<div class="self-center ml-1 mr-3">
					<Search className="size-6" />
				</div>
				<input
					class="w-full text-sm py-2.5 rounded-r-xl outline-hidden bg-transparent"
					bind:value={query}
					placeholder={$i18n.t('Search Knowledge')}
				/>
			</div>
		</div>
	</div>

	<div class="my-4 grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-2">
		<a
			href="/workspace/knowledge/create"
			class="flex flex-col justify-center items-center cursor-pointer w-full px-3 py-8 dark:hover:bg-white/5 hover:bg-black/5 rounded-xl transition border border-gray-100 dark:border-gray-800 min-h-[200px]"
		>
			<div class="p-4 rounded-full bg-gray-50 dark:bg-gray-800">
				<Plus className="size-8" />
			</div>
			<div class="mt-2 font-medium">
				{$i18n.t('Add a knowledge base')}
			</div>
		</a>

		{#each filteredItems as item}
			<div
				class="flex flex-col cursor-pointer w-full px-3 py-3 dark:hover:bg-white/5 hover:bg-black/5 rounded-xl transition border border-gray-100 dark:border-gray-800 min-h-[200px]"
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
				<div class="flex flex-col flex-1">
					<div class="flex items-center justify-between -mt-1">
						{#if item?.meta?.document}
							<Badge type="muted" content={$i18n.t('Document')} />
						{:else}
							<Badge type="success" content={$i18n.t('Collection')} />
						{/if}

						<div class="flex self-center -mr-1 translate-y-1">
							<ItemMenu
								on:delete={() => {
									selectedItem = item;
									showDeleteConfirm = true;
								}}
							/>
						</div>
					</div>

					<div class="flex-1 px-1 mb-1 text-center">
						<div class="font-semibold line-clamp-1 h-fit">{item.name}</div>

						<div class="text-xs overflow-hidden text-ellipsis line-clamp-1">
							{item.description}
						</div>
					</div>

					<div class="mt-auto">
						<div class="flex justify-between">
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
							<div class="text-xs text-gray-500 line-clamp-1">
								{$i18n.t('Updated')}
								{dayjs(item.updated_at * 1000).fromNow()}
							</div>
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
