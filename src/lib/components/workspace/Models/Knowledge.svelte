<script lang="ts">
	import { getContext } from 'svelte';
	import Selector from './Knowledge/Selector.svelte';
	import FileItem from '$lib/components/common/FileItem.svelte';

	export let knowledge = [];
	const i18n = getContext('i18n');
</script>

<div>
	<div class="flex w-full justify-between mb-1">
		<div class=" self-center text-sm font-semibold">{$i18n.t('Knowledge')}</div>
	</div>

	<div class=" text-xs dark:text-gray-500">
		{$i18n.t('To attach knowledge base here, add them to the "Knowledge" workspace first.')}
	</div>

	<div class="flex flex-col">
		{#if knowledge?.length > 0}
			<div class=" flex items-center gap-2 mt-2">
				{#each knowledge as file, fileIdx}
					<FileItem
						{file}
						dismissible
						on:dismiss={(e) => {
							knowledge = knowledge.filter((_, idx) => idx !== fileIdx);
						}}
					/>
				{/each}
			</div>
		{/if}

		<div class="flex flex-wrap text-sm font-medium gap-1.5 mt-2">
			<Selector
				bind:knowledge
				on:select={(e) => {
					const item = e.detail;

					if (!knowledge.find((k) => k.name === item.name)) {
						knowledge = [
							...knowledge,
							{
								...item,
								type: item?.type ?? 'doc'
							}
						];
					}
				}}
			>
				<button
					class=" px-3.5 py-1.5 font-medium hover:bg-black/5 dark:hover:bg-white/5 outline outline-1 outline-gray-300 dark:outline-gray-800 rounded-3xl"
					type="button">{$i18n.t('Select Knowledge')}</button
				>
			</Selector>
		</div>
		<!-- {knowledge} -->
	</div>
</div>
