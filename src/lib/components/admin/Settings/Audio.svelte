<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	const dispatch = createEventDispatcher();

	import { getBackendConfig } from '$lib/apis';
	import {
		getAudioConfig,
		updateAudioConfig,
		getModels as _getModels,
		getVoices as _getVoices
	} from '$lib/apis/audio';
	import { config, settings } from '$lib/stores';

	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import SelectDropdown from '$lib/components/common/SelectDropdown.svelte';

	import { TTS_RESPONSE_SPLIT } from '$lib/types';

	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let saveHandler: () => void;

	// Audio
	let TTS_OPENAI_API_BASE_URL = '';
	let TTS_OPENAI_API_KEY = '';
	let TTS_API_KEY = '';
	let TTS_ENGINE = '';
	let TTS_MODEL = '';
	let TTS_VOICE = '';
	let TTS_SPLIT_ON: TTS_RESPONSE_SPLIT = TTS_RESPONSE_SPLIT.PUNCTUATION;
	let TTS_AZURE_SPEECH_REGION = '';
	let TTS_AZURE_SPEECH_OUTPUT_FORMAT = '';

	let STT_OPENAI_API_BASE_URL = '';
	let STT_OPENAI_API_KEY = '';
	let STT_ENGINE = '';
	let STT_MODEL = '';
	let STT_WHISPER_MODEL = '';
	let STT_AZURE_API_KEY = '';
	let STT_AZURE_REGION = '';
	let STT_AZURE_LOCALES = '';
	let STT_DEEPGRAM_API_KEY = '';

	let STT_WHISPER_MODEL_LOADING = false;

	// eslint-disable-next-line no-undef
	let voices: SpeechSynthesisVoice[] = [];
	let models: Awaited<ReturnType<typeof _getModels>>['models'] = [];

	const getModels = async () => {
		if (TTS_ENGINE === '') {
			models = [];
		} else {
			const res = await _getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			).catch((e) => {
				toast.error(`${e}`);
			});

			if (res) {
				console.log(res);
				models = res.models;
			}
		}
	};

	const getVoices = async () => {
		if (TTS_ENGINE === '') {
			const getVoicesLoop = setInterval(() => {
				voices = speechSynthesis.getVoices();

				// do your loop
				if (voices.length > 0) {
					clearInterval(getVoicesLoop);
					voices.sort((a, b) => a.name.localeCompare(b.name, $i18n.resolvedLanguage));
				}
			}, 100);
		} else {
			const res = await _getVoices(localStorage.token).catch((e) => {
				toast.error(`${e}`);
			});

			if (res) {
				console.log(res);
				voices = res.voices;
				voices.sort((a, b) => a.name.localeCompare(b.name, $i18n.resolvedLanguage));
			}
		}
	};

	const updateConfigHandler = async () => {
		const res = await updateAudioConfig(localStorage.token, {
			tts: {
				OPENAI_API_BASE_URL: TTS_OPENAI_API_BASE_URL,
				OPENAI_API_KEY: TTS_OPENAI_API_KEY,
				API_KEY: TTS_API_KEY,
				ENGINE: TTS_ENGINE,
				MODEL: TTS_MODEL,
				VOICE: TTS_VOICE,
				SPLIT_ON: TTS_SPLIT_ON,
				AZURE_SPEECH_REGION: TTS_AZURE_SPEECH_REGION,
				AZURE_SPEECH_OUTPUT_FORMAT: TTS_AZURE_SPEECH_OUTPUT_FORMAT
			},
			stt: {
				OPENAI_API_BASE_URL: STT_OPENAI_API_BASE_URL,
				OPENAI_API_KEY: STT_OPENAI_API_KEY,
				ENGINE: STT_ENGINE,
				MODEL: STT_MODEL,
				WHISPER_MODEL: STT_WHISPER_MODEL,
				DEEPGRAM_API_KEY: STT_DEEPGRAM_API_KEY,
				AZURE_API_KEY: STT_AZURE_API_KEY,
				AZURE_REGION: STT_AZURE_REGION,
				AZURE_LOCALES: STT_AZURE_LOCALES
			}
		});

		if (res) {
			saveHandler();
			config.set(await getBackendConfig());
		}
	};

	const sttModelUpdateHandler = async () => {
		STT_WHISPER_MODEL_LOADING = true;
		await updateConfigHandler();
		STT_WHISPER_MODEL_LOADING = false;
	};

	onMount(async () => {
		const res = await getAudioConfig(localStorage.token);

		if (res) {
			console.log(res);
			TTS_OPENAI_API_BASE_URL = res.tts.OPENAI_API_BASE_URL;
			TTS_OPENAI_API_KEY = res.tts.OPENAI_API_KEY;
			TTS_API_KEY = res.tts.API_KEY;

			TTS_ENGINE = res.tts.ENGINE;
			TTS_MODEL = res.tts.MODEL;
			TTS_VOICE = res.tts.VOICE;

			TTS_SPLIT_ON = res.tts.SPLIT_ON || TTS_RESPONSE_SPLIT.PUNCTUATION;

			TTS_AZURE_SPEECH_OUTPUT_FORMAT = res.tts.AZURE_SPEECH_OUTPUT_FORMAT;
			TTS_AZURE_SPEECH_REGION = res.tts.AZURE_SPEECH_REGION;

			STT_OPENAI_API_BASE_URL = res.stt.OPENAI_API_BASE_URL;
			STT_OPENAI_API_KEY = res.stt.OPENAI_API_KEY;

			STT_ENGINE = res.stt.ENGINE;
			STT_MODEL = res.stt.MODEL;
			STT_WHISPER_MODEL = res.stt.WHISPER_MODEL;
			STT_AZURE_API_KEY = res.stt.AZURE_API_KEY;
			STT_AZURE_REGION = res.stt.AZURE_REGION;
			STT_AZURE_LOCALES = res.stt.AZURE_LOCALES;
			STT_DEEPGRAM_API_KEY = res.stt.DEEPGRAM_API_KEY;
		}

		await getVoices();
		await getModels();
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={async () => {
		await updateConfigHandler();
		dispatch('save');
	}}
>
	<div class="space-y-3 overflow-y-auto scrollbar-hidden h-full" style="padding-right: 4px;">
		<div class="flex flex-col gap-3" style="gap: 20px;">
			<!-- STT Settings Section -->
			<div style="background: linear-gradient(to bottom, rgba(0,0,0,0.02), transparent); border-radius: 12px; padding: 20px; border: 1px solid rgba(0,0,0,0.05);">
				<div class="mb-4 flex items-center gap-2">
					<div class="w-1 h-6 bg-orange-500 rounded-sm"></div>
					<div class="text-base font-medium text-gray-800 dark:text-gray-200 tracking-tight">
						{$i18n.t('STT Settings')}
					</div>
				</div>

				<div class="space-y-3" style="background: white; border-radius: 10px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid rgba(0,0,0,0.06);">
					<!-- Speech-to-Text Engine -->
					<div class="py-0.5 flex w-full flex-col gap-2 sm:flex-row sm:justify-between sm:items-center" style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
						<div class="self-center text-xs font-medium" style="color: #374151; font-size: 13px;">{$i18n.t('Speech-to-Text Engine')}</div>
						<div class="w-full sm:w-auto">
							<SelectDropdown
								value={STT_ENGINE}
								options={[
									{ value: '', label: $i18n.t('Whisper (Local)') },
									{ value: 'openai', label: 'OpenAI' },
									{ value: 'web', label: $i18n.t('Web API') },
									{ value: 'deepgram', label: 'Deepgram' },
									{ value: 'azure', label: 'Azure AI Speech' }
								]}
								on:change={(e) => (STT_ENGINE = e.detail.value)}
							/>
						</div>
					</div>

					<!-- Engine-specific Configuration -->
					{#if STT_ENGINE === 'openai'}
						<div style="padding: 12px; background: #f9fafb; border-radius: 8px; border: 1px solid rgba(0,0,0,0.06);">
							<div>
								<div class="mt-1 flex gap-2 mb-1" style="gap: 12px;">
									<input
										class="flex-1 w-full bg-transparent outline-hidden"
										placeholder={$i18n.t('API Base URL')}
										bind:value={STT_OPENAI_API_BASE_URL}
										required
										style="background: white; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
									/>

									<SensitiveInput placeholder={$i18n.t('API Key')} bind:value={STT_OPENAI_API_KEY} />
								</div>
							</div>

							<div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(0,0,0,0.06);">
								<div class="mb-1.5 text-sm font-medium" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">{$i18n.t('STT Model')}</div>
								<div class="flex w-full">
									<div class="flex-1">
										<input
											list="model-list"
											class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
											bind:value={STT_MODEL}
											placeholder="Select a model"
											style="background: white; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
										/>

										<datalist id="model-list">
											<option value="whisper-1" />
										</datalist>
									</div>
								</div>
							</div>
						</div>
					{:else if STT_ENGINE === 'deepgram'}
						<div style="padding: 12px; background: #f9fafb; border-radius: 8px; border: 1px solid rgba(0,0,0,0.06);">
							<div>
								<div class="mt-1 flex gap-2 mb-1">
									<SensitiveInput placeholder={$i18n.t('API Key')} bind:value={STT_DEEPGRAM_API_KEY} />
								</div>
							</div>

							<div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(0,0,0,0.06);">
								<div class="mb-1.5 text-sm font-medium" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">{$i18n.t('STT Model')}</div>
								<div class="flex w-full">
									<div class="flex-1">
										<input
											class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
											bind:value={STT_MODEL}
											placeholder="Select a model (optional)"
											style="background: white; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
										/>
									</div>
								</div>
								<div class="mt-2 mb-1 text-xs text-gray-400 dark:text-gray-500" style="line-height: 1.5; color: #6b7280;">
									{$i18n.t('Leave model field empty to use the default model.')}
									<a
										class="hover:underline dark:text-gray-200 text-gray-800"
										href="https://developers.deepgram.com/docs/models"
										target="_blank"
										style="color: #3b82f6; font-weight: 600; transition: color 0.2s;"
									>
										{$i18n.t('Click here to see available models.')}
									</a>
								</div>
							</div>
						</div>
					{:else if STT_ENGINE === 'azure'}
						<div style="padding: 12px; background: #f9fafb; border-radius: 8px; border: 1px solid rgba(0,0,0,0.06);">
							<div>
								<div class="mt-1 flex gap-2 mb-1" style="gap: 12px;">
									<SensitiveInput
										placeholder={$i18n.t('API Key')}
										bind:value={STT_AZURE_API_KEY}
										required
									/>
									<input
										class="flex-1 w-full rounded-lg py-2 pl-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
										placeholder={$i18n.t('Azure Region')}
										bind:value={STT_AZURE_REGION}
										required
										style="background: white; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
									/>
								</div>

								<div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(0,0,0,0.06);">
									<div class="mb-1.5 text-sm font-medium" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">{$i18n.t('Language Locales')}</div>
									<div class="flex w-full">
										<div class="flex-1">
											<input
												class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
												bind:value={STT_AZURE_LOCALES}
												placeholder={$i18n.t('e.g., en-US,ja-JP (leave blank for auto-detect)')}
												style="background: white; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
											/>
										</div>
									</div>
								</div>
							</div>
						</div>
					{:else if STT_ENGINE === ''}
						<div style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
							<div class="mb-1.5 text-sm font-medium" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">{$i18n.t('STT Model')}</div>

							<div class="flex w-full" style="gap: 8px;">
								<div class="flex-1 mr-2">
									<input
										class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
										placeholder={$i18n.t('Set whisper model')}
										bind:value={STT_WHISPER_MODEL}
										style="background: #f9fafb; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
									/>
								</div>

								<button
									class="px-3 py-2 bg-blue-500 hover:bg-blue-600 active:bg-blue-700 
									text-white rounded-lg transition-all duration-200 
									shadow-md hover:shadow-lg 
									flex items-center justify-center"
									on:click={() => {
										sttModelUpdateHandler();
									}}
									disabled={STT_WHISPER_MODEL_LOADING}
								>

									{#if STT_WHISPER_MODEL_LOADING}
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

							<div class="mt-2 mb-1 text-xs text-gray-400 dark:text-gray-500" style="line-height: 1.5; color: #6b7280;">
								{$i18n.t(`Open WebUI uses faster-whisper internally.`)}

								<a
									class="hover:underline dark:text-gray-200 text-gray-800"
									href="https://github.com/SYSTRAN/faster-whisper"
									target="_blank"
									style="color: #3b82f6; font-weight: 600; transition: color 0.2s;"
								>
									{$i18n.t(
										`Click here to learn more about faster-whisper and see the available models.`
									)}
								</a>
							</div>
						</div>
					{/if}
				</div>
			</div>

			<!-- TTS Settings Section -->
			<div style="background: linear-gradient(to bottom, rgba(0,0,0,0.02), transparent); border-radius: 12px; padding: 20px; border: 1px solid rgba(0,0,0,0.05);">
				<div class="mb-4 flex items-center gap-2">
					<div class="w-1 h-6 bg-orange-500 rounded-sm"></div>
					<div class="text-base font-medium text-gray-800 dark:text-gray-200 tracking-tight">
						{$i18n.t('TTS Settings')}
					</div>
				</div>

				<div class="space-y-3" style="background: white; border-radius: 10px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid rgba(0,0,0,0.06);">
					<!-- Text-to-Speech Engine -->
					<div class="py-0.5 flex w-full flex-col gap-2 sm:flex-row sm:justify-between sm:items-center" style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
						<div class="self-center text-xs font-medium" style="color: #374151; font-size: 13px;">{$i18n.t('Text-to-Speech Engine')}</div>
						<div class="w-full sm:w-auto">
							<SelectDropdown
								value={TTS_ENGINE}
								options={[
									{ value: '', label: $i18n.t('Web API') },
									{ value: 'transformers', label: `${$i18n.t('Transformers')} (${$i18n.t('Local')})` },
									{ value: 'openai', label: $i18n.t('OpenAI') },
									{ value: 'elevenlabs', label: $i18n.t('ElevenLabs') },
									{ value: 'azure', label: $i18n.t('Azure AI Speech') }
								]}
								on:change={async (e) => {
									TTS_ENGINE = e.detail.value;
									await updateConfigHandler();
									await getVoices();
									await getModels();

									if (e.detail.value === 'openai') {
										TTS_VOICE = 'alloy';
										TTS_MODEL = 'tts-1';
									} else {
										TTS_VOICE = '';
										TTS_MODEL = '';
									}
								}}
							/>
						</div>
					</div>

					<!-- Engine-specific Configuration -->
					{#if TTS_ENGINE === 'openai'}
						<div style="padding: 12px; background: #f9fafb; border-radius: 8px; border: 1px solid rgba(0,0,0,0.06);">
							<div>
								<div class="mt-1 flex gap-2 mb-1" style="gap: 12px;">
									<input
										class="flex-1 w-full bg-transparent outline-hidden"
										placeholder={$i18n.t('API Base URL')}
										bind:value={TTS_OPENAI_API_BASE_URL}
										required
										style="background: white; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
									/>

									<SensitiveInput placeholder={$i18n.t('API Key')} bind:value={TTS_OPENAI_API_KEY} />
								</div>
							</div>
						</div>
					{:else if TTS_ENGINE === 'elevenlabs'}
						<div style="padding: 12px; background: #f9fafb; border-radius: 8px; border: 1px solid rgba(0,0,0,0.06);">
							<div>
								<div class="mt-1 flex gap-2 mb-1">
									<input
										class="flex-1 w-full rounded-lg py-2 pl-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
										placeholder={$i18n.t('API Key')}
										bind:value={TTS_API_KEY}
										required
										style="background: white; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
									/>
								</div>
							</div>
						</div>
					{:else if TTS_ENGINE === 'azure'}
						<div style="padding: 12px; background: #f9fafb; border-radius: 8px; border: 1px solid rgba(0,0,0,0.06);">
							<div>
								<div class="mt-1 flex gap-2 mb-1" style="gap: 12px;">
									<input
										class="flex-1 w-full rounded-lg py-2 pl-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
										placeholder={$i18n.t('API Key')}
										bind:value={TTS_API_KEY}
										required
										style="background: white; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
									/>
									<input
										class="flex-1 w-full rounded-lg py-2 pl-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
										placeholder={$i18n.t('Azure Region')}
										bind:value={TTS_AZURE_SPEECH_REGION}
										required
										style="background: white; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
									/>
								</div>
							</div>
						</div>
					{/if}

					<!-- Voice and Model Configuration -->
					<div style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.04);">
						{#if TTS_ENGINE === ''}
							<div>
								<div class="mb-1.5 text-sm font-medium" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">{$i18n.t('TTS Voice')}</div>
								<div class="flex w-full">
									<div class="flex-1">
										<SelectDropdown
											value={TTS_VOICE}
											options={[
												{ value: '', label: $i18n.t('Default') },
												...voices.map((voice) => ({ value: voice.voiceURI, label: voice.name }))
											]}
											on:change={(e) => (TTS_VOICE = e.detail.value)}
										/>
									</div>
								</div>
							</div>
						{:else if TTS_ENGINE === 'transformers'}
							<div>
								<div class="mb-1.5 text-sm font-medium" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">{$i18n.t('TTS Model')}</div>
								<div class="flex w-full">
									<div class="flex-1">
										<input
											list="model-list"
											class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
											bind:value={TTS_MODEL}
											placeholder="CMU ARCTIC speaker embedding name"
											style="background: #f9fafb; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
										/>

										<datalist id="model-list">
											<option value="tts-1" />
										</datalist>
									</div>
								</div>
								<div class="mt-2 mb-1 text-xs text-gray-400 dark:text-gray-500" style="line-height: 1.5; color: #6b7280;">
									{$i18n.t(`Open WebUI uses SpeechT5 and CMU Arctic speaker embeddings.`)}

									To learn more about SpeechT5,

									<a
										class="hover:underline dark:text-gray-200 text-gray-800"
										href="https://github.com/microsoft/SpeechT5"
										target="_blank"
										style="color: #3b82f6; font-weight: 600; transition: color 0.2s;"
									>
										{$i18n.t(`click here`, {
											name: 'SpeechT5'
										})}.
									</a>
									To see the available CMU Arctic speaker embeddings,
									<a
										class="hover:underline dark:text-gray-200 text-gray-800"
										href="https://huggingface.co/datasets/Matthijs/cmu-arctic-xvectors"
										target="_blank"
										style="color: #3b82f6; font-weight: 600; transition: color 0.2s;"
									>
										{$i18n.t(`click here`)}.
									</a>
								</div>
							</div>
						{:else if TTS_ENGINE === 'openai'}
							<div class="flex gap-2" style="gap: 12px;">
								<div class="w-full">
									<div class="mb-1.5 text-sm font-medium" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">{$i18n.t('TTS Voice')}</div>
									<div class="flex w-full">
										<div class="flex-1">
											<input
												list="voice-list"
												class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
												bind:value={TTS_VOICE}
												placeholder="Select a voice"
												style="background: #f9fafb; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
											/>

											<datalist id="voice-list">
												{#each voices as voice}
													<option value={voice.id}>{voice.name}</option>
												{/each}
											</datalist>
										</div>
									</div>
								</div>
								<div class="w-full">
									<div class="mb-1.5 text-sm font-medium" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">{$i18n.t('TTS Model')}</div>
									<div class="flex w-full">
										<div class="flex-1">
											<input
												list="tts-model-list"
												class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
												bind:value={TTS_MODEL}
												placeholder="Select a model"
												style="background: #f9fafb; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
											/>

											<datalist id="tts-model-list">
												{#each models as model}
													<option value={model.id} class="bg-gray-50 dark:bg-gray-700" />
												{/each}
											</datalist>
										</div>
									</div>
								</div>
							</div>
						{:else if TTS_ENGINE === 'elevenlabs'}
							<div class="flex gap-2" style="gap: 12px;">
								<div class="w-full">
									<div class="mb-1.5 text-sm font-medium" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">{$i18n.t('TTS Voice')}</div>
									<div class="flex w-full">
										<div class="flex-1">
											<input
												list="voice-list"
												class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
												bind:value={TTS_VOICE}
												placeholder="Select a voice"
												style="background: #f9fafb; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
											/>

											<datalist id="voice-list">
												{#each voices as voice}
													<option value={voice.id}>{voice.name}</option>
												{/each}
											</datalist>
										</div>
									</div>
								</div>
								<div class="w-full">
									<div class="mb-1.5 text-sm font-medium" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">{$i18n.t('TTS Model')}</div>
									<div class="flex w-full">
										<div class="flex-1">
											<input
												list="tts-model-list"
												class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
												bind:value={TTS_MODEL}
												placeholder="Select a model"
												style="background: #f9fafb; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
											/>

											<datalist id="tts-model-list">
												{#each models as model}
													<option value={model.id} class="bg-gray-50 dark:bg-gray-700" />
												{/each}
											</datalist>
										</div>
									</div>
								</div>
							</div>
						{:else if TTS_ENGINE === 'azure'}
							<div class="flex gap-2" style="gap: 12px;">
								<div class="w-full">
									<div class="mb-1.5 text-sm font-medium" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">{$i18n.t('TTS Voice')}</div>
									<div class="flex w-full">
										<div class="flex-1">
											<input
												list="voice-list"
												class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
												bind:value={TTS_VOICE}
												placeholder="Select a voice"
												style="background: #f9fafb; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
											/>

											<datalist id="voice-list">
												{#each voices as voice}
													<option value={voice.id}>{voice.name}</option>
												{/each}
											</datalist>
										</div>
									</div>
								</div>
								<div class="w-full">
									<div class="mb-1.5 text-sm font-medium" style="color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px;">
										{$i18n.t('Output format')}
										<a
											href="https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-text-to-speech?tabs=streaming#audio-outputs"
											target="_blank"
											style="color: #3b82f6; font-weight: 600; margin-left: 4px;"
										>
											<small>{$i18n.t('Available list')}</small>
										</a>
									</div>
									<div class="flex w-full">
										<div class="flex-1">
											<input
												list="tts-model-list"
												class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
												bind:value={TTS_AZURE_SPEECH_OUTPUT_FORMAT}
												placeholder="Select a output format"
												style="background: #f9fafb; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; padding: 10px 14px; transition: all 0.2s;"
											/>
										</div>
									</div>
								</div>
							</div>
						{/if}
					</div>

					<!-- Response Splitting -->
					<div class="pt-0.5 flex w-full flex-col gap-2 sm:flex-row sm:justify-between sm:items-center" style="padding: 8px 0;">
						<div class="self-center text-xs font-medium" style="color: #374151; font-size: 13px;">{$i18n.t('Response splitting')}</div>
						<div class="w-full sm:w-auto">
							<SelectDropdown
								value={TTS_SPLIT_ON}
								options={Object.values(TTS_RESPONSE_SPLIT).map((split) => ({
									value: split,
									label: $i18n.t(split.charAt(0).toUpperCase() + split.slice(1))
								}))}
								on:change={(e) => (TTS_SPLIT_ON = e.detail.value)}
							/>
						</div>
					</div>
					<div class="mt-2 mb-1 text-xs text-gray-400 dark:text-gray-500" style="line-height: 1.5; color: #6b7280; background: #f3f4f6; padding: 10px 14px; border-radius: 8px; border-left: 3px solid #10b981;">
						{$i18n.t(
							"Control how message text is split for TTS requests. 'Punctuation' splits into sentences, 'paragraphs' splits into paragraphs, and 'none' keeps the message as a single string."
						)}
					</div>
				</div>
			</div>
		</div>
	</div>
	<div class="flex justify-end text-sm font-medium" style="border-top: 1px solid rgba(0,0,0,0.08); padding-top: 16px;">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-orange-600 hover:bg-orange-700 text-white transition rounded-lg"
			type="submit"
			
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form> 