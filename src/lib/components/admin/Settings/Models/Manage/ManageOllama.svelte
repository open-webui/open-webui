<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { WEBUI_NAME, models, MODEL_DOWNLOAD_POOL, user, config, settings } from '$lib/stores';
	import { splitStream } from '$lib/utils';

	import {
		createModel,
		deleteModel,
		downloadModel,
		getOllamaUrls,
		getOllamaVersion,
		pullModel,
		uploadModel,
		getOllamaConfig,
		getOllamaModels
	} from '$lib/apis/ollama';
	import { getModels } from '$lib/apis';

	import Modal from '$lib/components/common/Modal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ModelDeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	let modelUploadInputElement: HTMLInputElement;
	let showModelDeleteConfirm = false;

	let loading = true;

	// Models
	export let urlIdx: number | null = null;

	let ollamaModels = [];

	let updateModelId = null;
	let updateProgress = null;
	let updateModelsControllers = {};
	let updateCancelled = false;
	let showExperimentalOllama = false;

	const MAX_PARALLEL_DOWNLOADS = 3;

	let modelLoading = false;
	let modelTag = '';

	let createModelLoading = false;
	let createModelName = '';
	let createModelObject = '';

	let createModelDigest = '';
	let createModelPullProgress = null;

	let digest = '';
	let pullProgress = null;

	let modelUploadMode = 'file';
	let modelInputFile: File[] | null = null;
	let modelFileUrl = '';
	let modelFileContent = `TEMPLATE """{{ .System }}\nUSER: {{ .Prompt }}\nASSISTANT: """\nPARAMETER num_ctx 4096\nPARAMETER stop "</s>"\nPARAMETER stop "USER:"\nPARAMETER stop "ASSISTANT:"`;
	let modelFileDigest = '';

	let uploadProgress = null;
	let uploadMessage = '';

	let deleteModelTag = '';

	const updateModelsHandler = async () => {
		updateCancelled = false;
		toast.info('Checking for model updates...');

		for (const model of ollamaModels) {
			if (updateCancelled) {
				break;
			}

			console.debug(model);

			updateModelId = model.id;
			const [res, controller] = await pullModel(localStorage.token, model.id, urlIdx).catch(
				(error) => {
					if (error.name !== 'AbortError') {
						toast.error(`${error}`);
					}
					return [null, null];
				}
			);

			updateModelsControllers = {
				...updateModelsControllers,
				[model.id]: controller
			};

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

								console.log(data);
								if (data.error) {
									throw data.error;
								}
								if (data.detail) {
									throw data.detail;
								}
								if (data.status) {
									if (data.digest) {
										updateProgress = 0;
										if (data.completed) {
											updateProgress = Math.round((data.completed / data.total) * 1000) / 10;
										} else {
											updateProgress = 100;
										}
									}
								}
							}
						}
					} catch (err) {
						if (err.name !== 'AbortError') {
							console.error(err);
						}
						break;
					}
				}
			}

			delete updateModelsControllers[model.id];
			updateModelsControllers = { ...updateModelsControllers };
		}

		if (updateCancelled) {
			toast.info('Model update cancelled');
		} else {
			toast.success('All models are up to date');
		}
		updateModelId = null;
		updateProgress = null;
	};

	const pullModelHandler = async () => {
		const sanitizedModelTag = modelTag.trim().replace(/^ollama\s+(run|pull)\s+/, '');
		console.log($MODEL_DOWNLOAD_POOL);
		if ($MODEL_DOWNLOAD_POOL[sanitizedModelTag]) {
			toast.error(
				$i18n.t(`Model '{{modelTag}}' is already in queue for downloading.`, {
					modelTag: sanitizedModelTag
				})
			);
			return;
		}
		if (Object.keys($MODEL_DOWNLOAD_POOL).length === MAX_PARALLEL_DOWNLOADS) {
			toast.error(
				$i18n.t('Maximum of 3 models can be downloaded simultaneously. Please try again later.')
			);
			return;
		}

		modelLoading = true;
		const [res, controller] = await pullModel(localStorage.token, sanitizedModelTag, urlIdx).catch(
			(error) => {
				if (error.name !== 'AbortError') {
					toast.error(`${error}`);
				}
				return [null, null];
			}
		);

		if (res) {
			const reader = res.body
				.pipeThrough(new TextDecoderStream())
				.pipeThrough(splitStream('\n'))
				.getReader();

			MODEL_DOWNLOAD_POOL.set({
				...$MODEL_DOWNLOAD_POOL,
				[sanitizedModelTag]: {
					...$MODEL_DOWNLOAD_POOL[sanitizedModelTag],
					abortController: controller,
					reader,
					done: false
				}
			});

			while (true) {
				try {
					const { value, done } = await reader.read();
					if (done) break;

					let lines = value.split('\n');

					for (const line of lines) {
						if (line !== '') {
							let data = JSON.parse(line);
							console.log(data);
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

									MODEL_DOWNLOAD_POOL.set({
										...$MODEL_DOWNLOAD_POOL,
										[sanitizedModelTag]: {
											...$MODEL_DOWNLOAD_POOL[sanitizedModelTag],
											pullProgress: downloadProgress,
											digest: data.digest
										}
									});
								} else {
									MODEL_DOWNLOAD_POOL.set({
										...$MODEL_DOWNLOAD_POOL,
										[sanitizedModelTag]: {
											...$MODEL_DOWNLOAD_POOL[sanitizedModelTag],
											done: data.status === 'success'
										}
									});
								}
							}
						}
					}
				} catch (err) {
					if (err.name !== 'AbortError') {
						console.error(err);
						if (typeof err !== 'string') {
							err = err.message;
						}

						toast.error(`${err}`);
						// opts.callback({ success: false, error, modelName: opts.modelName });
					} else {
						break;
					}
				}
			}

			console.log($MODEL_DOWNLOAD_POOL[sanitizedModelTag]);

			if ($MODEL_DOWNLOAD_POOL[sanitizedModelTag]?.done) {
				toast.success(
					$i18n.t(`Model '{{modelName}}' has been successfully downloaded.`, {
						modelName: sanitizedModelTag
					})
				);

				models.set(
					await getModels(
						localStorage.token,
						$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
					)
				);
			} else {
				toast.error($i18n.t('Download canceled'));
			}

			delete $MODEL_DOWNLOAD_POOL[sanitizedModelTag];

			MODEL_DOWNLOAD_POOL.set({
				...$MODEL_DOWNLOAD_POOL
			});
		}

		modelTag = '';
		modelLoading = false;
	};

	const uploadModelHandler = async () => {
		modelLoading = true;

		let uploaded = false;
		let fileResponse = null;
		let name = '';

		if (modelUploadMode === 'file') {
			const file = modelInputFile ? modelInputFile[0] : null;

			if (file) {
				uploadMessage = 'Uploading...';

				fileResponse = await uploadModel(localStorage.token, file, urlIdx).catch((error) => {
					toast.error(`${error}`);
					return null;
				});
			}
		} else {
			uploadProgress = 0;
			fileResponse = await downloadModel(localStorage.token, modelFileUrl, urlIdx).catch(
				(error) => {
					toast.error(`${error}`);
					return null;
				}
			);
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
								if (uploadMessage) {
									uploadMessage = '';
								}
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
				} catch (err) {
					console.error(err);
				}
			}
		} else {
			const error = await fileResponse?.json();
			toast.error(error?.detail ?? error);
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
					} catch (err) {
						console.error(err);
						toast.error(`${err}`);
					}
				}
			}
		}

		modelFileUrl = '';

		if (modelUploadInputElement) {
			modelUploadInputElement.value = '';
		}
		modelInputFile = null;
		modelLoading = false;
		uploadProgress = null;

		models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			)
		);
	};

	const deleteModelHandler = async () => {
		const res = await deleteModel(localStorage.token, deleteModelTag, urlIdx).catch((error) => {
			toast.error(`${error}`);
		});

		if (res) {
			toast.success($i18n.t(`Deleted {{deleteModelTag}}`, { deleteModelTag }));
		}

		deleteModelTag = '';
		models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			)
		);

		ollamaModels = await getOllamaModels(localStorage.token, urlIdx).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
	};

	const cancelUpdateModelHandler = async (model: string) => {
		const controller = updateModelsControllers[model];
		if (controller) {
			controller.abort();
			updateCancelled = true;
		}
	};

	const cancelModelPullHandler = async (model: string) => {
		const { reader, abortController } = $MODEL_DOWNLOAD_POOL[model];
		if (abortController) {
			abortController.abort();
		}
		if (reader) {
			await reader.cancel();
			delete $MODEL_DOWNLOAD_POOL[model];
			MODEL_DOWNLOAD_POOL.set({
				...$MODEL_DOWNLOAD_POOL
			});
			await deleteModel(localStorage.token, model);
			toast.success($i18n.t('{{model}} download has been canceled', { model: model }));
		}
	};

	const createModelHandler = async () => {
		createModelLoading = true;

		let modelObject = {};
		// parse createModelObject
		try {
			modelObject = JSON.parse(createModelObject);
		} catch (error) {
			toast.error(`${error}`);
			createModelLoading = false;
			return;
		}

		const res = await createModel(
			localStorage.token,
			{
				model: createModelName,
				...modelObject
			},
			urlIdx
		).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

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
										createModelDigest = data.digest;

										if (data.completed) {
											createModelPullProgress =
												Math.round((data.completed / data.total) * 1000) / 10;
										} else {
											createModelPullProgress = 100;
										}
									}
								}
							}
						}
					}
				} catch (err) {
					console.error(err);
					toast.error(`${err}`);
				}
			}
		}

		models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			)
		);

		createModelLoading = false;

		createModelName = '';
		createModelObject = '';
		createModelDigest = '';
		createModelPullProgress = null;
	};

	const init = async () => {
		loading = true;
		ollamaModels = await getOllamaModels(localStorage.token, urlIdx).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (ollamaModels) {
			loading = false;
		}
	};

	$: if (urlIdx !== null) {
		init();
	}
