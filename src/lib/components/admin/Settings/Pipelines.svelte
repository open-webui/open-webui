<script lang="ts">
	import { v4 as uuidv4 } from 'uuid';

	import { getContext, onMount, tick } from 'svelte';

	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { stringify } from 'postcss';
	import {
		getPipelineValves,
		getPipelineValvesSpec,
		updatePipelineValves,
		getPipelines
	} from '$lib/apis';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { toast } from 'svelte-sonner';

	const i18n: Writable<i18nType> = getContext('i18n');

	export let saveHandler: Function;

	let pipelines = null;

	let valves = null;
	let valves_spec = null;

	let selectedPipelineIdx = null;

	const updateHandler = async () => {
		const pipeline = pipelines[selectedPipelineIdx];

		if (pipeline && (pipeline?.pipeline?.valves ?? false)) {
			const res = await updatePipelineValves(localStorage.token, pipeline.id, valves).catch(
				(error) => {
					toast.error(error);
				}
			);

			if (res) {
				toast.success('Valves updated successfully');
				saveHandler();
			}
		} else {
			toast.error('No valves to update');
		}
	};

	onMount(async () => {
		pipelines = await getPipelines(localStorage.token);

		if (pipelines.length > 0) {
			selectedPipelineIdx = 0;
		}
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={async () => {
		updateHandler();
	}}
>
	<div class=" space-y-2 pr-1.5 overflow-y-scroll max-h-80 h-full">
		{#if pipelines !== null && pipelines.length > 0}
			<div class="flex w-full justify-between mb-2">
				<div class=" self-center text-sm font-semibold">
					{$i18n.t('Pipelines')}
				</div>
			</div>
			<div class="space-y-1">
				{#if pipelines.length > 0}
					<div class="flex gap-2">
						<div class="flex-1 pb-1">
							<select
								class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
								bind:value={selectedPipelineIdx}
								placeholder={$i18n.t('Select a pipeline')}
								on:change={async () => {
									await tick();
									valves_spec = await getPipelineValvesSpec(
										localStorage.token,
										pipelines[selectedPipelineIdx].id
									);
									valves = await getPipelineValves(
										localStorage.token,
										pipelines[selectedPipelineIdx].id
									);
								}}
							>
								{#each pipelines as pipeline, idx}
									<option value={idx} class="bg-gray-100 dark:bg-gray-700"
										>{pipeline.name} ({pipeline.pipeline.type ?? 'pipe'})</option
									>
								{/each}
							</select>
						</div>
					</div>
				{/if}

				<div class="text-sm font-medium">{$i18n.t('Valves')}</div>

				<div class="space-y-1">
					{#if pipelines[selectedPipelineIdx].pipeline.valves}
						{#if valves}
							{#each Object.keys(valves_spec.properties) as property, idx}
								<div class=" py-0.5 w-full justify-between">
									<div class="flex w-full justify-between">
										<div class=" self-center text-xs font-medium">
											{valves_spec.properties[property].title}
										</div>

										<button
											class="p-1 px-3 text-xs flex rounded transition"
											type="button"
											on:click={() => {
												valves[property] = (valves[property] ?? null) === null ? '' : null;
											}}
										>
											{#if (valves[property] ?? null) === null}
												<span class="ml-2 self-center"> {$i18n.t('None')} </span>
											{:else}
												<span class="ml-2 self-center"> {$i18n.t('Custom')} </span>
											{/if}
										</button>
									</div>

									{#if (valves[property] ?? null) !== null}
										<div class="flex mt-0.5 space-x-2">
											<div class=" flex-1">
												<input
													class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
													type="text"
													placeholder={valves_spec.properties[property].title}
													bind:value={valves[property]}
													autocomplete="off"
												/>
											</div>
										</div>
									{/if}
								</div>
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
