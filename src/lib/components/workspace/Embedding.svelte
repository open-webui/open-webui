<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import {chats, selectedIndexId, WEBUI_NAME} from '$lib/stores';

	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import CreateIndexModal from '$lib/components/embedding/CreateIndexModal.svelte';
	import {getEmbeddingIndex} from "$lib/apis/embedding";
	import {goto} from "$app/navigation";
	import TagList from "$lib/components/common/Tags/TagList.svelte";
	import {getChatList} from "$lib/apis/chats";

	const i18n = getContext('i18n');

	let query = '';

	let showCreateIndexModal = false;

	let listIndex = []

	// $: filteredIndexs = listIndex.filter(
	// 		(doc) =>
	// 				(selectedTag === '' ||
	// 						(doc?.content?.tags ?? []).map((tag) => tag.name).includes(selectedTag)) &&
	// 				(query === '' || doc.name.includes(query))
	// );

	onMount(async () => {
		listIndex = await getEmbeddingIndex()
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Embedding')} | {$WEBUI_NAME}
	</title>
</svelte:head>

<CreateIndexModal bind:show={showCreateIndexModal} onClose={(index) => {
	listIndex = [index, ...listIndex]
	console.log(listIndex)
}} />

<div class="mb-3">
	<div class="flex justify-between items-center">
		<div class=" text-lg font-semibold self-center">{$i18n.t('Embedding Index')}</div>

		<div>
			<button
				class="flex items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 transition"
				type="button"
				on:click={() => {
					showCreateIndexModal = !showCreateIndexModal;
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

				<div class=" text-xs">{$i18n.t('Create new index')}</div>
			</button>
		</div>
	</div>
</div>

<div class=" flex w-full space-x-2">
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
			placeholder={$i18n.t('Search Documents')}
		/>
	</div>
</div>

<!-- <div>
    <div
        class="my-3 py-16 rounded-lg border-2 border-dashed dark:border-gray-600 {dragged &&
            ' dark:bg-gray-700'} "
        role="region"
        on:drop={onDrop}
        on:dragover={onDragOver}
        on:dragleave={onDragLeave}
    >
        <div class="  pointer-events-none">
            <div class="text-center dark:text-white text-2xl font-semibold z-50">{$i18n.t('Add Files')}</div>

            <div class=" mt-2 text-center text-sm dark:text-gray-200 w-full">
                Drop any files here to add to my documents
            </div>
        </div>
    </div>
</div> -->

<hr class=" dark:border-gray-850 my-2.5" />

<div class="my-3 mb-5">
	{#each listIndex as embeddingIndex}
		<button
			class=" flex space-x-4 cursor-pointer text-left w-full px-3 py-2 dark:hover:bg-white/5 hover:bg-black/5 rounded-xl"
			on:click={() => {
				selectedIndexId.set(embeddingIndex.id)
				goto(`/embedding/detail?id=${embeddingIndex.id}`);
			}}
		>
<!--			<div class="my-auto flex items-center">-->
<!--				<Checkbox state={embeddingIndex?.selected ?? 'unchecked'} />-->
<!--			</div>-->
			<div class=" flex flex-1 space-x-4 cursor-pointer w-full">
				<div class=" flex items-center space-x-3">
					<div class=" self-center flex-1">
						<div class="font-bold line-clamp-1">{embeddingIndex.name}<span class="text-xs ml-4 font-light">({embeddingIndex.num_docs} {$i18n.t('Documents')})</span></div>
						<div class="mt-1 text-xs overflow-hidden text-ellipsis line-clamp-1">
							Phân loại: {embeddingIndex.category}
						</div>
						<div class="mt-1 text-xs overflow-hidden text-ellipsis line-clamp-1">
							{embeddingIndex.geographic}
						</div>
					</div>
				</div>
			</div>
			<div class="flex flex-row space-x-1 self-center">
				<button
					class="self-center w-fit text-sm z-20 px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
					type="button"
					on:click={async (e) => {
						e.stopPropagation();
					}}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						stroke-width="1.5"
						stroke="currentColor"
						class="w-4 h-4"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487zm0 0L19.5 7.125"
						/>
					</svg>
				</button>

				<!-- <button
            class="self-center w-fit text-sm px-2 py-2 border dark:border-gray-600 rounded-xl"
            type="button"
            on:click={() => {
                console.log('download file');
            }}
        >
            <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 16 16"
                fill="currentColor"
                class="w-4 h-4"
            >
                <path
                    d="M8.75 2.75a.75.75 0 0 0-1.5 0v5.69L5.03 6.22a.75.75 0 0 0-1.06 1.06l3.5 3.5a.75.75 0 0 0 1.06 0l3.5-3.5a.75.75 0 0 0-1.06-1.06L8.75 8.44V2.75Z"
                />
                <path
                    d="M3.5 9.75a.75.75 0 0 0-1.5 0v1.5A2.75 2.75 0 0 0 4.75 14h6.5A2.75 2.75 0 0 0 14 11.25v-1.5a.75.75 0 0 0-1.5 0v1.5c0 .69-.56 1.25-1.25 1.25h-6.5c-.69 0-1.25-.56-1.25-1.25v-1.5Z"
                />
            </svg>
        </button> -->

<!--				<button-->
<!--					class="self-center w-fit text-sm px-2 py-2 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"-->
<!--					type="button"-->
<!--					on:click={(e) => {-->
<!--						e.stopPropagation();-->
<!--					}}-->
<!--				>-->
<!--					<svg-->
<!--						xmlns="http://www.w3.org/2000/svg"-->
<!--						fill="none"-->
<!--						viewBox="0 0 24 24"-->
<!--						stroke-width="1.5"-->
<!--						stroke="currentColor"-->
<!--						class="w-4 h-4"-->
<!--					>-->
<!--						<path-->
<!--							stroke-linecap="round"-->
<!--							stroke-linejoin="round"-->
<!--							d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"-->
<!--						/>-->
<!--					</svg>-->
<!--				</button>-->
			</div>
		</button>
	{/each}
</div>
