<script lang="ts">
	import Fuse from 'fuse.js';

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { WEBUI_NAME, knowledge } from '$lib/stores';

	import { getKnowledgeItems, deleteKnowledgeById } from '$lib/apis/knowledge';

	import { blobToFile, transformFileName } from '$lib/utils';

	import { goto } from '$app/navigation';
	import Tooltip from '../common/Tooltip.svelte';
	import GarbageBin from '../icons/GarbageBin.svelte';
	import Pencil from '../icons/Pencil.svelte';
	import DeleteConfirmDialog from '../common/ConfirmDialog.svelte';
	import ItemMenu from './Knowledge/ItemMenu.svelte';
	import Badge from '../common/Badge.svelte';

	let query = '';
	let selectedItem = null;
	let showDeleteConfirm = false;

	let fuse = null;

	let filteredItems = [];
	$: if (fuse) {
		filteredItems = query
			? fuse.search(query).map((e) => {
					return e.item;
				})
			: $knowledge;
	}

	const deleteHandler = async (item) => {
		const res = await deleteKnowledgeById(localStorage.token, item.id).catch((e) => {
			toast.error(e);
		});

		if (res) {
			knowledge.set(await getKnowledgeItems(localStorage.token));
			toast.success($i18n.t('Knowledge deleted successfully.'));
		}
	};

	onMount(async () => {
		knowledge.set(await getKnowledgeItems(localStorage.token));

		knowledge.subscribe((value) => {
			fuse = new Fuse(value, {
				keys: ['name', 'description']
			});
		});
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Knowledge')} | {$WEBUI_NAME}
	</title>
</svelte:head>

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	on:confirm={() => {
		deleteHandler(selectedItem);
	}}
/>

<div class=" flex w-full space-x-2 mb-2.5">
	<div class="flex flex-1">
		<div class=" self-center ml-1 mr-3">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="w-4 h-4"
			>
				<path
					fill-rule="evenodd"
					d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
					clip-rule="evenodd"
				/>
			</svg>
		</div>
		<input
			class=" w-full text-sm pr-4 py-1 rounded-r-xl outline-none bg-transparent"
			bind:value={query}
			placeholder={$i18n.t('Search Knowledge')}
		/>
	</div>

	<div>
		<button
			class=" px-2 py-2 rounded-xl border border-gray-50 dark:border-gray-800 dark:border-0 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 transition font-medium text-sm flex items-center space-x-1"
			aria-label={$i18n.t('Create Knowledge')}
			on:click={() => {
				goto('/workspace/knowledge/create');
			}}
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 16 16"
				fill="currentColor"
				class="w-4 h-4"
			>
				<path
					d="M8.75 3.75a.75.75 0 0 0-1.5 0v3.5h-3.5a.75.75 0 0 0 0 1.5h3.5v3.5a.75.75 0 0 0 1.5 0v-3.5h3.5a.75.75 0 0 0 0-1.5h-3.5v-3.5Z"
				/>
			</svg>
		</button>
	</div>
</div>

<div class="mb-3.5">
	<div class="flex justify-between items-center">
		<div class="flex md:self-center text-base font-medium px-0.5">
			{$i18n.t('Knowledge')}
			<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />
			<span class="text-base font-medium text-gray-500 dark:text-gray-300"
				>{filteredItems.length}</span
			>
		</div>
	</div>
</div>

<div class="my-3 mb-5 grid md:grid-cols-2 lg:grid-cols-3 gap-2">
	{#each filteredItems as item}
		<button
			class=" flex space-x-4 cursor-pointer text-left w-full px-4 py-3 border border-gray-50 dark:border-gray-850 dark:hover:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-850 transition rounded-xl"
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
				<div class="flex items-center justify-between -mt-1">
					<div class=" font-semibold line-clamp-1 h-fit">{item.name}</div>

					<div class=" flex self-center">
						<ItemMenu
							on:delete={() => {
								selectedItem = item;
								showDeleteConfirm = true;
							}}
						/>
					</div>
				</div>

				<div class=" self-center flex-1">
					<div class=" text-xs overflow-hidden text-ellipsis line-clamp-1">
						{item.description}
					</div>

					<div class="mt-5 flex justify-between">
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
				</div>
			</div>
		</button>
	{/each}
</div>

<div class=" text-gray-500 text-xs mt-1 mb-2">
	ⓘ {$i18n.t("Use '#' in the prompt input to load and include your knowledge.")}
</div>
