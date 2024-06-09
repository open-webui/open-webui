<script lang="ts">
	import { getContext } from 'svelte';

	export let knowledge = [];

	const i18n = getContext('i18n');
</script>

<div>
	<div class="flex w-full justify-between mb-1">
		<div class=" self-center text-sm font-semibold">{$i18n.t('Knowledge')}</div>
	</div>

	<div class=" text-xs dark:text-gray-500">
		To add documents here, upload them to the "Documents" workspace first.
	</div>

	<div class="flex flex-col">
		{#if knowledge.length > 0}
			{#each knowledge as doc}
				<div class=" flex items-center gap-2">
					<div class=" py-0.5 text-sm w-full">{doc.name}</div>
				</div>
			{/each}
		{/if}

		<div class="flex flex-wrap text-sm font-medium gap-1.5 mt-2">
			<button
				class=" px-3.5 py-1.5 font-medium hover:bg-black/5 dark:hover:bg-white/5 outline outline-1 outline-gray-300 dark:outline-gray-800 rounded-3xl"
				type="button"
				on:click={() => {
					console.log('hi');
				}}>Select Documents</button
			>
		</div>
		<!-- {knowledge} -->
	</div>
</div>
