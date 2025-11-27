<script lang="ts">
	import Fuse from 'fuse.js';

	import { DropdownMenu } from 'bits-ui';
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	import { flyAndScale } from '$lib/utils/transitions';
	import { knowledge } from '$lib/stores';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import { getNoteList } from '$lib/apis/notes';
	import dayjs from 'dayjs';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let onClose: Function = () => {};

	export let knowledgeItems = [];

	let query = '';

	let items = [];
	let filteredItems = [];

	let fuse = null;
	$: if (fuse) {
		filteredItems = query
			? fuse.search(query).map((e) => {
					return e.item;
				})
			: items;
	}

	const decodeString = (str: string) => {
		try {
			return decodeURIComponent(str);
		} catch (e) {
			return str;
		}
	};

	onMount(async () => {
		let notes = await getNoteList(localStorage.token).catch(() => {
			return [];
		});

		notes = notes.map((note) => {
			return {
				...note,
				type: 'note',
				name: note.title,
				description: dayjs(note.updated_at / 1000000).fromNow()
			};
		});

		let legacy_documents = knowledgeItems
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

		let collections = knowledgeItems
			.filter((item) => !item?.meta?.document)
			.map((item) => ({
				...item,
				type: 'collection'
			}));
		let collection_files =
			knowledgeItems.length > 0
				? [
						...knowledgeItems
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
								type: 'file'
							}))
					]
				: [];

		items = [...notes, ...collections, ...legacy_collections].map((item) => {
			return {
				...item,
				...(item?.legacy || item?.meta?.legacy || item?.meta?.document ? { legacy: true } : {})
			};
		});

		fuse = new Fuse(items, {
			keys: ['name', 'description']
		});
	});
</script>

<Dropdown
	on:change={(e) => {
		if (e.detail === false) {
			onClose();
			query = '';
		}
	}}
>
	<slot />

	<div slot="content">
		<DropdownMenu.Content
			class="w-full max-w-96 rounded-xl p-1 border border-gray-100  dark:border-gray-800 z-[99999999] bg-white dark:bg-gray-850 dark:text-white shadow-lg"
			sideOffset={8}
			side="bottom"
			align="start"
			transition={flyAndScale}
		>
			<div class=" flex w-full space-x-2 py-0.5 px-2 pb-2">
				<div class="flex flex-1">
					<div class=" self-center ml-1 mr-3">
						<Search />
					</div>
					<input
						class=" w-full text-sm pr-4 py-1 rounded-r-xl outline-hidden bg-transparent"
						bind:value={query}
						placeholder={$i18n.t('Search Knowledge')}
					/>
				</div>
			</div>

			<div class="max-h-56 overflow-y-scroll">
				{#if filteredItems.length === 0}
					<div class="text-center text-xs text-gray-500 dark:text-gray-400 py-4">
						{$i18n.t('No knowledge found')}
					</div>
				{:else}
					{#each filteredItems as item}
						<DropdownMenu.Item
							class="flex gap-2.5 items-center px-3 py-2 text-sm  cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
							on:click={() => {
								dispatch('select', item);
							}}
						>
							<div>
								<div class=" font-medium text-black dark:text-gray-100 flex items-center gap-1">
									{#if item.legacy}
										<div
											class="bg-gray-500/20 text-gray-700 dark:text-gray-200 rounded-sm uppercase text-xs font-semibold px-1 shrink-0"
										>
											Legacy
										</div>
									{:else if item?.meta?.document}
										<div
											class="bg-gray-500/20 text-gray-700 dark:text-gray-200 rounded-sm uppercase text-xs font-semibold px-1 shrink-0"
										>
											Document
										</div>
									{:else if item?.type === 'file'}
										<div
											class="bg-gray-500/20 text-gray-700 dark:text-gray-200 rounded-sm uppercase text-xs font-semibold px-1 shrink-0"
										>
											File
										</div>
									{:else if item?.type === 'note'}
										<div
											class="bg-blue-500/20 text-blue-700 dark:text-blue-200 rounded-sm uppercase text-xs font-semibold px-1 shrink-0"
										>
											Note
										</div>
									{:else}
										<div
											class="bg-green-500/20 text-green-700 dark:text-green-200 rounded-sm uppercase text-xs font-semibold px-1 shrink-0"
										>
											Collection
										</div>
									{/if}

									<div class="line-clamp-1">
										{decodeString(item?.name)}
									</div>
								</div>

								<div class=" text-xs text-gray-600 dark:text-gray-100 line-clamp-1">
									{item?.description}
								</div>
							</div>
						</DropdownMenu.Item>
					{/each}
				{/if}
			</div>
		</DropdownMenu.Content>
	</div>
</Dropdown>
