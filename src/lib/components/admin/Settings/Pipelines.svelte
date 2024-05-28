<script lang="ts">
	import { v4 as uuidv4 } from 'uuid';

	import { getContext, onMount } from 'svelte';

	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { stringify } from 'postcss';
	import { getPipelineValves, getPipelines } from '$lib/apis';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n: Writable<i18nType> = getContext('i18n');

	export let saveHandler: Function;

	let pipelines = null;
	let valves = null;

	let selectedPipelineIdx = 0;

	$: if (
		pipelines !== null &&
		pipelines.length > 0 &&
		pipelines[selectedPipelineIdx] !== undefined &&
		pipelines[selectedPipelineIdx].pipeline.valves
	) {
		(async () => {
			valves = await getPipelineValves(localStorage.token, pipelines[selectedPipelineIdx].id);
		})();
	}

	onMount(async () => {
		pipelines = await getPipelines(localStorage.token);
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={async () => {
		saveHandler();
	}}
>
	<div class=" space-y-2 pr-1.5 overflow-y-scroll max-h-80 h-full">
		{#if pipelines !== null && pipelines.length > 0}
			<div class="flex w-full justify-between mb-2">
				<div class=" self-center text-sm font-semibold">
					{$i18n.t('Pipelines')}
				</div>
			</div>
			<div class="space-y-2">
				{#if pipelines.length > 0}
					<div class="flex gap-2">
						<div class="flex-1 pb-1">
							<select
								class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
								bind:value={selectedPipelineIdx}
								placeholder={$i18n.t('Select an Ollama instance')}
							>
								{#each pipelines as pipeline, idx}
									<option value={idx} class="bg-gray-100 dark:bg-gray-700">{pipeline.name}</option>
								{/each}
							</select>
						</div>
					</div>
				{/if}

				<div class="text-sm font-medium">{$i18n.t('Valves')}</div>

				<div class="space-y-2">
					{#if pipelines[selectedPipelineIdx].pipeline.valves}
						{#if valves}
							{#each Object.keys(valves) as valve, idx}
								<div>{valve}</div>
							{/each}
						{:else}
							<Spinner className="size-5" />
						{/if}
					{:else}
						<div>No valves</div>
					{/if}
				</div>
			</div>
		{:else if pipelines !== null && pipelines.length === 0}
			<div>Pipelines Not Detected</div>
		{:else}
			<div class="flex h-full justify-center">
				<div class="my-auto">
					<Spinner className="size-6" />
				</div>
			</div>
		{/if}
	</div>
	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
			type="submit"
		>
			Save
		</button>
	</div>
</form>
