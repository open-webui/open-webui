<script lang="ts">
	import { v4 as uuidv4 } from 'uuid';

	import { toast } from 'svelte-sonner';
	import { models } from '$lib/stores';
	import { getContext, onMount, tick } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import {
		getPipelineValves,
		getPipelineValvesSpec,
		updatePipelineValves,
		getPipelines,
		getModels,
		getPipelinesList
	} from '$lib/apis';

	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n: Writable<i18nType> = getContext('i18n');

	export let saveHandler: Function;

	let PIPELINES_LIST = null;
	let selectedPipelinesUrlIdx = '';

	let pipelines = null;

	let valves = null;
	let valves_spec = null;
	let selectedPipelineIdx = null;

	const updateHandler = async () => {
		const pipeline = pipelines[selectedPipelineIdx];

		if (pipeline && (pipeline?.pipeline?.valves ?? false)) {
			if (valves?.pipelines ?? false) {
				valves.pipelines = valves.pipelines.split(',').map((v) => v.trim());
			}

			const res = await updatePipelineValves(localStorage.token, pipeline.id, valves).catch(
				(error) => {
					toast.error(error);
				}
			);

			if (res) {
				toast.success('Valves updated successfully');
				setPipelines();
				models.set(await getModels(localStorage.token));
				saveHandler();
			}
		} else {
			toast.error('No valves to update');
		}
	};

	const getValves = async (idx) => {
		valves = null;
		valves_spec = null;

		valves_spec = await getPipelineValvesSpec(localStorage.token, pipelines[idx].id);
		valves = await getPipelineValves(localStorage.token, pipelines[idx].id);

		if (valves?.pipelines ?? false) {
			valves.pipelines = valves.pipelines.join(',');
		}
	};

	const setPipelines = async () => {
		pipelines = null;
		valves = null;
		valves_spec = null;

		pipelines = await getPipelines(localStorage.token, selectedPipelinesUrlIdx);

		if (pipelines.length > 0) {
			selectedPipelineIdx = 0;
			await getValves(selectedPipelineIdx);
		}
	};

	onMount(async () => {
		PIPELINES_LIST = await getPipelinesList(localStorage.token);

		if (PIPELINES_LIST.length > 0) {
			selectedPipelinesUrlIdx = PIPELINES_LIST[0]['idx'];
		}

		setPipelines();
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={async () => {
		updateHandler();
	}}
>
	<div class=" space-y-2 pr-1.5 overflow-y-scroll max-h-80 h-full">
		{#if PIPELINES_LIST !== null}
			<div class="flex w-full justify-between mb-2">
				<div class=" self-center text-sm font-semibold">
					{$i18n.t('Manage Pipelines')}
				</div>
			</div>

			{#if PIPELINES_LIST.length > 0}
				<div class="space-y-1">
					<div class="flex gap-2">
						<div class="flex-1">
							<select
								class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
								bind:value={selectedPipelinesUrlIdx}
								placeholder={$i18n.t('Select a pipeline url')}
								on:change={async () => {
									await tick();
									await setPipelines();
								}}
							>
								<option value="" selected disabled class="bg-gray-100 dark:bg-gray-700"
									>{$i18n.t('Select a pipeline url')}</option
								>

								{#each PIPELINES_LIST as pipelines, idx}
									<option value={pipelines.idx} class="bg-gray-100 dark:bg-gray-700"
										>{pipelines.url}</option
									>
								{/each}
							</select>
						</div>
					</div>
				</div>
			{/if}

			<hr class=" dark:border-gray-800 my-3 w-full" />

			{#if pipelines !== null}
				{#if pipelines.length > 0}
					<div class="flex w-full justify-between mb-2">
						<div class=" self-center text-sm font-semibold">
							{$i18n.t('Pipelines Valves')}
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
											await getValves(selectedPipelineIdx);
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
				{:else if pipelines.length === 0}
					<div>Pipelines Not Detected</div>
				{/if}
			{:else}
				<div class="flex justify-center">
					<div class="my-auto">
						<Spinner className="size-4" />
					</div>
				</div>
			{/if}
		{:else}
			<div class="flex justify-center h-full">
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
