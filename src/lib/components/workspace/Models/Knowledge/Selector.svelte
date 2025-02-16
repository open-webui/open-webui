<script lang="ts">
	import Fuse from 'fuse.js';

	import { DropdownMenu } from 'bits-ui';
	import { onMount, getContext, createEventDispatcher } from 'svelte';
	import { flyAndScale } from '$lib/utils/transitions';
	import { knowledge } from '$lib/stores';
	import Dropdown from '$lib/components/common/Dropdown.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let onClose: Function = () => {};

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

	onMount(() => {
		let legacy_documents = $knowledge.filter((item) => item?.meta?.document);
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

		items = [...$knowledge, ...legacy_collections].map((item) => {
			return {
				...item,
				...(item?.legacy || item?.meta?.legacy || item?.meta?.document ? { legacy: true } : {}),
				type: item?.meta?.document ? 'document' : 'collection'
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
			class="w-full max-w-80 rounded-lg px-1 py-1.5 border border-gray-300/30 dark:border-gray-700/50 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg"
			sideOffset={8}
			side="bottom"
			align="start"
			transition={flyAndScale}
		>
			<div class=" flex w-full space-x-2 py-0.5 px-2">
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
						class=" w-full text-sm pr-4 py-1 rounded-r-xl outline-hidden bg-transparent"
						bind:value={query}
						placeholder={$i18n.t('Search Knowledge')}
					/>
				</div>
			</div>

			<hr class=" border-gray-50 dark:border-gray-700 my-1.5" />

			<div class="max-h-48 overflow-y-scroll">
				{#if filteredItems.length === 0}
					<div class="text-center text-sm text-gray-500 dark:text-gray-400">
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
							<div class="flex items-center">
								<div class="flex flex-col">
									<div class=" w-fit mb-0.5">
										{#if item.legacy}
											<div
												class="bg-gray-500/20 text-gray-700 dark:text-gray-200 rounded-sm uppercase text-xs font-bold px-1"
											>
												Legacy
											</div>
										{:else if item?.meta?.document}
											<div
												class="bg-gray-500/20 text-gray-700 dark:text-gray-200 rounded-sm uppercase text-xs font-bold px-1"
											>
												Document
											</div>
										{:else}
											<div
												class="bg-green-500/20 text-green-700 dark:text-green-200 rounded-sm uppercase text-xs font-bold px-1"
											>
												Collection
											</div>
										{/if}
									</div>

									<div class="line-clamp-1 font-medium pr-0.5">
										{item.name}
									</div>
								</div>
							</div>
						</DropdownMenu.Item>
					{/each}
				{/if}
			</div>
		</DropdownMenu.Content>
	</div>
</Dropdown>
