<script lang="ts">
	import queue from 'async/queue';
	import { toast } from 'svelte-sonner';

	import {
		createModel,
		deleteModel,
		getOllamaUrls,
		getOllamaVersion,
		pullModel
	} from '$lib/apis/ollama';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, models, user } from '$lib/stores';
	import { splitStream } from '$lib/utils';
	import { onMount } from 'svelte';
	import { addLiteLLMModel, deleteLiteLLMModel, getLiteLLMModelInfo } from '$lib/apis/litellm';

	export let getModels: Function;

	let showLiteLLM = false;
	let showLiteLLMParams = false;
	let modelUploadInputElement: HTMLInputElement;
	let liteLLMModelInfo = [];

	let liteLLMModel = '';
	let liteLLMModelName = '';
	let liteLLMAPIBase = '';
	let liteLLMAPIKey = '';
	let liteLLMRPM = '';

	let deleteLiteLLMModelId = '';

	$: liteLLMModelName = liteLLMModel;

	// Models

	let OLLAMA_URLS = [];
	let selectedOllamaUrlIdx: string | null = null;
	let showExperimentalOllama = false;
	let ollamaVersion = '';
	const MAX_PARALLEL_DOWNLOADS = 3;
	const modelDownloadQueue = queue(
		(task: { modelName: string }, cb) =>
			pullModelHandlerProcessor({ modelName: task.modelName, callback: cb }),
		MAX_PARALLEL_DOWNLOADS
	);
	let modelDownloadStatus: Record<string, any> = {};

	let modelTransferring = false;
	let modelTag = '';
	let digest = '';
	let pullProgress = null;

	let modelUploadMode = 'file';
	let modelInputFile = '';
	let modelFileUrl = '';
	let modelFileContent = `TEMPLATE """{{ .System }}\nUSER: {{ .Prompt }}\nASSISTANT: """\nPARAMETER num_ctx 4096\nPARAMETER stop "</s>"\nPARAMETER stop "USER:"\nPARAMETER stop "ASSISTANT:"`;
	let modelFileDigest = '';
	let uploadProgress = null;

	let deleteModelTag = '';

	const pullModelHandler = async () => {
		const sanitizedModelTag = modelTag.trim();
		if (modelDownloadStatus[sanitizedModelTag]) {
			toast.error(`Model '${sanitizedModelTag}' is already in queue for downloading.`);
			return;
		}
		if (Object.keys(modelDownloadStatus).length === 3) {
			toast.error('Maximum of 3 models can be downloaded simultaneously. Please try again later.');
			return;
		}

		modelTransferring = true;

		modelDownloadQueue.push(
			{ modelName: sanitizedModelTag },
			async (data: { modelName: string; success: boolean; error?: Error }) => {
				const { modelName } = data;
				// Remove the downloaded model
				delete modelDownloadStatus[modelName];

				console.log(data);

				if (!data.success) {
					toast.error(data.error);
				} else {
					toast.success(`Model '${modelName}' has been successfully downloaded.`);

					const notification = new Notification($WEBUI_NAME, {
						body: `Model '${modelName}' has been successfully downloaded.`,
						icon: `${WEBUI_BASE_URL}/static/favicon.png`
					});

					models.set(await getModels());
				}
			}
		);

		modelTag = '';
		modelTransferring = false;
	};

	const uploadModelHandler = async () => {
		modelTransferring = true;
		uploadProgress = 0;

		let uploaded = false;
		let fileResponse = null;
		let name = '';

		if (modelUploadMode === 'file') {
			const file = modelInputFile[0];
			const formData = new FormData();
			formData.append('file', file);

			fileResponse = await fetch(`${WEBUI_API_BASE_URL}/utils/upload`, {
				method: 'POST',
				headers: {
					...($user && { Authorization: `Bearer ${localStorage.token}` })
				},
				body: formData
			}).catch((error) => {
				console.log(error);
				return null;
			});
		} else {
			fileResponse = await fetch(`${WEBUI_API_BASE_URL}/utils/download?url=${modelFileUrl}`, {
				method: 'GET',
				headers: {
					...($user && { Authorization: `Bearer ${localStorage.token}` })
				}
			}).catch((error) => {
				console.log(error);
				return null;
			});
		}

		if (fileResponse && fileResponse.ok) {
			const reader = fileResponse.body
				.pipeThrough(new TextDecoderStream())
				.pipeThrough(splitStream('\n'))
				.getReader();

			while (true) {
				const { value, done } = await reader.read();
				if (done) break;

				try {
					let lines = value.split('\n');

					for (const line of lines) {
						if (line !== '') {
							let data = JSON.parse(line.replace(/^data: /, ''));

							if (data.progress) {
								uploadProgress = data.progress;
							}

							if (data.error) {
								throw data.error;
							}

							if (data.done) {
								modelFileDigest = data.blob;
								name = data.name;
								uploaded = true;
							}
						}
					}
				} catch (error) {
					console.log(error);
				}
			}
		}

		if (uploaded) {
			const res = await createModel(
				localStorage.token,
				`${name}:latest`,
				`FROM @${modelFileDigest}\n${modelFileContent}`
			);

			if (res && res.ok) {
				const reader = res.body
					.pipeThrough(new TextDecoderStream())
					.pipeThrough(splitStream('\n'))
					.getReader();

				while (true) {
					const { value, done } = await reader.read();
					if (done) break;

					try {
						let lines = value.split('\n');

						for (const line of lines) {
							if (line !== '') {
								console.log(line);
								let data = JSON.parse(line);
								console.log(data);

								if (data.error) {
									throw data.error;
								}
								if (data.detail) {
									throw data.detail;
								}

								if (data.status) {
									if (
										!data.digest &&
										!data.status.includes('writing') &&
										!data.status.includes('sha256')
									) {
										toast.success(data.status);
									} else {
										if (data.digest) {
											digest = data.digest;

											if (data.completed) {
												pullProgress = Math.round((data.completed / data.total) * 1000) / 10;
											} else {
												pullProgress = 100;
											}
										}
									}
								}
							}
						}
					} catch (error) {
						console.log(error);
						toast.error(error);
					}
				}
			}
		}

		modelFileUrl = '';
		modelInputFile = '';
		modelTransferring = false;
		uploadProgress = null;

		models.set(await getModels());
	};

	const deleteModelHandler = async () => {
		const res = await deleteModel(localStorage.token, deleteModelTag, selectedOllamaUrlIdx).catch(
			(error) => {
				toast.error(error);
			}
		);

		if (res) {
			toast.success(`Deleted ${deleteModelTag}`);
		}

		deleteModelTag = '';
		models.set(await getModels());
	};

	const pullModelHandlerProcessor = async (opts: { modelName: string; callback: Function }) => {
		const res = await pullModel(localStorage.token, opts.modelName, selectedOllamaUrlIdx).catch(
			(error) => {
				opts.callback({ success: false, error, modelName: opts.modelName });
				return null;
			}
		);

		if (res) {
			const reader = res.body
				.pipeThrough(new TextDecoderStream())
				.pipeThrough(splitStream('\n'))
				.getReader();

			while (true) {
				try {
					const { value, done } = await reader.read();
					if (done) break;

					let lines = value.split('\n');

					for (const line of lines) {
						if (line !== '') {
							let data = JSON.parse(line);
							if (data.error) {
								throw data.error;
							}
							if (data.detail) {
								throw data.detail;
							}
							if (data.status) {
								if (data.digest) {
									let downloadProgress = 0;
									if (data.completed) {
										downloadProgress = Math.round((data.completed / data.total) * 1000) / 10;
									} else {
										downloadProgress = 100;
									}
									modelDownloadStatus[opts.modelName] = {
										pullProgress: downloadProgress,
										digest: data.digest
									};
								} else {
									toast.success(data.status);
								}
							}
						}
					}
				} catch (error) {
					console.log(error);
					if (typeof error !== 'string') {
						error = error.message;
					}
					opts.callback({ success: false, error, modelName: opts.modelName });
				}
			}
			opts.callback({ success: true, modelName: opts.modelName });
		}
	};

	const addLiteLLMModelHandler = async () => {
		if (!liteLLMModelInfo.find((info) => info.model_name === liteLLMModelName)) {
			const res = await addLiteLLMModel(localStorage.token, {
				name: liteLLMModelName,
				model: liteLLMModel,
				api_base: liteLLMAPIBase,
				api_key: liteLLMAPIKey,
				rpm: liteLLMRPM
			}).catch((error) => {
				toast.error(error);
				return null;
			});

			if (res) {
				if (res.message) {
					toast.success(res.message);
				}
			}
		} else {
			toast.error(`Model ${liteLLMModelName} already exists.`);
		}

		liteLLMModelName = '';
		liteLLMModel = '';
		liteLLMAPIBase = '';
		liteLLMAPIKey = '';
		liteLLMRPM = '';

		liteLLMModelInfo = await getLiteLLMModelInfo(localStorage.token);
		models.set(await getModels());
	};

	const deleteLiteLLMModelHandler = async () => {
		const res = await deleteLiteLLMModel(localStorage.token, deleteLiteLLMModelId).catch(
			(error) => {
				toast.error(error);
				return null;
			}
		);

		if (res) {
			if (res.message) {
				toast.success(res.message);
			}
		}

		deleteLiteLLMModelId = '';
		liteLLMModelInfo = await getLiteLLMModelInfo(localStorage.token);
		models.set(await getModels());
	};

	onMount(async () => {
		OLLAMA_URLS = await getOllamaUrls(localStorage.token).catch((error) => {
			toast.error(error);
			return [];
		});

		if (OLLAMA_URLS.length > 1) {
			selectedOllamaUrlIdx = 0;
		}

		ollamaVersion = await getOllamaVersion(localStorage.token).catch((error) => false);
		liteLLMModelInfo = await getLiteLLMModelInfo(localStorage.token);
	});
