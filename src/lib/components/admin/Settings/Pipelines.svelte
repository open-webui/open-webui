<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { config, models, settings } from '$lib/stores';
	import { getContext, onMount, tick } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import {
		getPipelineValves,
		getPipelineValvesSpec,
		updatePipelineValves,
		getPipelines,
		getModels,
		getPipelinesList,
		downloadPipeline,
		deletePipeline,
		uploadPipeline
	} from '$lib/apis';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import AdminSettingField from './AdminSettingField.svelte';
	import AdminSettingRow from './AdminSettingRow.svelte';

	const i18n: Writable<i18nType> = getContext('i18n');

	export let saveHandler: Function;

	let downloading = false;
	let uploading = false;

	let pipelineFiles: any = null;

	let PIPELINES_LIST: any[] | null = null;
	let selectedPipelinesUrlIdx = '';

	let pipelines: any[] | null = null;

	let valves: any = null;
	let valves_spec: any = null;
	let selectedPipelineIdx: number | null = null;

	let pipelineDownloadUrl = '';
	const inputClass =
		'w-full h-7 rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';
	const selectClass =
		'w-full h-7 rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 pe-8 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500';
	const actionButtonClass =
		'rounded-lg px-2 py-1 text-xs text-gray-500 transition-colors hover:bg-black/5 hover:text-gray-900 disabled:opacity-50 dark:text-gray-500 dark:hover:bg-white/5 dark:hover:text-white';
	const iconButtonClass =
		'flex size-7 items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-black/5 hover:text-gray-900 disabled:opacity-50 dark:text-gray-600 dark:hover:bg-white/5 dark:hover:text-white';
	const mutedMessageClass = 'text-xs text-gray-400 dark:text-gray-600';

	const updateHandler = async () => {
		const pipeline = pipelines[selectedPipelineIdx];

		if (pipeline && (pipeline?.valves ?? false)) {
			for (const property in valves_spec.properties) {
				if (valves_spec.properties[property]?.type === 'array') {
					valves[property] = (valves[property] ?? '').split(',').map((v) => v.trim());
				}
			}

			const res = await updatePipelineValves(
				localStorage.token,
				pipeline.id,
				valves,
				selectedPipelinesUrlIdx
			).catch((error) => {
				toast.error(`${error}`);
			});

			if (res) {
				toast.success($i18n.t('Valves updated successfully'));
				setPipelines();
				models.set(
					await getModels(
						localStorage.token,
						$config?.features?.enable_direct_connections
							? ($settings?.directConnections ?? null)
							: null
					)
				);
				saveHandler();
			}
		} else {
			toast.error($i18n.t('No valves to update'));
		}
	};

	const getValves = async (idx) => {
		valves = null;
		valves_spec = null;

		valves_spec = await getPipelineValvesSpec(
			localStorage.token,
			pipelines[idx].id,
			selectedPipelinesUrlIdx
		);
		valves = await getPipelineValves(
			localStorage.token,
			pipelines[idx].id,
			selectedPipelinesUrlIdx
		);

		for (const property in valves_spec.properties) {
			if (valves_spec.properties[property]?.type === 'array') {
				valves[property] = valves[property].join(',');
			}
		}
	};

	const setPipelines = async () => {
		pipelines = null;
		valves = null;
		valves_spec = null;

		if (PIPELINES_LIST.length > 0) {
			console.debug(selectedPipelinesUrlIdx);
			pipelines = await getPipelines(localStorage.token, selectedPipelinesUrlIdx);

			if (pipelines.length > 0) {
				selectedPipelineIdx = 0;
				await getValves(selectedPipelineIdx);
			}
		} else {
			pipelines = [];
		}
	};

	const addPipelineHandler = async () => {
		downloading = true;
		const res = await downloadPipeline(
			localStorage.token,
			pipelineDownloadUrl,
			selectedPipelinesUrlIdx
		).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Pipeline downloaded successfully'));
			setPipelines();
			models.set(
				await getModels(
					localStorage.token,
					$config?.features?.enable_direct_connections
						? ($settings?.directConnections ?? null)
						: null
				)
			);
		}

		downloading = false;
	};

	const uploadPipelineHandler = async () => {
		uploading = true;

		if (pipelineFiles && pipelineFiles.length !== 0) {
			const file = pipelineFiles[0];

			console.log(file);

			const res = await uploadPipeline(localStorage.token, file, selectedPipelinesUrlIdx).catch(
				(error) => {
					console.error(error);
					toast.error($i18n.t('Something went wrong :/'));
					return null;
				}
			);

			if (res) {
				toast.success($i18n.t('Pipeline downloaded successfully'));
				setPipelines();
				models.set(
					await getModels(
						localStorage.token,
						$config?.features?.enable_direct_connections
							? ($settings?.directConnections ?? null)
							: null
					)
				);
			}
		} else {
			toast.error($i18n.t('No file selected'));
		}

		pipelineFiles = null;
		const pipelineUploadInputElement = document.getElementById('pipelines-upload-input');

		if (pipelineUploadInputElement) {
			pipelineUploadInputElement.value = null;
		}

		uploading = false;
	};

	const deletePipelineHandler = async () => {
		const res = await deletePipeline(
			localStorage.token,
			pipelines[selectedPipelineIdx].id,
			selectedPipelinesUrlIdx
		).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Pipeline deleted successfully'));
			setPipelines();
			models.set(
				await getModels(
					localStorage.token,
					$config?.features?.enable_direct_connections
						? ($settings?.directConnections ?? null)
						: null
				)
			);
		}
	};

	onMount(async () => {
		PIPELINES_LIST = await getPipelinesList(localStorage.token);
		console.log(PIPELINES_LIST);

		if (PIPELINES_LIST.length > 0) {
			selectedPipelinesUrlIdx = PIPELINES_LIST[0]['idx'].toString();
		}

		await setPipelines();
	});
