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
		getPipelinesList,
		downloadPipeline,
		deletePipeline,
		uploadPipeline
	} from '$lib/apis';

	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n: Writable<i18nType> = getContext('i18n');

	export let saveHandler: Function;

	let downloading = false;
	let uploading = false;

	let pipelineFiles;

	let PIPELINES_LIST = null;
	let selectedPipelinesUrlIdx = '';

	let pipelines = null;

	let valves = null;
	let valves_spec = null;
	let selectedPipelineIdx = null;

	let pipelineDownloadUrl = '';

	const updateHandler = async () => {
		const pipeline = pipelines[selectedPipelineIdx];

		if (pipeline && (pipeline?.valves ?? false)) {
			for (const property in valves_spec.properties) {
				if (valves_spec.properties[property]?.type === 'array') {
					valves[property] = valves[property].split(',').map((v) => v.trim());
				}
			}

			const res = await updatePipelineValves(
				localStorage.token,
				pipeline.id,
				valves,
				selectedPipelinesUrlIdx
			).catch((error) => {
				toast.error(error);
			});

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
			console.log(selectedPipelinesUrlIdx);
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
			toast.error(error);
			return null;
		});

		if (res) {
			toast.success('Pipeline downloaded successfully');
			setPipelines();
			models.set(await getModels(localStorage.token));
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
					console.log(error);
					toast.error('Something went wrong :/');
					return null;
				}
			);

			if (res) {
				toast.success('Pipeline downloaded successfully');
				setPipelines();
				models.set(await getModels(localStorage.token));
			}
		} else {
			toast.error('No file selected');
		}

		pipelineFiles = null;
		const pipelineUploadInputElement = document.getElementById('pipeline-upload-input');

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
			toast.error(error);
			return null;
		});

		if (res) {
			toast.success('Pipeline deleted successfully');
			setPipelines();
			models.set(await getModels(localStorage.token));
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
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={async () => {
		updateHandler();
	}}
>
	<div class="overflow-y-scroll scrollbar-hidden h-full">
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
									<option value={pipelines.idx.toString()} class="bg-gray-100 dark:bg-gray-700"
										>{pipelines.url}</option
									>
								{/each}
							</select>
						</div>
					</div>
				</div>

				<div class=" my-2">
					<div class=" mb-2 text-sm font-medium">
						{$i18n.t('Upload Pipeline')}
					</div>
					<div class="flex w-full">
						<div class="flex-1 mr-2">
							<input
								id="pipelines-upload-input"
								bind:files={pipelineFiles}
								type="file"
								accept=".py"
								hidden
							/>

							<button
								class="w-full text-sm font-medium py-2 bg-transparent hover:bg-gray-100 border border-dashed dark:border-gray-800 dark:hover:bg-gray-850 text-center rounded-xl"
								type="button"
								on:click={() => {
									document.getElementById('pipelines-upload-input')?.click();
								}}
							>
								{#if pipelineFiles}
									{pipelineFiles.length > 0 ? `${pipelineFiles.length}` : ''} pipeline(s) selected.
								{:else}
									{$i18n.t('Click here to select a py file.')}
								{/if}
							</button>
						</div>
						<button
							class="px-2.5 bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition"
							on:click={() => {
								uploadPipelineHandler();
							}}
							disabled={uploading}
							type="button"
						>
							{#if uploading}
								<div class="self-center">
									<svg
										class=" w-4 h-4"
										viewBox="0 0 24 24"
										fill="currentColor"
										xmlns="http://www.w3.org/2000/svg"
									>
										<style>
											.spinner_ajPY {
												transform-origin: center;
												animation: spinner_AtaB 0.75s infinite linear;
											}

											@keyframes spinner_AtaB {
												100% {
													transform: rotate(360deg);
												}
											}
										</style>
										<path
											d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z"
											opacity=".25"
										/>
										<path
											d="M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z"
											class="spinner_ajPY"
										/>
									</svg>
								</div>
							{:else}
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 16 16"
									fill="currentColor"
									class="size-4"
								>
									<path
										d="M7.25 10.25a.75.75 0 0 0 1.5 0V4.56l2.22 2.22a.75.75 0 1 0 1.06-1.06l-3.5-3.5a.75.75 0 0 0-1.06 0l-3.5 3.5a.75.75 0 0 0 1.06 1.06l2.22-2.22v5.69Z"
									/>
									<path
										d="M3.5 9.75a.75.75 0 0 0-1.5 0v1.5A2.75 2.75 0 0 0 4.75 14h6.5A2.75 2.75 0 0 0 14 11.25v-1.5a.75.75 0 0 0-1.5 0v1.5c0 .69-.56 1.25-1.25 1.25h-6.5c-.69 0-1.25-.56-1.25-1.25v-1.5Z"
									/>
								</svg>
							{/if}
						</button>
					</div>
				</div>

				<div class=" my-2">
					<div class=" mb-2 text-sm font-medium">
						{$i18n.t('Install from Github URL')}
					</div>
					<div class="flex w-full">
						<div class="flex-1 mr-2">
							<input
								class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
								placeholder={$i18n.t('Enter Github Raw URL')}
								bind:value={pipelineDownloadUrl}
							/>
						</div>
						<button
							class="px-2.5 bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition"
							on:click={() => {
								addPipelineHandler();
							}}
							disabled={downloading}
							type="button"
						>
							{#if downloading}
								<div class="self-center">
									<svg
										class=" w-4 h-4"
										viewBox="0 0 24 24"
										fill="currentColor"
										xmlns="http://www.w3.org/2000/svg"
									>
										<style>
											.spinner_ajPY {
												transform-origin: center;
												animation: spinner_AtaB 0.75s infinite linear;
											}

											@keyframes spinner_AtaB {
												100% {
													transform: rotate(360deg);
												}
											}
										</style>
										<path
											d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z"
											opacity=".25"
										/>
										<path
											d="M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z"
											class="spinner_ajPY"
										/>
									</svg>
								</div>
							{:else}
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 16 16"
									fill="currentColor"
									class="w-4 h-4"
								>
									<path
										d="M8.75 2.75a.75.75 0 0 0-1.5 0v5.69L5.03 6.22a.75.75 0 0 0-1.06 1.06l3.5 3.5a.75.75 0 0 0 1.06 0l3.5-3.5a.75.75 0 0 0-1.06-1.06L8.75 8.44V2.75Z"
									/>
									<path
										d="M3.5 9.75a.75.75 0 0 0-1.5 0v1.5A2.75 2.75 0 0 0 4.75 14h6.5A2.75 2.75 0 0 0 14 11.25v-1.5a.75.75 0 0 0-1.5 0v1.5c0 .69-.56 1.25-1.25 1.25h-6.5c-.69 0-1.25-.56-1.25-1.25v-1.5Z"
									/>
								</svg>
							{/if}
						</button>
					</div>

					<div class="mt-2 text-xs text-gray-500">
						<span class=" font-semibold dark:text-gray-200">Warning:</span> Pipelines are a plugin
						system with arbitrary code execution —
						<span class=" font-medium dark:text-gray-400"
							>don't fetch random pipelines from sources you don't trust.</span
						>
					</div>
				</div>

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
									<div class="flex-1">
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
													>{pipeline.name} ({pipeline.type ?? 'pipe'})</option
												>
											{/each}
										</select>
									</div>

									<button
										class="px-2.5 bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition"
										on:click={() => {
											deletePipelineHandler();
										}}
										type="button"
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											viewBox="0 0 16 16"
											fill="currentColor"
											class="w-4 h-4"
										>
											<path
												fill-rule="evenodd"
												d="M5 3.25V4H2.75a.75.75 0 0 0 0 1.5h.3l.815 8.15A1.5 1.5 0 0 0 5.357 15h5.285a1.5 1.5 0 0 0 1.493-1.35l.815-8.15h.3a.75.75 0 0 0 0-1.5H11v-.75A2.25 2.25 0 0 0 8.75 1h-1.5A2.25 2.25 0 0 0 5 3.25Zm2.25-.75a.75.75 0 0 0-.75.75V4h3v-.75a.75.75 0 0 0-.75-.75h-1.5ZM6.05 6a.75.75 0 0 1 .787.713l.275 5.5a.75.75 0 0 1-1.498.075l-.275-5.5A.75.75 0 0 1 6.05 6Zm3.9 0a.75.75 0 0 1 .712.787l-.275 5.5a.75.75 0 0 1-1.498-.075l.275-5.5a.75.75 0 0 1 .786-.711Z"
												clip-rule="evenodd"
											/>
										</svg>
									</button>
								</div>
							{/if}

							<div class="space-y-1">
								{#if pipelines[selectedPipelineIdx].valves}
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
				<div>Pipelines Not Detected</div>
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
