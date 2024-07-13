<script lang="ts">
	import { getDocs } from '$lib/apis/documents';
	import {
		getRAGConfig,
		updateRAGConfig,
		getQuerySettings,
		scanDocs,
		updateQuerySettings,
		resetVectorDB,
		getEmbeddingConfig,
		updateEmbeddingConfig,
		getRerankingConfig,
		updateRerankingConfig
	} from '$lib/apis/rag';

	import { documents, models } from '$lib/stores';
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	let querySettings = {
		template: '',
		r: 0.0,
		k: 4,
		hybrid: false
	};

	const submitHandler = async () => {
		querySettings = await updateQuerySettings(localStorage.token, querySettings);
	};

	onMount(async () => {
		querySettings = await getQuerySettings(localStorage.token);
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={() => {
		submitHandler();
		saveHandler();
	}}
>
	<div class=" space-y-3 pr-1.5 overflow-y-scroll max-h-[25rem]">
		<div class=" ">
			<div class=" text-sm font-medium">{$i18n.t('Query Params')}</div>

			<div class=" flex">
				<div class="  flex w-full justify-between">
					<div class="self-center text-xs font-medium min-w-fit">{$i18n.t('Top K')}</div>

					<div class="self-center p-3">
						<input
							class=" w-full rounded-lg py-1.5 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
							type="number"
							placeholder={$i18n.t('Enter Top K')}
							bind:value={querySettings.k}
							autocomplete="off"
							min="0"
						/>
					</div>
				</div>

				{#if querySettings.hybrid === true}
					<div class="flex w-full">
						<div class=" self-center text-xs font-medium min-w-fit">
							{$i18n.t('Minimum Score')}
						</div>

						<div class="self-center p-3">
							<input
								class=" w-full rounded-lg py-1.5 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
								type="number"
								step="0.01"
								placeholder={$i18n.t('Enter Score')}
								bind:value={querySettings.r}
								autocomplete="off"
								min="0.0"
								title={$i18n.t('The score should be a value between 0.0 (0%) and 1.0 (100%).')}
							/>
						</div>
					</div>
				{/if}
			</div>

			{#if querySettings.hybrid === true}
				<div class="mt-2 mb-1 text-xs text-gray-400 dark:text-gray-500">
					{$i18n.t(
						'Note: If you set a minimum score, the search will only return documents with a score greater than or equal to the minimum score.'
					)}
				</div>

				<hr class=" dark:border-gray-850 my-3" />
			{/if}

			<div>
				<div class=" mb-2.5 text-sm font-medium">{$i18n.t('RAG Template')}</div>
				<textarea
					bind:value={querySettings.template}
					class="w-full rounded-lg px-4 py-3 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none resize-none"
					rows="4"
				/>
			</div>
		</div>
	</div>
	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
