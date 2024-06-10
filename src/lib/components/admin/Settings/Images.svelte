<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { config, user } from '$lib/stores';
	import {
		getImageGenerationModels,
		getDefaultImageGenerationModel,
		updateDefaultImageGenerationModel,
		getImageSize,
		getImageGenerationConfig,
		updateImageGenerationConfig,
		getImageGenerationEngineUrls,
		updateImageGenerationEngineUrls,
		updateImageSize,
		getImageSteps,
		updateImageSteps,
		getOpenAIConfig,
		updateOpenAIConfig
	} from '$lib/apis/images';
	import { getBackendConfig } from '$lib/apis';
	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	let loading = false;

	let imageGenerationEngine = '';
	let enableImageGeneration = false;

	let AUTOMATIC1111_BASE_URL = '';
	let COMFYUI_BASE_URL = '';

	let OPENAI_API_BASE_URL = '';
	let OPENAI_API_KEY = '';

	let selectedModel = '';
	let models = null;

	let imageSize = '';
	let steps = 50;

	const getModels = async () => {
		models = await getImageGenerationModels(localStorage.token).catch((error) => {
			toast.error(error);
			return null;
		});
		selectedModel = await getDefaultImageGenerationModel(localStorage.token).catch((error) => {
			return '';
		});
	};

	const updateUrlHandler = async () => {
		if (imageGenerationEngine === 'comfyui') {
			const res = await updateImageGenerationEngineUrls(localStorage.token, {
				COMFYUI_BASE_URL: COMFYUI_BASE_URL
			}).catch((error) => {
				toast.error(error);

				console.log(error);
				return null;
			});

			if (res) {
				COMFYUI_BASE_URL = res.COMFYUI_BASE_URL;

				await getModels();

				if (models) {
					toast.success($i18n.t('Server connection verified'));
				}
			} else {
				({ COMFYUI_BASE_URL } = await getImageGenerationEngineUrls(localStorage.token));
			}
		} else {
			const res = await updateImageGenerationEngineUrls(localStorage.token, {
				AUTOMATIC1111_BASE_URL: AUTOMATIC1111_BASE_URL
			}).catch((error) => {
				toast.error(error);
				return null;
			});

			if (res) {
				AUTOMATIC1111_BASE_URL = res.AUTOMATIC1111_BASE_URL;

				await getModels();

				if (models) {
					toast.success($i18n.t('Server connection verified'));
				}
			} else {
				({ AUTOMATIC1111_BASE_URL } = await getImageGenerationEngineUrls(localStorage.token));
			}
		}
	};
	const updateImageGeneration = async () => {
		const res = await updateImageGenerationConfig(
			localStorage.token,
			imageGenerationEngine,
			enableImageGeneration
		).catch((error) => {
			toast.error(error);
			return null;
		});

		if (res) {
			imageGenerationEngine = res.engine;
			enableImageGeneration = res.enabled;
		}

		if (enableImageGeneration) {
			config.set(await getBackendConfig(localStorage.token));
			getModels();
		}
	};

	onMount(async () => {
		if ($user.role === 'admin') {
			const res = await getImageGenerationConfig(localStorage.token).catch((error) => {
				toast.error(error);
				return null;
			});

			if (res) {
				imageGenerationEngine = res.engine;
				enableImageGeneration = res.enabled;
			}
			const URLS = await getImageGenerationEngineUrls(localStorage.token);

			AUTOMATIC1111_BASE_URL = URLS.AUTOMATIC1111_BASE_URL;
			COMFYUI_BASE_URL = URLS.COMFYUI_BASE_URL;

			const config = await getOpenAIConfig(localStorage.token);

			OPENAI_API_KEY = config.OPENAI_API_KEY;
			OPENAI_API_BASE_URL = config.OPENAI_API_BASE_URL;

			imageSize = await getImageSize(localStorage.token);
			steps = await getImageSteps(localStorage.token);

			if (enableImageGeneration) {
				getModels();
			}
		}
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={async () => {
		loading = true;

		if (imageGenerationEngine === 'openai') {
			await updateOpenAIConfig(localStorage.token, OPENAI_API_BASE_URL, OPENAI_API_KEY);
		}

		await updateDefaultImageGenerationModel(localStorage.token, selectedModel);

		await updateImageSize(localStorage.token, imageSize).catch((error) => {
			toast.error(error);
			return null;
		});
		await updateImageSteps(localStorage.token, steps).catch((error) => {
			toast.error(error);
			return null;
		});

		dispatch('save');
		loading = false;
	}}
>
	<div class=" space-y-3 overflow-y-scroll scrollbar-hidden">
		<div>
			<div class=" mb-1 text-sm font-medium">{$i18n.t('Image Settings')}</div>

			<div class=" py-0.5 flex w-full justify-between">
				<div class=" self-center text-xs font-medium">{$i18n.t('Image Generation Engine')}</div>
				<div class="flex items-center relative">
					<select
						class="w-fit pr-8 rounded px-2 p-1 text-xs bg-transparent outline-none text-right"
						bind:value={imageGenerationEngine}
						placeholder={$i18n.t('Select a mode')}
						on:change={async () => {
							await updateImageGeneration();
						}}
					>
						<option value="">{$i18n.t('Default (Automatic1111)')}</option>
						<option value="comfyui">{$i18n.t('ComfyUI')}</option>
						<option value="openai">{$i18n.t('Open AI (Dall-E)')}</option>
					</select>
				</div>
			</div>

			<div>
				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">
						{$i18n.t('Image Generation (Experimental)')}
					</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
						on:click={() => {
							if (imageGenerationEngine === '' && AUTOMATIC1111_BASE_URL === '') {
								toast.error($i18n.t('AUTOMATIC1111 Base URL is required.'));
								enableImageGeneration = false;
							} else if (imageGenerationEngine === 'comfyui' && COMFYUI_BASE_URL === '') {
								toast.error($i18n.t('ComfyUI Base URL is required.'));
								enableImageGeneration = false;
							} else if (imageGenerationEngine === 'openai' && OPENAI_API_KEY === '') {
								toast.error($i18n.t('OpenAI API Key is required.'));
								enableImageGeneration = false;
							} else {
								enableImageGeneration = !enableImageGeneration;
							}

							updateImageGeneration();
						}}
						type="button"
					>
						{#if enableImageGeneration === true}
							<span class="ml-2 self-center">{$i18n.t('On')}</span>
						{:else}
							<span class="ml-2 self-center">{$i18n.t('Off')}</span>
						{/if}
					</button>
				</div>
			</div>
		</div>
		<hr class=" dark:border-gray-850" />

		{#if imageGenerationEngine === ''}
			<div class=" mb-2.5 text-sm font-medium">{$i18n.t('AUTOMATIC1111 Base URL')}</div>
			<div class="flex w-full">
				<div class="flex-1 mr-2">
					<input
						class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
						placeholder={$i18n.t('Enter URL (e.g. http://127.0.0.1:7860/)')}
						bind:value={AUTOMATIC1111_BASE_URL}
					/>
				</div>
				<button
					class="px-2.5 bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition"
					type="button"
					on:click={() => {
						updateUrlHandler();
					}}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="w-4 h-4"
					>
						<path
							fill-rule="evenodd"
							d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z"
							clip-rule="evenodd"
						/>
					</svg>
				</button>
			</div>

			<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
				{$i18n.t('Include `--api` flag when running stable-diffusion-webui')}
				<a
					class=" text-gray-300 font-medium"
					href="https://github.com/AUTOMATIC1111/stable-diffusion-webui/discussions/3734"
					target="_blank"
				>
					{$i18n.t('(e.g. `sh webui.sh --api`)')}
				</a>
			</div>
		{:else if imageGenerationEngine === 'comfyui'}
			<div class=" mb-2.5 text-sm font-medium">{$i18n.t('ComfyUI Base URL')}</div>
			<div class="flex w-full">
				<div class="flex-1 mr-2">
					<input
						class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
						placeholder={$i18n.t('Enter URL (e.g. http://127.0.0.1:7860/)')}
						bind:value={COMFYUI_BASE_URL}
					/>
				</div>
				<button
					class="px-2.5 bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition"
					type="button"
					on:click={() => {
						updateUrlHandler();
					}}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="w-4 h-4"
					>
						<path
							fill-rule="evenodd"
							d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z"
							clip-rule="evenodd"
						/>
					</svg>
				</button>
			</div>
		{:else if imageGenerationEngine === 'openai'}
			<div>
				<div class=" mb-1.5 text-sm font-medium">{$i18n.t('OpenAI API Config')}</div>

				<div class="flex gap-2 mb-1">
					<input
						class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
						placeholder={$i18n.t('API Base URL')}
						bind:value={OPENAI_API_BASE_URL}
						required
					/>

					<input
						class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
						placeholder={$i18n.t('API Key')}
						bind:value={OPENAI_API_KEY}
						required
					/>
				</div>
			</div>
		{/if}

		{#if enableImageGeneration}
			<hr class=" dark:border-gray-850" />

			<div>
				<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Set Default Model')}</div>
				<div class="flex w-full">
					<div class="flex-1 mr-2">
						{#if imageGenerationEngine === 'openai' && !OPENAI_API_BASE_URL.includes('https://api.openai.com')}
							<div class="flex w-full">
								<div class="flex-1">
									<input
										list="model-list"
										class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
										bind:value={selectedModel}
										placeholder="Select a model"
									/>

									<datalist id="model-list">
										{#each models ?? [] as model}
											<option value={model.id}>{model.name}</option>
										{/each}
									</datalist>
								</div>
							</div>
						{:else}
							<select
								class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
								bind:value={selectedModel}
								placeholder={$i18n.t('Select a model')}
								required
							>
								{#if !selectedModel}
									<option value="" disabled selected>{$i18n.t('Select a model')}</option>
								{/if}
								{#each models ?? [] as model}
									<option value={model.id} class="bg-gray-100 dark:bg-gray-700">{model.name}</option
									>
								{/each}
							</select>
						{/if}
					</div>
				</div>
			</div>

			<div>
				<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Set Image Size')}</div>
				<div class="flex w-full">
					<div class="flex-1 mr-2">
						<input
							class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
							placeholder={$i18n.t('Enter Image Size (e.g. 512x512)')}
							bind:value={imageSize}
						/>
					</div>
				</div>
			</div>

			<div>
				<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Set Steps')}</div>
				<div class="flex w-full">
					<div class="flex-1 mr-2">
						<input
							class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
							placeholder={$i18n.t('Enter Number of Steps (e.g. 50)')}
							bind:value={steps}
						/>
					</div>
				</div>
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg flex flex-row space-x-1 items-center {loading
				? ' cursor-not-allowed'
				: ''}"
			type="submit"
			disabled={loading}
		>
			{$i18n.t('Save')}

			{#if loading}
				<div class="ml-2 self-center">
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
			{/if}
		</button>
	</div>
</form>
