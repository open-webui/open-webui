<script lang="ts">
	import { toast } from 'svelte-sonner';
	import Fuse from 'fuse.js';

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { tick, getContext, onMount, onDestroy } from 'svelte';
	import { removeLastWordFromString, isValidHttpUrl, isYoutubeUrl } from '$lib/utils';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import DocumentPage from '$lib/components/icons/DocumentPage.svelte';
	import Database from '$lib/components/icons/Database.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import Youtube from '$lib/components/icons/Youtube.svelte';
	import { folders } from '$lib/stores';
	import Folder from '$lib/components/icons/Folder.svelte';

	const i18n = getContext('i18n');

	export let query = '';
	export let onSelect = (e) => {};

	export let knowledge = [];

	let selectedIdx = 0;

	let items = [];
	let fuse = null;

	export let filteredItems = [];
	$: if (fuse) {
		filteredItems = [
			...(query
				? fuse.search(query).map((e) => {
						return e.item;
					})
				: items),

			...(query.startsWith('http')
				? isYoutubeUrl(query)
					? [{ type: 'youtube', name: query, description: query }]
					: [
							{
								type: 'web',
								name: query,
								description: query
							}
						]
				: [])
		];
	}

	$: if (query) {
		selectedIdx = 0;
	}

	export const selectUp = () => {
		selectedIdx = Math.max(0, selectedIdx - 1);
	};

	export const selectDown = () => {
		selectedIdx = Math.min(selectedIdx + 1, filteredItems.length - 1);
	};

	export const select = async () => {
		// find item with data-selected=true
		const item = document.querySelector(`[data-selected="true"]`);
		if (item) {
			// click the item
			item.click();
		}
	};
	const decodeString = (str: string) => {
		try {
			return decodeURIComponent(str);
		} catch (e) {
			return str;
		}
	};

	onMount(async () => {
		let legacy_documents = knowledge
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

		let collections = knowledge
			.filter((item) => !item?.meta?.document)
			.map((item) => ({
				...item,
				type: 'collection'
			}));
		let collection_files =
			knowledge.length > 0
				? [
						...knowledge
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

		let folder_items = $folders.map((folder) => ({
			...folder,
			type: 'folder',
			description: $i18n.t('Folder'),
			title: folder.name
		}));

		items = [
			...folder_items,
			...collections,
			...collection_files,
			...legacy_collections,
			...legacy_documents
		].map((item) => {
			return {
				...item,
				...(item?.legacy || item?.meta?.legacy || item?.meta?.document ? { legacy: true } : {})
			};
		});

		fuse = new Fuse(items, {
			keys: ['name', 'description']
		});

		await tick();
	});

	const onKeyDown = (e) => {
		if (e.key === 'Enter') {
			e.preventDefault();
			select();
		}
	};
	onMount(() => {
		window.addEventListener('keydown', onKeyDown);
	});

	onDestroy(() => {
		window.removeEventListener('keydown', onKeyDown);
	});
</script>

<div class="px-2 text-xs text-gray-500 py-1">
	{$i18n.t('Knowledge')}
</div>

{#if filteredItems.length > 0 || query.startsWith('http')}
	{#each filteredItems as item, idx}
		{#if !['youtube', 'web'].includes(item.type)}
			<button
				class=" px-2 py-1 rounded-xl w-full text-left flex justify-between items-center {idx ===
				selectedIdx
					? ' bg-gray-50 dark:bg-gray-800 dark:text-gray-100 selected-command-option-button'
					: ''}"
				type="button"
				on:click={() => {
					console.log(item);
					onSelect({
						type: 'knowledge',
						data: item
					});
				}}
				on:mousemove={() => {
					selectedIdx = idx;
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
						{:else if item?.type === 'folder'}
							<Folder className="size-4" />
						{:else}
							<DocumentPage className="size-4" />
						{/if}
					</Tooltip>

					<Tooltip content={`${decodeString(item?.name)}`} placement="top-start">
						<div class="line-clamp-1 flex-1">
							{decodeString(item?.name)}
						</div>
					</Tooltip>
				</div>
			</button>
		{/if}
	{/each}

	{#if isYoutubeUrl(query)}
		<button
			class="px-2 py-1 rounded-xl w-full text-left bg-gray-50 dark:bg-gray-800 dark:text-gray-100 selected-command-option-button"
			type="button"
			data-selected={true}
			on:click={() => {
				if (isValidHttpUrl(query)) {
					onSelect({
						type: 'youtube',
						data: query
					});
				} else {
					toast.error(
						$i18n.t('Oops! Looks like the URL is invalid. Please double-check and try again.')
					);
				}
			}}
		>
			<div class="  text-black dark:text-gray-100 line-clamp-1 flex items-center gap-1">
				<Tooltip content={$i18n.t('YouTube')} placement="top">
					<Youtube className="size-4" />
				</Tooltip>

				<div class="truncate flex-1">
					{query}
				</div>
			</div>
		</button>
	{:else if query.startsWith('http')}
		<button
			class="px-2 py-1 rounded-xl w-full text-left bg-gray-50 dark:bg-gray-800 dark:text-gray-100 selected-command-option-button"
			type="button"
			data-selected={true}
			on:click={() => {
				if (isValidHttpUrl(query)) {
					onSelect({
						type: 'web',
						data: query
					});
				} else {
					toast.error(
						$i18n.t('Oops! Looks like the URL is invalid. Please double-check and try again.')
					);
				}
			}}
		>
			<div class="  text-black dark:text-gray-100 line-clamp-1 flex items-center gap-1">
				<Tooltip content={$i18n.t('Web')} placement="top">
					<GlobeAlt className="size-4" />
				</Tooltip>

				<div class="truncate flex-1">
					{query}
				</div>
			</div>
		</button>
	{/if}
{/if}
