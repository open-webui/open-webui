<script lang="ts">
	import { onMount, tick, getContext } from 'svelte';

	import { decodeString } from '$lib/utils';
	import { knowledge } from '$lib/stores';

	import { getKnowledgeBases } from '$lib/apis/knowledge';

	import Fuse from 'fuse.js';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Database from '$lib/components/icons/Database.svelte';
	import DocumentPage from '$lib/components/icons/DocumentPage.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');

	export let onSelect = (e) => {};

	let loaded = false;
	let items = [];
	let selectedIdx = 0;
	let query = '';

	onMount(async () => {
		if ($knowledge === null) {
			await knowledge.set(await getKnowledgeBases(localStorage.token));
		}

		let legacy_documents = $knowledge
			.filter((item) => item?.meta?.document)
			.map((item) => ({
				...item,
				type: 'file'
			}));

		let legacy_collections =
			legacy_documents.length > 0
				? [
						{
							name: 'All Documents',
							legacy: true,
							type: 'collection',
							description: 'Deprecated (legacy collection), please create a new knowledge base.',
							title: $i18n.t('All Documents'),
							collection_names: legacy_documents.map((item) => item.id)
						},

						...legacy_documents
							.reduce((a, item) => {
								return [...new Set([...a, ...(item?.meta?.tags ?? []).map((tag) => tag.name)])];
							}, [])
							.map((tag) => ({
								name: tag,
								legacy: true,
								type: 'collection',
								description: 'Deprecated (legacy collection), please create a new knowledge base.',
								collection_names: legacy_documents
									.filter((item) => (item?.meta?.tags ?? []).map((tag) => tag.name).includes(tag))
									.map((item) => item.id)
							}))
					]
				: [];

		let collections = $knowledge
			.filter((item) => !item?.meta?.document)
			.map((item) => ({
				...item,
				type: 'collection'
			}));
		``;
		let collection_files =
			$knowledge.length > 0
				? [
						...$knowledge
							.reduce((a, item) => {
								return [
									...new Set([
										...a,
										...(item?.files ?? []).map((file) => ({
											...file,
											collection: { name: item.name, description: item.description } // DO NOT REMOVE, USED IN FILE DESCRIPTION/ATTACHMENT
										}))
									])
								];
							}, [])
							.map((file) => ({
								...file,
								name: file?.meta?.name,
								description: `${file?.collection?.name} - ${file?.collection?.description}`,
								knowledge: true, // DO NOT REMOVE, USED TO INDICATE KNOWLEDGE BASE FILE
								type: 'file'
							}))
					]
				: [];

		items = [...collections, ...collection_files, ...legacy_collections, ...legacy_documents].map(
			(item) => {
				return {
					...item,
					...(item?.legacy || item?.meta?.legacy || item?.meta?.document ? { legacy: true } : {})
				};
			}
		);

		await tick();

		loaded = true;
	});
	let fuse;
	$: {
		if (items) {
			fuse = new Fuse(items, {
				keys: ['name']
			});
		}
	}

	$: filteredItems = query ? fuse.search(query).map((e) => e.item) : items;
</script>

<div class="px-1 mb-1 flex justify-center space-x-2 relative z-10" id="search-container">
	<div class="flex w-full rounded-xl items-center" id="chat-search">
		<div class="pl-2 pr-1.5">
			<Search />
		</div>
		<input
			class="w-full py-2 pl-1 text-sm bg-transparent dark:text-gray-300 outline-none"
			placeholder={$i18n.t('Search...')}
			autocomplete="off"
			bind:value={query}
		/>
		{#if query}
			<div class="self-center pl-1.5 pr-1.5 rounded-l-xl bg-transparent">
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

{#if loaded}
	{#if filteredItems.length === 0}
		<div class="text-center text-xs text-gray-500 py-3">{$i18n.t('No knowledge found')}</div>
	{:else}
		<div class="flex flex-col gap-0.5">
			{#each filteredItems as item, idx}
				<button
					class=" px-2.5 py-1 rounded-xl w-full text-left flex justify-between items-center text-sm {idx ===
					selectedIdx
						? ' bg-gray-50 dark:bg-gray-800 dark:text-gray-100 selected-command-option-button'
						: ''}"
					type="button"
					on:click={() => {
						console.log(item);
						onSelect(item);
					}}
					on:mousemove={() => {
						selectedIdx = idx;
					}}
					on:mouseleave={() => {
						if (idx === 0) {
							selectedIdx = -1;
						}
					}}
					data-selected={idx === selectedIdx}
				>
					<div class="  text-black dark:text-gray-100 flex items-center gap-1">
						<Tooltip
							content={item?.legacy
								? $i18n.t('Legacy')
								: item?.type === 'file'
									? $i18n.t('File')
									: item?.type === 'collection'
										? $i18n.t('Collection')
										: ''}
							placement="top"
						>
							{#if item?.type === 'collection'}
								<Database className="size-4" />
							{:else}
								<DocumentPage className="size-4" />
							{/if}
						</Tooltip>

						<Tooltip content={item.description || decodeString(item?.name)} placement="top-start">
							<div class="line-clamp-1 flex-1">
								{decodeString(item?.name)}
							</div>
						</Tooltip>
					</div>
				</button>
			{/each}
		</div>
	{/if}
{:else}
	<div class="py-4.5">
		<Spinner />
	</div>
{/if}
