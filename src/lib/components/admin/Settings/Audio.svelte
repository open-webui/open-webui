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

	import Spinner from '$lib/components/common/Spinner.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';

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
	let TTS_AZURE_SPEECH_BASE_URL = '';
	let TTS_AZURE_SPEECH_OUTPUT_FORMAT = '';

	let STT_OPENAI_API_BASE_URL = '';
	let STT_OPENAI_API_KEY = '';
	let STT_ENGINE = '';
	let STT_MODEL = '';
	let STT_SUPPORTED_CONTENT_TYPES = '';
	let STT_WHISPER_MODEL = '';
	let STT_AZURE_API_KEY = '';
	let STT_AZURE_REGION = '';
	let STT_AZURE_LOCALES = '';
	let STT_AZURE_BASE_URL = '';
	let STT_AZURE_MAX_SPEAKERS = '';
	let STT_DEEPGRAM_API_KEY = '';

	let STT_WHISPER_MODEL_LOADING = false;

	// eslint-disable-next-line no-undef
	let voices: SpeechSynthesisVoice[] = [];
	let models: Awaited<ReturnType<typeof _getModels>>['models'] = [];

	// Connection testing state
	let connectionTesting = false;
	let connectionStatus = { success: false, message: '', tested: false };

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
				AZURE_SPEECH_BASE_URL: TTS_AZURE_SPEECH_BASE_URL,
				AZURE_SPEECH_OUTPUT_FORMAT: TTS_AZURE_SPEECH_OUTPUT_FORMAT
			},
			stt: {
				OPENAI_API_BASE_URL: STT_OPENAI_API_BASE_URL,
				OPENAI_API_KEY: STT_OPENAI_API_KEY,
				ENGINE: STT_ENGINE,
				MODEL: STT_MODEL,
				SUPPORTED_CONTENT_TYPES: STT_SUPPORTED_CONTENT_TYPES.split(','),
				WHISPER_MODEL: STT_WHISPER_MODEL,
				DEEPGRAM_API_KEY: STT_DEEPGRAM_API_KEY,
				AZURE_API_KEY: STT_AZURE_API_KEY,
				AZURE_REGION: STT_AZURE_REGION,
				AZURE_LOCALES: STT_AZURE_LOCALES,
				AZURE_BASE_URL: STT_AZURE_BASE_URL,
				AZURE_MAX_SPEAKERS: STT_AZURE_MAX_SPEAKERS
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

	const testTTSConnection = async () => {
		if (TTS_ENGINE !== 'openai' || !TTS_OPENAI_API_BASE_URL) {
			connectionStatus = { success: false, message: 'Please enter a valid API Base URL', tested: true };
			return;
		}

		connectionTesting = true;
		connectionStatus = { success: false, message: 'Testing connection...', tested: false };

		try {
			// Clean up the URL - remove trailing slashes and /v1 suffixes
			let baseUrl = TTS_OPENAI_API_BASE_URL.trim();
			if (baseUrl.endsWith('/')) {
				baseUrl = baseUrl.slice(0, -1);
			}
			if (baseUrl.endsWith('/v1')) {
				baseUrl = baseUrl.slice(0, -3);
			}

			// Test models endpoint
			const modelsUrl = `${baseUrl}/v1/models`;
			const modelsHeaders = {
				'Content-Type': 'application/json'
			};
			
			// Add API key if provided
			if (TTS_OPENAI_API_KEY) {
				modelsHeaders['Authorization'] = `Bearer ${TTS_OPENAI_API_KEY}`;
			}

			const modelsResponse = await fetch(modelsUrl, {
				method: 'GET',
				headers: modelsHeaders
			});

			if (!modelsResponse.ok) {
				throw new Error(`Models endpoint failed: ${modelsResponse.status} ${modelsResponse.statusText}`);
			}

			const modelsData = await modelsResponse.json();
			console.log('Models data:', modelsData);

			// Test voices endpoint
			const voicesUrl = `${baseUrl}/v1/audio/voices`;
			const voicesResponse = await fetch(voicesUrl, {
				method: 'GET',
				headers: modelsHeaders
			});

			if (!voicesResponse.ok) {
				throw new Error(`Voices endpoint failed: ${voicesResponse.status} ${voicesResponse.statusText}`);
			}

			const voicesData = await voicesResponse.json();
			console.log('Voices data:', voicesData);

			// Update models dropdown
			if (modelsData?.data && Array.isArray(modelsData.data)) {
				models = modelsData.data.map(model => ({ 
					id: model.id, 
					name: model.name || model.id 
				}));
			} else {
				models = [];
			}

			// Update voices dropdown
			if (voicesData?.voices && Array.isArray(voicesData.voices)) {
				voices = voicesData.voices.map(voice => ({
					id: voice.id || voice.name,
					name: voice.name || voice.id
				}));
			} else {
				voices = [];
			}

			// Special handling for no voices found
			if (voices.length === 0) {
				connectionStatus = { 
					success: false, 
					message: `❌ No voices found. If using Kokoro/OpenAI-compatible backends, ensure the voices endpoint is enabled and returns valid data.`, 
					tested: true 
				};
				return;
			}

			// Reset selections to ensure admin makes conscious choices
			connectionStatus = { 
				success: true, 
				message: `✅ Connection successful! Found ${models.length} models and ${voices.length} voices. Please select your preferences.`, 
				tested: true 
			};

		} catch (error) {
			console.error('TTS connection test failed:', error);
			
			// Provide specific guidance for common issues
			let errorMessage = `❌ Connection failed: ${error.message}`;
			if (error.message.includes('voices')) {
				errorMessage += '. If using Kokoro/OpenAI-compatible backends, ensure the voices endpoint is enabled.';
			}
			
			connectionStatus = { 
				success: false, 
				message: errorMessage, 
				tested: true 
			};
		} finally {
			connectionTesting = false;
		}
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

			TTS_AZURE_SPEECH_REGION = res.tts.AZURE_SPEECH_REGION;
			TTS_AZURE_SPEECH_BASE_URL = res.tts.AZURE_SPEECH_BASE_URL;
			TTS_AZURE_SPEECH_OUTPUT_FORMAT = res.tts.AZURE_SPEECH_OUTPUT_FORMAT;

			STT_OPENAI_API_BASE_URL = res.stt.OPENAI_API_BASE_URL;
			STT_OPENAI_API_KEY = res.stt.OPENAI_API_KEY;

			STT_ENGINE = res.stt.ENGINE;
			STT_MODEL = res.stt.MODEL;
			STT_SUPPORTED_CONTENT_TYPES = (res?.stt?.SUPPORTED_CONTENT_TYPES ?? []).join(',');
			STT_WHISPER_MODEL = res.stt.WHISPER_MODEL;
			STT_AZURE_API_KEY = res.stt.AZURE_API_KEY;
			STT_AZURE_REGION = res.stt.AZURE_REGION;
			STT_AZURE_LOCALES = res.stt.AZURE_LOCALES;
			STT_AZURE_BASE_URL = res.stt.AZURE_BASE_URL;
			STT_AZURE_MAX_SPEAKERS = res.stt.AZURE_MAX_SPEAKERS;
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
	<div class=" space-y-3 overflow-y-scroll scrollbar-hidden h-full">
		<div class="flex flex-col gap-3">
			<div>
				<div class=" mb-2.5 text-base font-medium">{$i18n.t('Speech-to-Text')}</div>

				<hr class=" border-gray-100 dark:border-gray-850 my-2" />

				{#if STT_ENGINE !== 'web'}
					<div class="mb-2">
						<div class=" mb-1.5 text-xs font-medium">{$i18n.t('Supported MIME Types')}</div>
						<div class="flex w-full">
							<div class="flex-1">
								<input
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
									bind:value={STT_SUPPORTED_CONTENT_TYPES}
									placeholder={$i18n.t(
										'e.g., audio/wav,audio/mpeg,video/* (leave blank for defaults)'
									)}
								/>
							</div>
						</div>
					</div>
				{/if}

				<div class="mb-2 py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">{$i18n.t('Speech-to-Text Engine')}</div>
					<div class="flex items-center relative">
						<select
							class="dark:bg-gray-900 cursor-pointer w-fit pr-8 rounded-sm px-2 p-1 text-xs bg-transparent outline-hidden text-right"
							bind:value={STT_ENGINE}
							placeholder="Select an engine"
						>
							<option value="">{$i18n.t('Whisper (Local)')}</option>
							<option value="openai">OpenAI</option>
							<option value="web">{$i18n.t('Web API')}</option>
							<option value="deepgram">Deepgram</option>
							<option value="azure">Azure AI Speech</option>
						</select>
					</div>
				</div>

				{#if STT_ENGINE === 'openai'}
					<div>
						<div class="mt-1 flex gap-2 mb-1">
							<input
								class="flex-1 w-full bg-transparent outline-hidden"
								placeholder={$i18n.t('API Base URL')}
								bind:value={STT_OPENAI_API_BASE_URL}
								required
							/>

							<SensitiveInput placeholder={$i18n.t('API Key')} bind:value={STT_OPENAI_API_KEY} />
						</div>
					</div>

					<hr class="border-gray-100 dark:border-gray-850 my-2" />

					<div>
						<div class=" mb-1.5 text-xs font-medium">{$i18n.t('STT Model')}</div>
						<div class="flex w-full">
							<div class="flex-1">
								<input
									list="model-list"
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
									bind:value={STT_MODEL}
									placeholder="Select a model"
								/>

								<datalist id="model-list">
									<option value="whisper-1" />
								</datalist>
							</div>
						</div>
					</div>
				{:else if STT_ENGINE === 'deepgram'}
					<div>
						<div class="mt-1 flex gap-2 mb-1">
							<SensitiveInput placeholder={$i18n.t('API Key')} bind:value={STT_DEEPGRAM_API_KEY} />
						</div>
					</div>

					<hr class="border-gray-100 dark:border-gray-850 my-2" />

					<div>
						<div class=" mb-1.5 text-xs font-medium">{$i18n.t('STT Model')}</div>
						<div class="flex w-full">
							<div class="flex-1">
								<input
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
									bind:value={STT_MODEL}
									placeholder="Select a model (optional)"
								/>
							</div>
						</div>
						<div class="mt-2 mb-1 text-xs text-gray-400 dark:text-gray-500">
							{$i18n.t('Leave model field empty to use the default model.')}
							<a
								class=" hover:underline dark:text-gray-200 text-gray-800"
								href="https://developers.deepgram.com/docs/models"
								target="_blank"
							>
								{$i18n.t('Click here to see available models.')}
							</a>
						</div>
					</div>
				{:else if STT_ENGINE === 'azure'}
					<div>
						<div class="mt-1 flex gap-2 mb-1">
							<SensitiveInput
								placeholder={$i18n.t('API Key')}
								bind:value={STT_AZURE_API_KEY}
								required
							/>
						</div>

						<hr class="border-gray-100 dark:border-gray-850 my-2" />

						<div>
							<div class=" mb-1.5 text-xs font-medium">{$i18n.t('Azure Region')}</div>
							<div class="flex w-full">
								<div class="flex-1">
									<input
										class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
										bind:value={STT_AZURE_REGION}
										placeholder={$i18n.t('e.g., westus (leave blank for eastus)')}
									/>
								</div>
							</div>
						</div>

						<div>
							<div class=" mb-1.5 text-xs font-medium">{$i18n.t('Language Locales')}</div>
							<div class="flex w-full">
								<div class="flex-1">
									<input
										class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
										bind:value={STT_AZURE_LOCALES}
										placeholder={$i18n.t('e.g., en-US,ja-JP (leave blank for auto-detect)')}
									/>
								</div>
							</div>
						</div>

						<div>
							<div class=" mb-1.5 text-xs font-medium">{$i18n.t('Endpoint URL')}</div>
							<div class="flex w-full">
								<div class="flex-1">
									<input
										class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
										bind:value={STT_AZURE_BASE_URL}
										placeholder={$i18n.t('(leave blank for to use commercial endpoint)')}
									/>
								</div>
							</div>
						</div>

						<div>
							<div class=" mb-1.5 text-xs font-medium">{$i18n.t('Max Speakers')}</div>
							<div class="flex w-full">
								<div class="flex-1">
									<input
										class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
										bind:value={STT_AZURE_MAX_SPEAKERS}
										placeholder={$i18n.t('e.g., 3, 4, 5 (leave blank for default)')}
									/>
								</div>
							</div>
						</div>
					</div>
				{:else if STT_ENGINE === ''}
					<div>
						<div class=" mb-1.5 text-xs font-medium">{$i18n.t('STT Model')}</div>

						<div class="flex w-full">
							<div class="flex-1 mr-2">
								<input
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
									placeholder={$i18n.t('Set whisper model')}
									bind:value={STT_WHISPER_MODEL}
								/>
							</div>

							<button
								class="px-2.5 bg-gray-50 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition"
								on:click={() => {
									sttModelUpdateHandler();
								}}
								disabled={STT_WHISPER_MODEL_LOADING}
							>
								{#if STT_WHISPER_MODEL_LOADING}
									<div class="self-center">
										<Spinner />
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
							{$i18n.t(`Open WebUI uses faster-whisper internally.`)}

							<a
								class=" hover:underline dark:text-gray-200 text-gray-800"
								href="https://github.com/SYSTRAN/faster-whisper"
								target="_blank"
							>
								{$i18n.t(
									`Click here to learn more about faster-whisper and see the available models.`
								)}
							</a>
						</div>
					</div>
				{/if}
			</div>

			<div>
				<div class=" mb-2.5 text-base font-medium">{$i18n.t('Text-to-Speech')}</div>

				<hr class=" border-gray-100 dark:border-gray-850 my-2" />

				<div class="mb-2 py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">{$i18n.t('Text-to-Speech Engine')}</div>
					<div class="flex items-center relative">
						<select
							class=" dark:bg-gray-900 w-fit pr-8 cursor-pointer rounded-sm px-2 p-1 text-xs bg-transparent outline-hidden text-right"
							bind:value={TTS_ENGINE}
							placeholder="Select a mode"
							on:change={async (e) => {
								await updateConfigHandler();
								await getVoices();
								await getModels();

								if (e.target?.value === 'openai') {
									TTS_VOICE = 'alloy';
									TTS_MODEL = 'tts-1';
								} else {
									TTS_VOICE = '';
									TTS_MODEL = '';
								}
							}}
						>
							<option value="">{$i18n.t('Web API')}</option>
							<option value="transformers">{$i18n.t('Transformers')} ({$i18n.t('Local')})</option>
							<option value="openai">{$i18n.t('OpenAI')}</option>
							<option value="elevenlabs">{$i18n.t('ElevenLabs')}</option>
							<option value="azure">{$i18n.t('Azure AI Speech')}</option>
						</select>
					</div>
				</div>

				{#if TTS_ENGINE === 'openai'}
					<div>
						<div class="mt-1 flex gap-2 mb-1">
							<input
								class="flex-1 w-full bg-transparent outline-hidden"
								placeholder={$i18n.t('API Base URL')}
								bind:value={TTS_OPENAI_API_BASE_URL}
								required
								on:input={() => {
									connectionStatus = { success: false, message: '', tested: false };
								}}
							/>

							<SensitiveInput placeholder={$i18n.t('API Key')} bind:value={TTS_OPENAI_API_KEY} />

							<button
								type="button"
								class="px-2 py-1 text-xs text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition flex items-center gap-1"
								on:click={testTTSConnection}
								disabled={connectionTesting || !TTS_OPENAI_API_BASE_URL}
								title="Test connection and populate models/voices"
							>
								{#if connectionTesting}
									<svg class="animate-spin size-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
										<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
										<path class="opacity-75" fill="currentColor" d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
									</svg>
									Test
								{:else}
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-3">
										<path d="M8 3a5 5 0 1 0 4.546 2.914.5.5 0 0 1 .908-.417A6 6 0 1 1 8 2z"/>
										<path d="M8 4.466V.534a.25.25 0 0 1 .41-.192l2.36 1.966c.12.1.12.284 0 .384L8.41 4.658A.25.25 0 0 1 8 4.466"/>
									</svg>
									Test
								{/if}
							</button>
						</div>

						{#if connectionStatus.tested}
							<div class="mt-2 p-2 rounded-lg text-sm {connectionStatus.success ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300' : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300'}">
								{connectionStatus.message}
							</div>
						{/if}
					</div>
				{:else if TTS_ENGINE === 'elevenlabs'}
					<div>
						<div class="mt-1 flex gap-2 mb-1">
							<input
								class="flex-1 w-full rounded-lg py-2 pl-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
								placeholder={$i18n.t('API Key')}
								bind:value={TTS_API_KEY}
								required
							/>
						</div>
					</div>
				{:else if TTS_ENGINE === 'azure'}
					<div>
						<div class="mt-1 flex gap-2 mb-1">
							<SensitiveInput placeholder={$i18n.t('API Key')} bind:value={TTS_API_KEY} required />
						</div>

						<hr class="border-gray-100 dark:border-gray-850 my-2" />

						<div>
							<div class=" mb-1.5 text-xs font-medium">{$i18n.t('Azure Region')}</div>
							<div class="flex w-full">
								<div class="flex-1">
									<input
										class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
										bind:value={TTS_AZURE_SPEECH_REGION}
										placeholder={$i18n.t('e.g., westus (leave blank for eastus)')}
									/>
								</div>
							</div>
						</div>

						<div>
							<div class=" mb-1.5 text-xs font-medium">{$i18n.t('Endpoint URL')}</div>
							<div class="flex w-full">
								<div class="flex-1">
									<input
										class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
										bind:value={TTS_AZURE_SPEECH_BASE_URL}
										placeholder={$i18n.t('(leave blank for to use commercial endpoint)')}
									/>
								</div>
							</div>
						</div>
					</div>
				{/if}

				<div class="mb-2">
					{#if TTS_ENGINE === ''}
						<div>
							<div class=" mb-1.5 text-xs font-medium">{$i18n.t('TTS Voice')}</div>
							<div class="flex w-full">
								<div class="flex-1">
									<select
										class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
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
					{:else if TTS_ENGINE === 'transformers'}
						<div>
							<div class=" mb-1.5 text-xs font-medium">{$i18n.t('TTS Model')}</div>
							<div class="flex w-full">
								<div class="flex-1">
									<input
										list="model-list"
										class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
										bind:value={TTS_MODEL}
										placeholder="CMU ARCTIC speaker embedding name"
									/>

									<datalist id="model-list">
										<option value="tts-1" />
									</datalist>
								</div>
							</div>
							<div class="mt-2 mb-1 text-xs text-gray-400 dark:text-gray-500">
								{$i18n.t(`Open WebUI uses SpeechT5 and CMU Arctic speaker embeddings.`)}

								To learn more about SpeechT5,

								<a
									class=" hover:underline dark:text-gray-200 text-gray-800"
									href="https://github.com/microsoft/SpeechT5"
									target="_blank"
								>
									{$i18n.t(`click here`, {
										name: 'SpeechT5'
									})}.
								</a>
								To see the available CMU Arctic speaker embeddings,
								<a
									class=" hover:underline dark:text-gray-200 text-gray-800"
									href="https://huggingface.co/datasets/Matthijs/cmu-arctic-xvectors"
									target="_blank"
								>
									{$i18n.t(`click here`)}.
								</a>
							</div>
						</div>
					{:else if TTS_ENGINE === 'openai'}
						<div class=" flex gap-2">
							<div class="w-full">
								<div class=" mb-1.5 text-xs font-medium">{$i18n.t('TTS Voice')}</div>
								<div class="flex w-full">
									<div class="flex-1">
										<select
											class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
											bind:value={TTS_VOICE}
										>
											<option value="">{$i18n.t('Select a voice')}</option>
											{#each voices as voice}
												<option value={voice.id} class="bg-gray-50 dark:bg-gray-700">{voice.name}</option>
											{/each}
										</select>
									</div>
								</div>
							</div>
							<div class="w-full">
								<div class=" mb-1.5 text-xs font-medium">{$i18n.t('TTS Model')}</div>
								<div class="flex w-full">
									<div class="flex-1">
										<select
											class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
											bind:value={TTS_MODEL}
										>
											<option value="">{$i18n.t('Select a model')}</option>
											{#each models as model}
												<option value={model.id} class="bg-gray-50 dark:bg-gray-700">{model.name || model.id}</option>
											{/each}
										</select>
									</div>
								</div>
							</div>
						</div>
					{:else if TTS_ENGINE === 'elevenlabs'}
						<div class=" flex gap-2">
							<div class="w-full">
								<div class=" mb-1.5 text-xs font-medium">{$i18n.t('TTS Voice')}</div>
								<div class="flex w-full">
									<div class="flex-1">
										<input
											list="voice-list"
											class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
											bind:value={TTS_VOICE}
											placeholder="Select a voice"
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
								<div class=" mb-1.5 text-xs font-medium">{$i18n.t('TTS Model')}</div>
								<div class="flex w-full">
									<div class="flex-1">
										<input
											list="tts-model-list"
											class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
											bind:value={TTS_MODEL}
											placeholder="Select a model"
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
						<div class=" flex gap-2">
							<div class="w-full">
								<div class=" mb-1.5 text-xs font-medium">{$i18n.t('TTS Voice')}</div>
								<div class="flex w-full">
									<div class="flex-1">
										<input
											list="voice-list"
											class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
											bind:value={TTS_VOICE}
											placeholder="Select a voice"
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
								<div class=" mb-1.5 text-xs font-medium">
									{$i18n.t('Output format')}
									<a
										href="https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-text-to-speech?tabs=streaming#audio-outputs"
										target="_blank"
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
										/>
									</div>
								</div>
							</div>
						</div>
					{/if}
				</div>

				<div class="pt-0.5 flex w-full justify-between">
					<div class="self-center text-xs font-medium">{$i18n.t('Response splitting')}</div>
					<div class="flex items-center relative">
						<select
							class="dark:bg-gray-900 w-fit pr-8 cursor-pointer rounded-sm px-2 p-1 text-xs bg-transparent outline-hidden text-right"
							aria-label="Select how to split message text for TTS requests"
							bind:value={TTS_SPLIT_ON}
						>
							{#each Object.values(TTS_RESPONSE_SPLIT) as split}
								<option value={split}
									>{$i18n.t(split.charAt(0).toUpperCase() + split.slice(1))}</option
								>
							{/each}
						</select>
					</div>
				</div>
				<div class="mt-2 mb-1 text-xs text-gray-400 dark:text-gray-500">
					{$i18n.t(
						"Control how message text is split for TTS requests. 'Punctuation' splits into sentences, 'paragraphs' splits into paragraphs, and 'none' keeps the message as a single string."
					)}
				</div>
			</div>
		</div>
	</div>
	<div class="flex justify-end text-sm font-medium">
		<button
			class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