</script>

<form
	class="flex h-full flex-col justify-between text-sm"
	on:submit|preventDefault={async () => {
		updateHandler();
	}}
>
	<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-4">{$i18n.t('Pipelines')}</h2>

	<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5">
		{#if PIPELINES_LIST !== null}
			{#if PIPELINES_LIST.length > 0}
				<input
					id="pipelines-upload-input"
					bind:files={pipelineFiles}
					type="file"
					accept=".py"
					hidden
				/>

				<div class="flex flex-col gap-2.5">
					<AdminSettingField label={$i18n.t('Pipeline URL')}>
						<select
							class={selectClass}
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

							{#each PIPELINES_LIST as pipelines}
								<option value={pipelines.idx.toString()} class="bg-gray-100 dark:bg-gray-700"
									>{pipelines.url}</option
								>
							{/each}
						</select>
					</AdminSettingField>

					<AdminSettingField label={$i18n.t('Upload Pipeline')}>
						<div class="flex gap-2">
							<button
								class="h-7 flex-1 rounded-lg border border-dashed border-gray-100/50 bg-transparent px-2 text-left text-xs text-gray-500 transition-colors hover:bg-black/5 hover:text-gray-900 dark:border-white/[0.04] dark:text-gray-500 dark:hover:bg-white/5 dark:hover:text-white"
								type="button"
								on:click={() => {
									document.getElementById('pipelines-upload-input')?.click();
								}}
							>
								{#if pipelineFiles}
									{pipelineFiles.length > 0 ? `${pipelineFiles.length}` : ''} pipeline(s) selected
								{:else}
									{$i18n.t('Select a .py file')}
								{/if}
							</button>

							<button
								class={actionButtonClass}
								on:click={() => {
									uploadPipelineHandler();
								}}
								disabled={uploading}
								type="button"
							>
								{uploading ? $i18n.t('Uploading') : $i18n.t('Upload')}
							</button>
						</div>
					</AdminSettingField>

					<AdminSettingField
						label={$i18n.t('GitHub URL')}
						description={`${$i18n.t('Pipelines are a plugin system with arbitrary code execution.')} ${$i18n.t("Don't fetch random pipelines from sources you don't trust.")}`}
					>
						<div class="flex gap-2">
							<input
								class={inputClass}
								placeholder={$i18n.t('Enter GitHub Raw URL')}
								bind:value={pipelineDownloadUrl}
							/>
							<button
								class={actionButtonClass}
								on:click={() => {
									addPipelineHandler();
								}}
								disabled={downloading}
								type="button"
							>
								{downloading ? $i18n.t('Installing') : $i18n.t('Install')}
							</button>
						</div>
					</AdminSettingField>

					{#if pipelines !== null}
						{#if pipelines.length > 0}
							<AdminSettingField label={$i18n.t('Pipeline')}>
								<div class="flex gap-2">
									<select
										class={selectClass}
										bind:value={selectedPipelineIdx}
										placeholder={$i18n.t('Select a pipeline')}
										on:change={async () => {
											await tick();
											await getValves(selectedPipelineIdx ?? 0);
										}}
									>
										{#each pipelines as pipeline, idx}
											<option value={idx} class="bg-gray-100 dark:bg-gray-700">
												{pipeline.name} ({pipeline.type ?? 'pipe'})
											</option>
										{/each}
									</select>

									<button
										class={actionButtonClass}
										on:click={() => {
											deletePipelineHandler();
										}}
										type="button"
									>
										{$i18n.t('Delete')}
									</button>
								</div>
							</AdminSettingField>

							{#if pipelines[selectedPipelineIdx ?? 0]?.valves}
								{#if valves}
									{#each Object.keys(valves_spec.properties) as property}
										<div>
											<AdminSettingRow label={valves_spec.properties[property].title}>
												<button
													class={actionButtonClass}
													type="button"
													on:click={() => {
														valves[property] = (valves[property] ?? null) === null ? '' : null;
													}}
												>
													{(valves[property] ?? null) === null
														? $i18n.t('None')
														: $i18n.t('Custom')}
												</button>
											</AdminSettingRow>

											{#if (valves[property] ?? null) !== null}
												<div class="mt-1">
													{#if valves_spec.properties[property]?.enum ?? null}
														<select class={selectClass} bind:value={valves[property]}>
															{#each valves_spec.properties[property].enum as option}
																<option value={option} selected={option === valves[property]}>
																	{option}
																</option>
															{/each}
														</select>
													{:else if (valves_spec.properties[property]?.type ?? null) === 'boolean'}
														<AdminSettingRow
															label={valves[property] ? $i18n.t('Enabled') : $i18n.t('Disabled')}
															labelClassName="text-gray-400 dark:text-gray-600"
														>
															<Switch bind:state={valves[property]} />
														</AdminSettingRow>
													{:else}
														<input
															class={inputClass}
															type="text"
															placeholder={valves_spec.properties[property].title}
															bind:value={valves[property]}
															autocomplete="off"
															required
														/>
													{/if}
												</div>
											{/if}
										</div>
									{/each}
								{:else}
									<Spinner className="size-5" />
								{/if}
							{:else}
								<div class={mutedMessageClass}>{$i18n.t('No valves')}</div>
							{/if}
						{:else}
							<div class={mutedMessageClass}>{$i18n.t('Pipelines Not Detected')}</div>
						{/if}
					{:else}
						<div class="flex justify-center py-4">
							<Spinner className="size-4" />
						</div>
					{/if}
				</div>
			{:else}
				<div class={mutedMessageClass}>{$i18n.t('Pipelines Not Detected')}</div>
			{/if}
		{:else}
			<div class="flex justify-center h-full">
				<div class="my-auto">
					<Spinner className="size-6" />
				</div>
			</div>
		{/if}
	</div>

	{#if PIPELINES_LIST !== null && PIPELINES_LIST.length > 0}
		<div class="flex justify-end pt-6 text-sm font-normal">
			<button
				class="px-3.5 py-1.5 text-sm font-normal bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
				type="submit"
			>
				{$i18n.t('Save')}
			</button>
		</div>
	{/if}
</form>
