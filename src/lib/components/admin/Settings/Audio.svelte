<script lang="ts">
	import { _alltalk, getAudioConfig, updateOpenAIAudioConfig, updateAlltalkAudioConfig, ConfigMode, updateGeneralAudioConfig } from '$lib/apis/audio';
	import { config } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { toast } from 'svelte-sonner';
	import Switch from '$lib/components/common/Switch.svelte';
	import { getBackendConfig } from '$lib/apis';
	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	// Audio

	let TTS_OPENAI_API_BASE_URL = '';
	let TTS_OPENAI_API_KEY = '';
	let TTS_ENGINE = '';
	let TTS_MODEL = '';
	let TTS_VOICE = '';

	let STT_OPENAI_API_BASE_URL = '';
	let STT_OPENAI_API_KEY = '';
	let STT_ENGINE = '';
	let STT_MODEL = '';

	let voices = [];
	let models = [];
	let nonLocalVoices = false;


	const TTSEngineConfig = {
		webapi: {
			label: 'Web API',
			voices: [],
			url: '',
			getVoices: async () => {
				const getVoicesLoop = setInterval(async () => {
					voices = await speechSynthesis.getVoices();

					// do your loop
					if (voices.length > 0) {
						clearInterval(getVoicesLoop);
					}
				}, 100);
			}
		},
		openai: {
			label: 'Open AI',
			voices: [
				{ name: 'alloy' },
				{ name: 'echo' },
				{ name: 'fable' },
				{ name: 'onyx' },
				{ name: 'nova' },
				{ name: 'shimmer' }
			],
			models: [{ name: 'tts-1' }, { name: 'tts-1-hd' }],
			url: '',
			key: '',
			getVoices: async () => {
				voices = TTSEngineConfig.openai.voices;
			},
			getModels: async () => {
				models = TTSEngineConfig.openai.models;
			}
		},
		alltalk: {
			label: 'All Talk TTS'
		}
	};

	const updateConfigHandler = async () => {
		let res = null;
		if(TTS_ENGINE === 'openai'){
			res = await updateOpenAIAudioConfig(localStorage.token, ConfigMode.TTS, {
				OPENAI_API_BASE_URL: TTS_OPENAI_API_BASE_URL,
				OPENAI_API_KEY: TTS_OPENAI_API_KEY,
			});
			res = await updateOpenAIAudioConfig(localStorage.token, ConfigMode.STT, {
				OPENAI_API_BASE_URL: STT_OPENAI_API_BASE_URL,
				OPENAI_API_KEY: STT_OPENAI_API_KEY,
			});
		}else if(TTS_ENGINE === 'alltalk'){
			res = await updateAlltalkAudioConfig(localStorage.token, _alltalk);
		}

		const sttRes = await updateGeneralAudioConfig(localStorage.token, ConfigMode.STT, {
				ENGINE: TTS_ENGINE,
				MODEL: TTS_MODEL,
				VOICE: TTS_VOICE
		});
		const ttsRes = await updateGeneralAudioConfig(localStorage.token, ConfigMode.STT, {
				ENGINE: STT_ENGINE,
				MODEL: STT_MODEL
		});

		if (sttRes && ttsRes) {
			toast.success('Audio settings have been updated successfully');
			config.set(await getBackendConfig());
		}
	};

	onMount(async () => {
		const res = await getAudioConfig(localStorage.token);

		if (res) {
			console.log(res);
			TTS_OPENAI_API_BASE_URL = res.tts.openai.OPENAI_API_BASE_URL;
			TTS_OPENAI_API_KEY = res.tts.openai.OPENAI_API_KEY;

			TTS_ENGINE = res.tts.general.ENGINE;
			TTS_MODEL = res.tts.general.MODEL;
			TTS_VOICE = res.tts.general.VOICE;

			STT_OPENAI_API_BASE_URL = res.stt.openai.OPENAI_API_BASE_URL;
			STT_OPENAI_API_KEY = res.stt.openai.OPENAI_API_KEY;

			STT_ENGINE = res.stt.general.ENGINE;
			STT_MODEL = res.stt.general.MODEL;
		}

		if (TTS_ENGINE === 'openai') {
			TTSEngineConfig[TTS_ENGINE].getVoices();
			TTSEngineConfig[TTS_ENGINE].getModels();
		} else if(TTS_ENGINE === 'alltalk'){
			await _alltalk.setup();
			//model = _alltalk.currentModel;
			console.log("alltalk model: ", _alltalk.currentModel);
		} else {
			TTSEngineConfig.webapi.getVoices();
		}
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={async () => {
		await updateConfigHandler();
		dispatch('save');
	}}
>
	<div class=" space-y-3 overflow-y-scroll scrollbar-hidden h-full">
		<div class="flex flex-col gap-3">
			<div>
				<div class=" mb-1 text-sm font-medium">{$i18n.t('STT Settings')}</div>

				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">{$i18n.t('Speech-to-Text Engine')}</div>
					<div class="flex items-center relative">
						<select
							class="dark:bg-gray-900 w-fit pr-8 rounded px-2 p-1 text-xs bg-transparent outline-none text-right"
							bind:value={STT_ENGINE}
							placeholder="Select an engine"
						>
							<option value="">{$i18n.t('Whisper (Local)')}</option>
							<option value="openai">OpenAI</option>
							<option value="web">{$i18n.t('Web API')}</option>
						</select>
					</div>
				</div>

				{#if STT_ENGINE === 'openai'}
					<div>
						<div class="mt-1 flex gap-2 mb-1">
							<input
								class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
								placeholder={$i18n.t('API Base URL')}
								bind:value={STT_OPENAI_API_BASE_URL}
								required
							/>

							<input
								class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
								placeholder={$i18n.t('API Key')}
								bind:value={STT_OPENAI_API_KEY}
								required
							/>
						</div>
					</div>

					<hr class=" dark:border-gray-850 my-2" />

					<div>
						<div class=" mb-1.5 text-sm font-medium">{$i18n.t('STT Model')}</div>
						<div class="flex w-full">
							<div class="flex-1">
								<input
									list="model-list"
									class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
									bind:value={STT_MODEL}
									placeholder="Select a model"
								/>

								<datalist id="model-list">
									<option value="whisper-1" />
								</datalist>
							</div>
						</div>
					</div>
				{/if}
			</div>

			<hr class=" dark:border-gray-800" />

			<div>
				<div class=" mb-1 text-sm font-medium">{$i18n.t('TTS Settings')}</div>

				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">{$i18n.t('Text-to-Speech Engine')}</div>
					<div class="flex items-center relative">
						<select
							class=" dark:bg-gray-900 w-fit pr-8 rounded px-2 p-1 text-xs bg-transparent outline-none text-right"
							bind:value={TTS_ENGINE}
							placeholder="Select a mode"
							on:change={async (e) => {
								if (TTS_ENGINE === 'openai') {
									TTSEngineConfig.openai.getVoices();
									TTS_VOICE = 'alloy';
									TTS_MODEL = 'tts-1';
								} else if(TTS_ENGINE === 'alltalk'){
									await _alltalk.getVoices();
									TTS_VOICE = _alltalk.currentVoice;
									await _alltalk.getModels();
									console.log("alltalk model 2: ", _alltalk.currentModel);
									TTS_MODEL = _alltalk.currentModel;
								}  else {
									TTSEngineConfig.webapi.getVoices();
									TTS_VOICE = '';
								}
							}}
						>
							{#each Object.keys(TTSEngineConfig) as engineName}
								<option value="{engineName}">{$i18n.t(TTSEngineConfig[engineName].label)}</option>
							{/each}
						</select>
					</div>
				</div>

				{#if TTS_ENGINE === 'openai'}
					<div>
						<div class="mt-1 flex gap-2 mb-1">
							<input
								class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
								placeholder={$i18n.t('API Base URL')}
								bind:value={TTS_OPENAI_API_BASE_URL}
								required
							/>

							<input
								class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
								placeholder={$i18n.t('API Key')}
								bind:value={TTS_OPENAI_API_KEY}
								required
							/>
						</div>
					</div>
				{:else if TTS_ENGINE === 'alltalk'}
					<div class="flex w-full gap-2">
						<div class="w-full gap-2">
							<input
								class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
								placeholder={$i18n.t('API Base URL')}
								bind:value={_alltalk.baseUrl}
								required
							/>
						</div>
						<Tooltip content="Verify connection" className="self-start mt-0.5">
							<button
								class="self-center p-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-900 dark:hover:bg-gray-850 rounded-lg transition"
								on:click={async () => {
									const isReady = await _alltalk.isReadyCheck();
									if (isReady) {
										toast.success($i18n.t('Server connection verified'));
									} else {
										toast.error($i18n.t('Server connection failed'));
									}
								}}
								type="button"
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
						</Tooltip>
					</div>
				{/if}

				<hr class=" dark:border-gray-850 my-2" />

				{#if TTS_ENGINE === ''}
					<div>
						<div class=" mb-1.5 text-sm font-medium">{$i18n.t('TTS Voice')}</div>
						<div class="flex w-full">
							<div class="flex-1">
								<select
									class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
									bind:value={TTS_VOICE}
								>
									<option value="" selected={TTS_VOICE !== ''}>{$i18n.t('Default')}</option>
									{#each voices as voice}
										<option
											value={voice.voiceURI}
											class="bg-gray-100 dark:bg-gray-700"
											selected={TTS_VOICE === voice.voiceURI}>{voice.name}</option
										>
									{/each}
								</select>
							</div>
						</div>
					</div>
				{:else if TTS_ENGINE === 'openai'}
					<div class=" flex gap-2">
						<div class="w-full">
							<div class=" mb-1.5 text-sm font-medium">{$i18n.t('TTS Voice')}</div>
							<div class="flex w-full">
								<div class="flex-1">
									<input
										list="voice-list"
										class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
										bind:value={TTS_VOICE}
										placeholder="Select a voice"
									/>

									<datalist id="voice-list">
										{#each voices as voice}
											<option value={voice.name} />
										{/each}
									</datalist>
								</div>
							</div>
						</div>
						<div class="w-full">
							<div class=" mb-1.5 text-sm font-medium">{$i18n.t('TTS Model')}</div>
							<div class="flex w-full">
								<div class="flex-1">
									<input
										list="model-list"
										class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
										bind:value={TTS_MODEL}
										placeholder="Select a model"
									/>

									<datalist id="model-list">
										{#each models as model}
											<option value={model.name} />
										{/each}
									</datalist>
								</div>
							</div>
						</div>
					</div>
				{:else if TTS_ENGINE === 'alltalk'}
					<div>
						<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Set Voice')}</div>
						<div class="flex w-full gap-2">
							<div class="w-full gap-2">
								<input
									list="voice-list"
									class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
									bind:value={_alltalk.currentVoice}
									placeholder="Select a voice"
								/>

								<datalist id="voice-list">
									{#each _alltalk?.voicesList as voice}
										<option value={voice} />
									{/each}
								</datalist>
							</div>
							<Tooltip content="Preview voice" className="self-start mt-0.5">
								<button
									class="self-center p-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-900 dark:hover:bg-gray-850 rounded-lg transition"
									on:click={() => {
										_alltalk.getPreviewVoice(_alltalk.currentVoice);
									}}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="2.3"
										stroke="currentColor"
										class="w-4 h-4"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
										/>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M15.91 11.672a.375.375 0 0 1 0 .656l-5.603 3.113a.375.375 0 0 1-.557-.328V8.887c0-.286.307-.466.557-.327l5.603 3.112Z"
										/>
									</svg>
								</button>
							</Tooltip>
						</div>
					</div>
					<div>
						<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Set Model')}</div>
						<div class="flex w-full">
							<div class="flex-1">
								<input
									list="model-list"
									class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
									bind:value={_alltalk.currentModel}
									placeholder="Select a model"
								/>

								<datalist id="model-list">
									{#each _alltalk?.modelList as model}
										<option value={model} />
									{/each}
								</datalist>
							</div>
						</div>
					</div>
					<div class=" py-0.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Deepspeed status')}
						</div>

						<button
							class="p-1 px-3 text-xs flex rounded transition"
							on:click={() => {
								_alltalk.useDeepSpeed = !_alltalk.useDeepSpeed;
							}}
							type="button"
						>
							{#if _alltalk.useDeepSpeed === true}
								<span class="ml-2 self-center">{$i18n.t('On')}</span>
							{:else}
								<span class="ml-2 self-center">{$i18n.t('Off')}</span>
							{/if}
						</button>
					</div>
					<div class=" py-0.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Use low vram mode')}
						</div>

						<button
							class="p-1 px-3 text-xs flex rounded transition"
							on:click={() => {
								_alltalk.useLowVRAM = !_alltalk.useLowVRAM;
							}}
							type="button"
						>
							{#if _alltalk.useLowVRAM === true}
								<span class="ml-2 self-center">{$i18n.t('On')}</span>
							{:else}
								<span class="ml-2 self-center">{$i18n.t('Off')}</span>
							{/if}
						</button>
					</div>
					<div class=" py-0.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Use streaming mode')}
						</div>

						<button
							class="p-1 px-3 text-xs flex rounded transition"
							on:click={() => {
								_alltalk.useStreamingMode = !_alltalk.useStreamingMode;
							}}
							type="button"
						>
							{#if _alltalk.useStreamingMode === true}
								<span class="ml-2 self-center">{$i18n.t('On')}</span>
							{:else}
								<span class="ml-2 self-center">{$i18n.t('Off')}</span>
							{/if}
						</button>
					</div>
					<div class=" py-0.5 flex w-full justify-between">
						<div class=" self-center text-xs font-medium">
							{$i18n.t('Enable Narrator')}
						</div>

						<button
							class="p-1 px-3 text-xs flex rounded transition"
							on:click={() => {
								_alltalk.useNarrator = !_alltalk.useNarrator;
							}}
							type="button"
						>
							{#if _alltalk.useNarrator === true}
								<span class="ml-2 self-center">{$i18n.t('On')}</span>
							{:else}
								<span class="ml-2 self-center">{$i18n.t('Off')}</span>
							{/if}
						</button>
					</div>
					{#if _alltalk.useNarrator === true}
						<div>
							<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Set Narrator Voice')}</div>
							<div class="flex w-full gap-2">
								<div class="w-full gap-2">
									<input
										list="voice-list"
										class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
										bind:value={_alltalk.narratorVoice}
										placeholder="Select a voice"
									/>

									<datalist id="voice-list">
										{#each _alltalk?.voicesList as voice}
											<option value={voice} />
										{/each}
									</datalist>
								</div>
							</div>
						</div>
					{/if}
				{/if}
			</div>
		</div>
	</div>
	<div class="flex justify-end text-sm font-medium">
		<button
			class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
