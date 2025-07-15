<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { knowledge } from '$lib/stores';

	import Selector from './Knowledge/Selector.svelte';
	import FileItem from '$lib/components/common/FileItem.svelte';
	import { getKnowledgeBases } from '$lib/apis/knowledge';

	export let selectedItems = [];
	const i18n = getContext('i18n');

	let loaded = false;

	onMount(async () => {
		if (!$knowledge) {
			knowledge.set(await getKnowledgeBases(localStorage.token));
		}
		loaded = true;
	});
</script>

<div>
	<slot name="label">
		<div class="mb-2">
			<div class="flex w-full justify-between mb-1">
				<div class=" self-center text-sm font-semibold">
					{$i18n.t('Knowledge')}
				</div>
			</div>

			<div class=" text-xs dark:text-gray-500">
				{$i18n.t('To attach knowledge base here, add them to the "Knowledge" workspace first.')}
			</div>
		</div>
	</slot>

	<div class="flex flex-col">
		{#if selectedItems?.length > 0}
			<div class=" flex flex-wrap items-center gap-2 mb-2.5">
				{#each selectedItems as file, fileIdx}
					<FileItem
						{file}
						item={file}
						name={file.name}
						modal={true}
						edit={true}
						type={file?.legacy
							? `Legacy${file.type ? ` ${file.type}` : ''}`
							: (file?.type ?? 'Collection')}
						dismissible
						on:dismiss={(e) => {
							selectedItems = selectedItems.filter((_, idx) => idx !== fileIdx);
						}}
					/>
				{/each}
			</div>
		{/if}

		{#if loaded}
			<div class="flex flex-wrap text-sm font-medium gap-1.5">
				<Selector
					knowledgeItems={$knowledge || []}
					on:select={(e) => {
						const item = e.detail;

						if (!selectedItems.find((k) => k.id === item.id)) {
							selectedItems = [
								...selectedItems,
								{
									...item
								}
							];
						}
					}}
				>
					<button
						class=" px-3.5 py-1.5 font-medium hover:bg-black/5 dark:hover:bg-white/5 outline outline-1 outline-gray-100 dark:outline-gray-850 rounded-3xl"
						type="button">{$i18n.t('Select Knowledge')}</button
					>
				</Selector>
			</div>
		{/if}
		<!-- {knowledge} -->
	</div>
</div>