</script>

<div class="flex flex-col h-full justify-between text-sm">
	<div class=" space-y-3 pr-1.5 overflow-y-scroll h-[23rem]">
		{#if ollamaVersion}
			<div class="space-y-2 pr-1.5">
				<div class="text-sm font-medium">Manage Ollama Models</div>

				{#if OLLAMA_URLS.length > 1}
					<div class="flex-1 pb-1">
						<select
							class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
							bind:value={selectedOllamaUrlIdx}
							placeholder="Select an Ollama instance"
						>
							{#each OLLAMA_URLS as url, idx}
								<option value={idx} class="bg-gray-100 dark:bg-gray-700">{url}</option>
							{/each}
						</select>
					</div>
				{/if}

				<div class="space-y-2">
					<div>
						<div class=" mb-2 text-sm font-medium">Pull a model from Ollama.com</div>
						<div class="flex w-full">
							<div class="flex-1 mr-2">
								<input
									class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
									placeholder="Enter model tag (e.g. mistral:7b)"
									bind:value={modelTag}
								/>
							</div>
							<button
								class="px-2.5 bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition"
								on:click={() => {
									pullModelHandler();
								}}
								disabled={modelTransferring}
							>
								{#if modelTransferring}
									<div class="self-center">
										<svg
											class=" w-4 h-4"
											viewBox="0 0 24 24"
											fill="currentColor"
											xmlns="http://www.w3.org/2000/svg"
											><style>
												.spinner_ajPY {
													transform-origin: center;
													animation: spinner_AtaB 0.75s infinite linear;
												}
												@keyframes spinner_AtaB {
													100% {
														transform: rotate(360deg);
													}
												}
											</style><path
												d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z"
												opacity=".25"
											/><path
												d="M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z"
												class="spinner_ajPY"
											/></svg
										>
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

						<div class="mt-2 mb-1 text-xs text-gray-400 dark:text-gray-500">
							To access the available model names for downloading, <a
								class=" text-gray-500 dark:text-gray-300 font-medium underline"
								href="https://ollama.com/library"
								target="_blank">click here.</a
							>
						</div>

						{#if Object.keys(modelDownloadStatus).length > 0}
							{#each Object.keys(modelDownloadStatus) as model}
								<div class="flex flex-col">
									<div class="font-medium mb-1">{model}</div>
									<div class="">
										<div
											class="dark:bg-gray-600 bg-gray-500 text-xs font-medium text-gray-100 text-center p-0.5 leading-none rounded-full"
											style="width: {Math.max(15, modelDownloadStatus[model].pullProgress ?? 0)}%"
										>
											{modelDownloadStatus[model].pullProgress ?? 0}%
										</div>
										<div class="mt-1 text-xs dark:text-gray-500" style="font-size: 0.5rem;">
											{modelDownloadStatus[model].digest}
										</div>
									</div>
								</div>
							{/each}
						{/if}
					</div>

					<div>
						<div class=" mb-2 text-sm font-medium">Delete a model</div>
						<div class="flex w-full">
							<div class="flex-1 mr-2">
								<select
									class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
									bind:value={deleteModelTag}
									placeholder="Select a model"
								>
									{#if !deleteModelTag}
										<option value="" disabled selected>Select a model</option>
									{/if}
									{#each $models.filter((m) => m.size != null && (selectedOllamaUrlIdx === null ? true : (m?.urls ?? []).includes(selectedOllamaUrlIdx))) as model}
										<option value={model.name} class="bg-gray-100 dark:bg-gray-700"
											>{model.name + ' (' + (model.size / 1024 ** 3).toFixed(1) + ' GB)'}</option
										>
									{/each}
								</select>
							</div>
							<button
								class="px-2.5 bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition"
								on:click={() => {
									deleteModelHandler();
								}}
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
					</div>

					<div class="pt-1">
						<div class="flex justify-between items-center text-xs">
							<div class=" text-sm font-medium">Experimental</div>
							<button
								class=" text-xs font-medium text-gray-500"
								type="button"
								on:click={() => {
									showExperimentalOllama = !showExperimentalOllama;
								}}>{showExperimentalOllama ? 'Hide' : 'Show'}</button
							>
						</div>
					</div>

					{#if showExperimentalOllama}
						<form
							on:submit|preventDefault={() => {
								uploadModelHandler();
							}}
						>
							<div class=" mb-2 flex w-full justify-between">
								<div class="  text-sm font-medium">Upload a GGUF model</div>

								<button
									class="p-1 px-3 text-xs flex rounded transition"
									on:click={() => {
										if (modelUploadMode === 'file') {
											modelUploadMode = 'url';
										} else {
											modelUploadMode = 'file';
										}
									}}
									type="button"
								>
									{#if modelUploadMode === 'file'}
										<span class="ml-2 self-center">File Mode</span>
									{:else}
										<span class="ml-2 self-center">URL Mode</span>
									{/if}
								</button>
							</div>

							<div class="flex w-full mb-1.5">
								<div class="flex flex-col w-full">
									{#if modelUploadMode === 'file'}
										<div class="flex-1 {modelInputFile && modelInputFile.length > 0 ? 'mr-2' : ''}">
											<input
												id="model-upload-input"
												bind:this={modelUploadInputElement}
												type="file"
												bind:files={modelInputFile}
												on:change={() => {
													console.log(modelInputFile);
												}}
												accept=".gguf"
												required
												hidden
											/>

											<button
												type="button"
												class="w-full rounded-lg text-left py-2 px-4 dark:text-gray-300 dark:bg-gray-850"
												on:click={() => {
													modelUploadInputElement.click();
												}}
											>
												{#if modelInputFile && modelInputFile.length > 0}
													{modelInputFile[0].name}
												{:else}
													Click here to select
												{/if}
											</button>
										</div>
									{:else}
										<div class="flex-1 {modelFileUrl !== '' ? 'mr-2' : ''}">
											<input
												class="w-full rounded-lg text-left py-2 px-4 dark:text-gray-300 dark:bg-gray-850 outline-none {modelFileUrl !==
												''
													? 'mr-2'
													: ''}"
												type="url"
												required
												bind:value={modelFileUrl}
												placeholder="Type Hugging Face Resolve (Download) URL"
											/>
										</div>
									{/if}
								</div>

								{#if (modelUploadMode === 'file' && modelInputFile && modelInputFile.length > 0) || (modelUploadMode === 'url' && modelFileUrl !== '')}
									<button
										class="px-3 text-gray-100 bg-emerald-600 hover:bg-emerald-700 disabled:bg-gray-700 disabled:cursor-not-allowed rounded transition"
										type="submit"
										disabled={modelTransferring}
									>
										{#if modelTransferring}
											<div class="self-center">
												<svg
													class=" w-4 h-4"
													viewBox="0 0 24 24"
													fill="currentColor"
													xmlns="http://www.w3.org/2000/svg"
													><style>
														.spinner_ajPY {
															transform-origin: center;
															animation: spinner_AtaB 0.75s infinite linear;
														}
														@keyframes spinner_AtaB {
															100% {
																transform: rotate(360deg);
															}
														}
													</style><path
														d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z"
														opacity=".25"
													/><path
														d="M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z"
														class="spinner_ajPY"
													/></svg
												>
											</div>
										{:else}
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 16 16"
												fill="currentColor"
												class="w-4 h-4"
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
								{/if}
							</div>

							{#if (modelUploadMode === 'file' && modelInputFile && modelInputFile.length > 0) || (modelUploadMode === 'url' && modelFileUrl !== '')}
								<div>
									<div>
										<div class=" my-2.5 text-sm font-medium">Modelfile Content</div>
										<textarea
											bind:value={modelFileContent}
											class="w-full rounded py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none resize-none"
											rows="6"
										/>
									</div>
								</div>
							{/if}
							<div class=" mt-1 text-xs text-gray-400 dark:text-gray-500">
								To access the GGUF models available for downloading, <a
									class=" text-gray-500 dark:text-gray-300 font-medium underline"
									href="https://huggingface.co/models?search=gguf"
									target="_blank">click here.</a
								>
							</div>

							{#if uploadProgress !== null}
								<div class="mt-2">
									<div class=" mb-2 text-xs">Upload Progress</div>

									<div class="w-full rounded-full dark:bg-gray-800">
										<div
											class="dark:bg-gray-600 bg-gray-500 text-xs font-medium text-gray-100 text-center p-0.5 leading-none rounded-full"
											style="width: {Math.max(15, uploadProgress ?? 0)}%"
										>
											{uploadProgress ?? 0}%
										</div>
									</div>
									<div class="mt-1 text-xs dark:text-gray-500" style="font-size: 0.5rem;">
										{modelFileDigest}
									</div>
								</div>
							{/if}
						</form>
					{/if}
				</div>
			</div>
			<hr class=" dark:border-gray-700 my-2" />
		{/if}

		<div class=" space-y-3">
			<div class="mt-2 space-y-3 pr-1.5">
				<div>
					<div class=" mb-2 text-sm font-medium">Manage LiteLLM Models</div>

					<div>
						<div class="flex justify-between items-center text-xs">
							<div class=" text-sm font-medium">Add a model</div>
							<button
								class=" text-xs font-medium text-gray-500"
								type="button"
								on:click={() => {
									showLiteLLMParams = !showLiteLLMParams;
								}}>{showLiteLLMParams ? 'Hide Additional Params' : 'Show Additional Params'}</button
							>
						</div>
					</div>

					<div class="my-2 space-y-2">
						<div class="flex w-full mb-1.5">
							<div class="flex-1 mr-2">
								<input
									class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
									placeholder="Enter LiteLLM Model (litellm_params.model)"
									bind:value={liteLLMModel}
									autocomplete="off"
								/>
							</div>

							<button
								class="px-2.5 bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition"
								on:click={() => {
									addLiteLLMModelHandler();
								}}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 16 16"
									fill="currentColor"
									class="w-4 h-4"
								>
									<path
										d="M8.75 3.75a.75.75 0 0 0-1.5 0v3.5h-3.5a.75.75 0 0 0 0 1.5h3.5v3.5a.75.75 0 0 0 1.5 0v-3.5h3.5a.75.75 0 0 0 0-1.5h-3.5v-3.5Z"
									/>
								</svg>
							</button>
						</div>

						{#if showLiteLLMParams}
							<div>
								<div class=" mb-1.5 text-sm font-medium">Model Name</div>
								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
											placeholder="Enter Model Name (model_name)"
											bind:value={liteLLMModelName}
											autocomplete="off"
										/>
									</div>
								</div>
							</div>

							<div>
								<div class=" mb-1.5 text-sm font-medium">API Base URL</div>
								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
											placeholder="Enter LiteLLM API Base URL (litellm_params.api_base)"
											bind:value={liteLLMAPIBase}
											autocomplete="off"
										/>
									</div>
								</div>
							</div>

							<div>
								<div class=" mb-1.5 text-sm font-medium">API Key</div>
								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
											placeholder="Enter LiteLLM API Key (litellm_params.api_key)"
											bind:value={liteLLMAPIKey}
											autocomplete="off"
										/>
									</div>
								</div>
							</div>

							<div>
								<div class="mb-1.5 text-sm font-medium">API RPM</div>
								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
											placeholder="Enter LiteLLM API RPM (litellm_params.rpm)"
											bind:value={liteLLMRPM}
											autocomplete="off"
										/>
									</div>
								</div>
							</div>
						{/if}
					</div>

					<div class="mb-2 text-xs text-gray-400 dark:text-gray-500">
						Not sure what to add?
						<a
							class=" text-gray-300 font-medium underline"
							href="https://litellm.vercel.app/docs/proxy/configs#quick-start"
							target="_blank"
						>
							Click here for help.
						</a>
					</div>

					<div>
						<div class=" mb-2.5 text-sm font-medium">Delete a model</div>
						<div class="flex w-full">
							<div class="flex-1 mr-2">
								<select
									class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
									bind:value={deleteLiteLLMModelId}
									placeholder="Select a model"
								>
									{#if !deleteLiteLLMModelId}
										<option value="" disabled selected>Select a model</option>
									{/if}
									{#each liteLLMModelInfo as model}
										<option value={model.model_info.id} class="bg-gray-100 dark:bg-gray-700"
											>{model.model_name}</option
										>
									{/each}
								</select>
							</div>
							<button
								class="px-2.5 bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition"
								on:click={() => {
									deleteLiteLLMModelHandler();
								}}
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
					</div>
				</div>
			</div>

			<!-- <div class="mt-2 space-y-3 pr-1.5">
				<div>
					<div class=" mb-2.5 text-sm font-medium">Add LiteLLM Model</div>
					<div class="flex w-full mb-2">
						<div class="flex-1">
							<input
								class="w-full rounded py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none"
								placeholder="Enter LiteLLM Model (e.g. ollama/mistral)"
								bind:value={liteLLMModel}
								autocomplete="off"
							/>
						</div>
					</div>

					<div class="flex justify-between items-center text-sm">
						<div class="  font-medium">Advanced Model Params</div>
						<button
							class=" text-xs font-medium text-gray-500"
							type="button"
							on:click={() => {
								showLiteLLMParams = !showLiteLLMParams;
							}}>{showLiteLLMParams ? 'Hide' : 'Show'}</button
						>
					</div>

					{#if showLiteLLMParams}
						<div>
							<div class=" mb-2.5 text-sm font-medium">LiteLLM API Key</div>
							<div class="flex w-full">
								<div class="flex-1">
									<input
										class="w-full rounded py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none"
										placeholder="Enter LiteLLM API Key (e.g. os.environ/AZURE_API_KEY_CA)"
										bind:value={liteLLMAPIKey}
										autocomplete="off"
									/>
								</div>
							</div>
						</div>

						<div>
							<div class=" mb-2.5 text-sm font-medium">LiteLLM API Base URL</div>
							<div class="flex w-full">
								<div class="flex-1">
									<input
										class="w-full rounded py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none"
										placeholder="Enter LiteLLM API Base URL"
										bind:value={liteLLMAPIBase}
										autocomplete="off"
									/>
								</div>
							</div>
						</div>

						<div>
							<div class=" mb-2.5 text-sm font-medium">LiteLLM API RPM</div>
							<div class="flex w-full">
								<div class="flex-1">
									<input
										class="w-full rounded py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none"
										placeholder="Enter LiteLLM API RPM"
										bind:value={liteLLMRPM}
										autocomplete="off"
									/>
								</div>
							</div>
						</div>
					{/if}

					<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
						Not sure what to add?
						<a
							class=" text-gray-300 font-medium underline"
							href="https://litellm.vercel.app/docs/proxy/configs#quick-start"
							target="_blank"
						>
							Click here for help.
						</a>
					</div>
				</div>
			</div> -->
		</div>
	</div>
</div>
