<script lang="ts">
	import { onMount, tick, getContext } from 'svelte';

	import { decodeString } from '$lib/utils';
	import { knowledge } from '$lib/stores';

	import { getKnowledgeBases } from '$lib/apis/knowledge';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Database from '$lib/components/icons/Database.svelte';
	import DocumentPage from '$lib/components/icons/DocumentPage.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	export let onSelect = (e) => {};

	let loaded = false;
	let items = [];
	let selectedIdx = 0;

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
</script>

{#if loaded}
	<div class="flex flex-col gap-0.5">
		{#each items as item, idx}
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
{:else}
	<div class="py-4.5">
		<Spinner />
	</div>
{/if}