</script>

<ModelDeleteConfirmDialog
	bind:show={showModelDeleteConfirm}
	on:confirm={() => {
		deleteModelHandler();
	}}
/>

{#if !loading}
	<div class=" flex flex-col w-full">
		<div>
			<div class="space-y-2">
				<div>
					<div class=" mb-2 text-sm font-medium flex items-center gap-1.5">
						<div>
							{$i18n.t('Pull a model from Ollama.com')}
						</div>

						<div>
							<Tooltip content="Update All Models" placement="top">
								<button
									class="flex gap-2 items-center bg-transparent rounded-lg transition"
									on:click={() => {
										updateModelsHandler();
									}}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 16 16"
										fill="currentColor"
										class="w-4 h-4"
									>
										<path
											d="M7 1a.75.75 0 0 1 .75.75V6h-1.5V1.75A.75.75 0 0 1 7 1ZM6.25 6v2.94L5.03 7.72a.75.75 0 0 0-1.06 1.06l2.5 2.5a.75.75 0 0 0 1.06 0l2.5-2.5a.75.75 0 1 0-1.06-1.06L7.75 8.94V6H10a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h2.25Z"
										/>
										<path
											d="M4.268 14A2 2 0 0 0 6 15h6a2 2 0 0 0 2-2v-3a2 2 0 0 0-1-1.732V11a3 3 0 0 1-3 3H4.268Z"
										/>
									</svg>
								</button>
							</Tooltip>
						</div>
					</div>
					<div class="flex w-full">
						<div class="flex-1 mr-2">
							<input
								class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
								placeholder={$i18n.t('Enter model tag (e.g. {{modelTag}})', {
									modelTag: 'mistral:7b'
								})}
								bind:value={modelTag}
							/>
						</div>
						<Tooltip content={$i18n.t('Pull Model')} placement="top">
							<button
								class="px-2.5 bg-gray-50 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition"
								on:click={() => {
									pullModelHandler();
								}}
								disabled={modelLoading || modelTag.trim() === ''}
							>
								{#if modelLoading}
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
						</Tooltip>
					</div>

					<div class="mt-2 mb-1 text-xs text-gray-400 dark:text-gray-500">
						{$i18n.t('To access the available model names for downloading,')}
						<a
							class=" text-gray-500 dark:text-gray-300 font-medium underline"
							href="https://ollama.com/library"
							target="_blank">{$i18n.t('click here.')}</a
						>
					</div>

					{#if updateModelId}
						<div class="text-xs flex justify-between items-center">
							<div>Updating "{updateModelId}" {updateProgress ? `(${updateProgress}%)` : ''}</div>

							<Tooltip content={$i18n.t('Cancel')}>
								<button
									class="text-gray-800 dark:text-gray-100"
									on:click={() => {
										cancelUpdateModelHandler(updateModelId);
									}}
								>
									<svg
										class="w-4 h-4 text-gray-800 dark:text-white"
										aria-hidden="true"
										xmlns="http://www.w3.org/2000/svg"
										width="24"
										height="24"
										fill="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											stroke="currentColor"
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M6 18 17.94 6M18 18 6.06 6"
										/>
									</svg>
								</button>
							</Tooltip>
						</div>
					{/if}

					{#if Object.keys($MODEL_DOWNLOAD_POOL).length > 0}
						{#each Object.keys($MODEL_DOWNLOAD_POOL) as model}
							{#if 'pullProgress' in $MODEL_DOWNLOAD_POOL[model]}
								<div class="flex flex-col">
									<div class="font-medium mb-1">{model}</div>
									<div class="">
										<div class="flex flex-row justify-between space-x-4 pr-2">
											<div class=" flex-1">
												<div
													class="dark:bg-gray-600 bg-gray-500 text-xs font-medium text-gray-100 text-center p-0.5 leading-none rounded-full"
													style="width: {Math.max(
														15,
														$MODEL_DOWNLOAD_POOL[model].pullProgress ?? 0
													)}%"
												>
													{$MODEL_DOWNLOAD_POOL[model].pullProgress ?? 0}%
												</div>
											</div>

											<Tooltip content={$i18n.t('Cancel')}>
												<button
													class="text-gray-800 dark:text-gray-100"
													on:click={() => {
														cancelModelPullHandler(model);
													}}
												>
													<svg
														class="w-4 h-4 text-gray-800 dark:text-white"
														aria-hidden="true"
														xmlns="http://www.w3.org/2000/svg"
														width="24"
														height="24"
														fill="currentColor"
														viewBox="0 0 24 24"
													>
														<path
															stroke="currentColor"
															stroke-linecap="round"
															stroke-linejoin="round"
															stroke-width="2"
															d="M6 18 17.94 6M18 18 6.06 6"
														/>
													</svg>
												</button>
											</Tooltip>
										</div>
										{#if 'digest' in $MODEL_DOWNLOAD_POOL[model]}
											<div class="mt-1 text-xs dark:text-gray-500" style="font-size: 0.5rem;">
												{$MODEL_DOWNLOAD_POOL[model].digest}
											</div>
										{/if}
									</div>
								</div>
							{/if}
						{/each}
					{/if}
				</div>

				<div>
					<div class=" mb-2 text-sm font-medium">{$i18n.t('Delete a model')}</div>
					<div class="flex w-full">
						<div
							class="flex-1 mr-2 pr-1.5 rounded-lg bg-gray-50 dark:text-gray-300 dark:bg-gray-850"
						>
							<select
								class="w-full py-2 px-4 text-sm outline-hidden bg-transparent"
								bind:value={deleteModelTag}
								placeholder={$i18n.t('Select a model')}
							>
								<option value="" disabled selected>{$i18n.t('Select a model')}</option>

								{#each ollamaModels as model}
									<option value={model.id} class="bg-gray-50 dark:bg-gray-700"
										>{model.name + ' (' + (model.size / 1024 ** 3).toFixed(1) + ' GB)'}</option
									>
								{/each}
							</select>
						</div>
						<Tooltip content={$i18n.t('Delete Model')} placement="top">
							<button
								class="px-2.5 bg-gray-50 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition"
								on:click={() => {
									showModelDeleteConfirm = true;
								}}
								disabled={deleteModelTag === ''}
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
						</Tooltip>
					</div>
				</div>

				<div>
					<div class=" mb-2 text-sm font-medium">{$i18n.t('Create a model')}</div>
					<div class="flex w-full">
						<div class="flex-1 mr-2 flex flex-col gap-2">
							<input
								class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
								placeholder={$i18n.t('Enter model tag (e.g. {{modelTag}})', {
									modelTag: 'my-modelfile'
								})}
								bind:value={createModelName}
								disabled={createModelLoading}
							/>

							<textarea
								bind:value={createModelObject}
								class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-100 dark:bg-gray-850 outline-hidden resize-none scrollbar-hidden"
								rows="6"
								placeholder={`e.g. {"model": "my-modelfile", "from": "ollama:7b"})`}
								disabled={createModelLoading}
							/>
						</div>

						<div class="flex self-start">
							<Tooltip content={$i18n.t('Create Model')} placement="top">
								<button
									class="px-2.5 py-2.5 bg-gray-50 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition disabled:cursor-not-allowed"
									on:click={() => {
										createModelHandler();
									}}
									disabled={createModelLoading ||
										createModelName.trim() === '' ||
										createModelObject.trim() === ''}
								>
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
								</button>
							</Tooltip>
						</div>
					</div>

					{#if createModelDigest !== ''}
						<div class="flex flex-col mt-1">
							<div class="font-medium mb-1">{createModelTag}</div>
							<div class="">
								<div class="flex flex-row justify-between space-x-4 pr-2">
									<div class=" flex-1">
										<div
											class="dark:bg-gray-600 bg-gray-500 text-xs font-medium text-gray-100 text-center p-0.5 leading-none rounded-full"
											style="width: {Math.max(15, createModelPullProgress ?? 0)}%"
										>
											{createModelPullProgress ?? 0}%
										</div>
									</div>
								</div>
								{#if createModelDigest}
									<div class="mt-1 text-xs dark:text-gray-500" style="font-size: 0.5rem;">
										{createModelDigest}
									</div>
								{/if}
							</div>
						</div>
					{/if}
				</div>

				<div class="pt-1">
					<div class="flex justify-between items-center text-xs">
						<div class=" text-sm font-medium">{$i18n.t('Experimental')}</div>
						<button
							class=" text-xs font-medium text-gray-500"
							type="button"
							on:click={() => {
								showExperimentalOllama = !showExperimentalOllama;
							}}>{showExperimentalOllama ? $i18n.t('Hide') : $i18n.t('Show')}</button
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
							<div class="  text-sm font-medium">{$i18n.t('Upload a GGUF model')}</div>

							<button
								class="p-1 px-3 text-xs flex rounded-sm transition"
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
									<span class="ml-2 self-center">{$i18n.t('File Mode')}</span>
								{:else}
									<span class="ml-2 self-center">{$i18n.t('URL Mode')}</span>
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
											accept=".gguf,.safetensors"
											required
											hidden
										/>

										<button
											type="button"
											class="w-full rounded-lg text-left py-2 px-4 bg-gray-50 dark:text-gray-300 dark:bg-gray-850"
											on:click={() => {
												modelUploadInputElement.click();
											}}
										>
											{#if modelInputFile && modelInputFile.length > 0}
												{modelInputFile[0].name}
											{:else}
												{$i18n.t('Click here to select')}
											{/if}
										</button>
									</div>
								{:else}
									<div class="flex-1 {modelFileUrl !== '' ? 'mr-2' : ''}">
										<input
											class="w-full rounded-lg text-left py-2 px-4 bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden {modelFileUrl !==
											''
												? 'mr-2'
												: ''}"
											type="url"
											required
											bind:value={modelFileUrl}
											placeholder={$i18n.t('Type Hugging Face Resolve (Download) URL')}
										/>
									</div>
								{/if}
							</div>

							{#if (modelUploadMode === 'file' && modelInputFile && modelInputFile.length > 0) || (modelUploadMode === 'url' && modelFileUrl !== '')}
								<Tooltip content={$i18n.t('Upload Model')} placement="top">
									<button
										class="px-2.5 bg-gray-50 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg disabled:cursor-not-allowed transition"
										type="submit"
										disabled={modelLoading}
									>
										{#if modelLoading}
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
													d="M7.25 10.25a.75.75 0 0 0 1.5 0V4.56l2.22 2.22a.75.75 0 1 0 1.06-1.06l-3.5-3.5a.75.75 0 0 0-1.06 0l-3.5 3.5a.75.75 0 0 0 1.06 1.06l2.22-2.22v5.69Z"
												/>
												<path
													d="M3.5 9.75a.75.75 0 0 0-1.5 0v1.5A2.75 2.75 0 0 0 4.75 14h6.5A2.75 2.75 0 0 0 14 11.25v-1.5a.75.75 0 0 0-1.5 0v1.5c0 .69-.56 1.25-1.25 1.25h-6.5c-.69 0-1.25-.56-1.25-1.25v-1.5Z"
												/>
											</svg>
										{/if}
									</button>
								</Tooltip>
							{/if}
						</div>

						{#if (modelUploadMode === 'file' && modelInputFile && modelInputFile.length > 0) || (modelUploadMode === 'url' && modelFileUrl !== '')}
							<div>
								<div>
									<div class=" my-2.5 text-sm font-medium">
										{$i18n.t('Modelfile Content')}
									</div>
									<textarea
										bind:value={modelFileContent}
										class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-100 dark:bg-gray-850 outline-hidden resize-none"
										rows="6"
									/>
								</div>
							</div>
						{/if}
						<div class=" mt-1 text-xs text-gray-400 dark:text-gray-500">
							{$i18n.t('To access the GGUF models available for downloading,')}
							<a
								class=" text-gray-500 dark:text-gray-300 font-medium underline"
								href="https://huggingface.co/models?search=gguf"
								target="_blank">{$i18n.t('click here.')}</a
							>
						</div>

						{#if uploadMessage}
							<div class="mt-2">
								<div class=" mb-2 text-xs">{$i18n.t('Upload Progress')}</div>

								<div class="w-full rounded-full dark:bg-gray-800">
									<div
										class="dark:bg-gray-600 bg-gray-500 text-xs font-medium text-gray-100 text-center p-0.5 leading-none rounded-full"
										style="width: 100%"
									>
										{uploadMessage}
									</div>
								</div>
								<div class="mt-1 text-xs dark:text-gray-500" style="font-size: 0.5rem;">
									{modelFileDigest}
								</div>
							</div>
						{:else if uploadProgress !== null}
							<div class="mt-2">
								<div class=" mb-2 text-xs">{$i18n.t('Upload Progress')}</div>

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
	</div>
{:else if ollamaModels === null}
	<div class="flex justify-center items-center w-full h-full text-xs py-3">
		{$i18n.t('Failed to fetch models')}
	</div>
{:else}
	<div class="flex justify-center items-center w-full h-full py-3">
		<Spinner className="size-5" />
	</div>
{/if}
