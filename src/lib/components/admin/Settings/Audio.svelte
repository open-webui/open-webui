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
	let TTS_KOKORO_API_BASE_URL = '';
	let TTS_KOKORO_ENABLE_NORMALIZATION: boolean = true;
	let TTS_KOKORO_CUSTOM_COMBINATION_STRING: string = '';

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

	// Unified Voice Type for rendering in select dropdowns
	type DisplayVoice = {
		id: string; // Unique identifier (voiceURI, actual API ID, or voice name itself)
		name: string; // Name to display in the dropdown
	};

	type FetchedModel = {
		id: string;
		object: string;
		created: number;
		owned_by: string;
		name?: string; // Some APIs might have a name field for models
	};

	// Type for parsed KokoroTTS voice combinations
	type KokoroVoiceCombination = {
		name: string;
		weight: number;
		percentage: number;
		isValid: boolean;
	};

	let voices: DisplayVoice[] = [];
	let models: FetchedModel[] = [];
	let kokoroVoiceCombinations: KokoroVoiceCombination[] = [];

	// --- Validation State ---
	let isKokoroCombinationInputValid = true;
	let kokoroCombinationError: string | null = null;

	// Helper to get a clean URL for KokoroTTS
	const getCleanKokoroUrl = (url: string) => {
		if (!url) return '';
		return url.replace(/\/+$/, ''); // Remove trailing slashes
	};

	// Function to parse KokoroTTS voice combination string and calculate percentages
	const parseKokoroVoiceCombinations = (combinationString: string | null | undefined) => {
		if (!combinationString) {
			kokoroVoiceCombinations = [];
			isKokoroCombinationInputValid = true;
			kokoroCombinationError = null;
			return;
		}

		const combinations: KokoroVoiceCombination[] = [];
		let totalWeight = 0;
		const invalidVoices: string[] = [];

		// Regex to capture voice names. It looks for:
		// 1. `([\w-]+)`: Captures the voice name (alphanumeric + hyphen).
		// 2. `(?:\([^)]+\))?`: Optionally matches a weight in parentheses (any characters inside), but doesn't capture it.
		// The 'g' flag ensures we find all matches.
		const voiceRegex = /([\w-]+)(?:\([^)]+\))?/g;
		let match;

		// Create a set of available VOICE IDs for quick lookup
		const availableVoiceIds = new Set(voices.map(voice => voice.id));

		while ((match = voiceRegex.exec(combinationString)) !== null) {
			const voiceName = match[1]; // This is the captured voice name
			const weightMatch = match[0].match(/\((\d+(?:\.\d+)?)\)/); // Extract weight separately if it exists
			const weight = weightMatch ? parseFloat(weightMatch[1]) : 1; // Default weight is 1

			if (voiceName) {
				const isValid = availableVoiceIds.has(voiceName); // VALIDATE AGAINST VOICE IDs
				if (!isValid) {
					invalidVoices.push(voiceName); // Add to the list of invalid voices
				}
				combinations.push({ name: voiceName, weight, percentage: 0, isValid });
				totalWeight += weight;
			}
		}

		// Calculate percentages
		if (totalWeight > 0) {
			combinations.forEach((combo) => {
				combo.percentage = (combo.weight / totalWeight) * 100;
			});
		}

		kokoroVoiceCombinations = combinations;
		isKokoroCombinationInputValid = invalidVoices.length === 0;

		if (!isKokoroCombinationInputValid) {
			const invalidVoicesString = invalidVoices.join('", "');
			kokoroCombinationError = $i18n.t('Invalid voice names found: "{{voiceNames}}". Please check the available voices.', { voiceNames: invalidVoicesString });
		} else {
			kokoroCombinationError = null;
		}
	};

	// Watch for changes in TTS_KOKORO_CUSTOM_COMBINATION_STRING to update percentages and validation
	$: if (TTS_ENGINE === 'kokoro' && TTS_VOICE === '_custom_kokoro_combination_') {
		parseKokoroVoiceCombinations(TTS_KOKORO_CUSTOM_COMBINATION_STRING);
	}

	const getModels = async () => {
		if (TTS_ENGINE === 'kokoro') {
			const cleanUrl = getCleanKokoroUrl(TTS_KOKORO_API_BASE_URL);
			if (!cleanUrl) {
				models = [];
				return;
			}
			try {
				const response = await fetch(`${cleanUrl}/v1/models`);
				if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
				const data = await response.json();
				models = data.data.filter((m: FetchedModel) => m.owned_by === 'kokoro');
				console.log('KokoroTTS models:', models);
			} catch (e: any) {
				toast.error(`Failed to fetch KokoroTTS models: ${e.message}`);
				models = [];
			}
		} else if (TTS_ENGINE === '') {
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
		let fetchedVoices: DisplayVoice[] = [];

		if (TTS_ENGINE === 'kokoro') {
			const cleanUrl = getCleanKokoroUrl(TTS_KOKORO_API_BASE_URL);
			if (!cleanUrl) {
				voices = [];
				return;
			}
			try {
				const response = await fetch(`${cleanUrl}/v1/audio/voices`);
				if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
				const data = await response.json();
				fetchedVoices = (data.voices as string[]).map((voiceName) => ({
					id: voiceName,
					name: voiceName
				}));
				fetchedVoices.sort((a, b) => a.name.localeCompare(b.name, $i18n.resolvedLanguage));
				console.log('KokoroTTS voices:', fetchedVoices);
			} catch (e: any) {
				toast.error(`Failed to fetch KokoroTTS voices: ${e.message}`);
			}
		} else if (TTS_ENGINE === '') {
			const getBrowserVoicesLoop = setInterval(() => {
				const browserVoices = speechSynthesis.getVoices();
				if (browserVoices.length > 0) {
					clearInterval(getBrowserVoicesLoop);
					fetchedVoices = browserVoices.map((voice) => ({
						id: voice.voiceURI,
						name: voice.name
					}));
					fetchedVoices.sort((a, b) => a.name.localeCompare(b.name, $i18n.resolvedLanguage));
				}
			}, 100);
		} else {
			const res = await _getVoices(localStorage.token).catch((e) => {
				toast.error(`${e}`);
			});

			if (res) {
				console.log(res);
				fetchedVoices = res.voices.map((v: any) => ({
					id: v.id || v.name,
					name: v.name || v.id
				}));
				fetchedVoices.sort((a, b) => a.name.localeCompare(b.name, $i18n.resolvedLanguage));
			}
		}
		voices = fetchedVoices;
	};

	const updateConfigHandler = async () => {
		if (TTS_ENGINE === 'kokoro' && TTS_VOICE === '_custom_kokoro_combination_' && !isKokoroCombinationInputValid) {
			toast.error(kokoroCombinationError || $i18n.t('Please correct the invalid voice names in the combination.'));
			return false;
		}

		const res = await updateAudioConfig(localStorage.token, {
			tts: {
				OPENAI_API_BASE_URL: TTS_OPENAI_API_BASE_URL,
				OPENAI_API_KEY: TTS_OPENAI_API_KEY,
				API_KEY: TTS_API_KEY,
				ENGINE: TTS_ENGINE,
				MODEL: TTS_MODEL,
				VOICE: (() => {
					if (TTS_ENGINE === 'kokoro' && TTS_VOICE === '_custom_kokoro_combination_') {
						return TTS_KOKORO_CUSTOM_COMBINATION_STRING;
					}
					return TTS_VOICE;
				})(),
				SPLIT_ON: TTS_SPLIT_ON,
				AZURE_SPEECH_REGION: TTS_AZURE_SPEECH_REGION,
				AZURE_SPEECH_BASE_URL: TTS_AZURE_SPEECH_BASE_URL,
				AZURE_SPEECH_OUTPUT_FORMAT: TTS_AZURE_SPEECH_OUTPUT_FORMAT,
				KOKORO_API_BASE_URL: getCleanKokoroUrl(TTS_KOKORO_API_BASE_URL),
				...(TTS_ENGINE === 'kokoro' && {
					KOKORO_NORMALIZATION_OPTIONS: { normalize: TTS_KOKORO_ENABLE_NORMALIZATION }
				})
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
			return true;
		}
		return false;
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

			if (res.tts.ENGINE === 'kokoro' && res.tts.VOICE) {
				if (res.tts.VOICE.includes('+') || res.tts.VOICE.includes('(')) {
					TTS_KOKORO_CUSTOM_COMBINATION_STRING = res.tts.VOICE;
					TTS_VOICE = '_custom_kokoro_combination_';
					// Parse will be called by reactive block
				} else {
					TTS_VOICE = res.tts.VOICE;
				}
			} else {
				TTS_VOICE = res.tts.VOICE;
				TTS_KOKORO_CUSTOM_COMBINATION_STRING = '';
			}

			TTS_SPLIT_ON = res.tts.SPLIT_ON || TTS_RESPONSE_SPLIT.PUNCTUATION;

			TTS_AZURE_SPEECH_REGION = res.tts.AZURE_SPEECH_REGION;
			TTS_AZURE_SPEECH_BASE_URL = res.tts.AZURE_SPEECH_BASE_URL;
			TTS_AZURE_SPEECH_OUTPUT_FORMAT = res.tts.AZURE_SPEECH_OUTPUT_FORMAT;
			TTS_KOKORO_API_BASE_URL = res.tts.KOKORO_API_BASE_URL || '';
			TTS_KOKORO_ENABLE_NORMALIZATION = res.tts.KOKORO_NORMALIZATION_OPTIONS?.normalize ?? true;

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
		if (TTS_ENGINE === 'kokoro' && TTS_VOICE === '_custom_kokoro_combination_') {
			parseKokoroVoiceCombinations(TTS_KOKORO_CUSTOM_COMBINATION_STRING);
		}
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={async () => {
		if (
			TTS_ENGINE === 'kokoro' &&
			TTS_VOICE === '_custom_kokoro_combination_' &&
			!TTS_KOKORO_CUSTOM_COMBINATION_STRING
		) {
			toast.error($i18n.t('Please enter a custom voice combination for KokoroTTS.'));
			return;
		}
		const saveSuccess = await updateConfigHandler();
		if (saveSuccess) {
			dispatch('save');
		}
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
				{/if}

				{#if STT_ENGINE === ''}
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
								TTS_VOICE = '';
								TTS_MODEL = '';
								TTS_KOKORO_CUSTOM_COMBINATION_STRING = '';
								TTS_KOKORO_ENABLE_NORMALIZATION = true;
								kokoroVoiceCombinations = [];
								isKokoroCombinationInputValid = true;
								kokoroCombinationError = null;
								await updateConfigHandler();
								await getVoices();
								await getModels();

								if (e.target?.value === 'openai') {
									TTS_VOICE = 'alloy';
									TTS_MODEL = 'tts-1';
								}
							}}
						>
							<option value="">{$i18n.t('Web API')}</option>
							<option value="transformers">{$i18n.t('Transformers')} ({$i18n.t('Local')})</option>
							<option value="openai">{$i18n.t('OpenAI')}</option>
							<option value="elevenlabs">{$i18n.t('ElevenLabs')}</option>
							<option value="kokoro">{$i18n.t('KokoroTTS')}</option>
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
							/>

							<SensitiveInput placeholder={$i18n.t('API Key')} bind:value={TTS_OPENAI_API_KEY} />
						</div>
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
				{:else if TTS_ENGINE === 'kokoro'}
					<div>
						<div class="mt-1 flex gap-2 mb-1">
							<input
								class="flex-1 w-full bg-transparent outline-hidden"
								placeholder={$i18n.t('API Base URL')}
								bind:value={TTS_KOKORO_API_BASE_URL}
								required
								on:blur={async () => {
									// Fetching voices/models might fail if API URL is invalid,
									// but we should still try to parse the combination.
									await getVoices(); // Fetch voices for validation
									await getModels(); // Fetch models for selection elsewhere
									// Re-parse to update validation status based on new voices
									parseKokoroVoiceCombinations(TTS_KOKORO_CUSTOM_COMBINATION_STRING);
								}}
							/>
							<SensitiveInput
								placeholder={$i18n.t('API Key (Optional)')}
								bind:value={TTS_API_KEY}
								required={false}
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
										{#each voices as voice (voice.id)}
											<option
												value={voice.id}
												class="bg-gray-100 dark:bg-gray-700"
												selected={TTS_VOICE === voice.id}
											>
												{voice.name}
											</option>
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
										required
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
										<input
											list="voice-list"
											class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
											bind:value={TTS_VOICE}
											placeholder="Select a voice"
											required
										/>

										<datalist id="voice-list">
											{#each voices as voice (voice.id)}
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
											required
										/>

										<datalist id="tts-model-list">
											{#each models as model (model.id)}
												<option value={model.id} class="bg-gray-50 dark:bg-gray-700" />
											{/each}
										</datalist>
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
											required
										/>

										<datalist id="voice-list">
											{#each voices as voice (voice.id)}
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
											required
										/>

										<datalist id="tts-model-list">
											{#each models as model (model.id)}
												<option value={model.id} class="bg-gray-50 dark:bg-gray-700" />
											{/each}
										</datalist>
									</div>
								</div>
							</div>
						</div>
					{:else if TTS_ENGINE === 'kokoro'}
						<div class=" flex gap-2">
							<div class="w-full">
								<div class=" mb-1.5 text-xs font-medium">{$i18n.t('TTS Voice')}</div>
								<div class="flex w-full">
									<div class="flex-1">
										<select
											class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
											bind:value={TTS_VOICE}
											on:change={(e) => {
												const selectedValue = e.target.value;
												if (selectedValue === '_custom_kokoro_combination_') {
													if (!TTS_KOKORO_CUSTOM_COMBINATION_STRING && voices.length > 0) {
														TTS_KOKORO_CUSTOM_COMBINATION_STRING = voices[0].id;
													}
													// The reactive block will handle parsing and validation
												} else {
													kokoroVoiceCombinations = []; // Clear combinations if a specific voice is selected
													isKokoroCombinationInputValid = true;
													kokoroCombinationError = null;
												}
											}}
											required
										>
											<option value="">{$i18n.t('Select a voice')}</option>
											<option value="_custom_kokoro_combination_">
												{$i18n.t('Custom Combination...')}
											</option>
											{#each voices as voice (voice.id)}
												<option value={voice.id} selected={TTS_VOICE === voice.id}>
													{voice.name}
												</option>
											{/each}
										</select>
									</div>
								</div>

								{#if TTS_VOICE === '_custom_kokoro_combination_'}
									<div class="flex-1 mt-2">
										<input
											class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden
                                                {isKokoroCombinationInputValid ? '' : 'border-red-500 dark:border-red-700'}"
											bind:value={TTS_KOKORO_CUSTOM_COMBINATION_STRING}
											placeholder={$i18n.t('e.g., af_bella+af_sky or af_bella(2)+af_sky(1)')}
											required
											aria-invalid={!isKokoroCombinationInputValid}
											aria-describedby={!isKokoroCombinationInputValid ? 'kokoro-combination-error' : undefined}
										/>
										<div class="mt-2 mb-1 text-xs text-gray-400 dark:text-gray-500">
											{$i18n.t(
												'Enter voice combinations (e.g., af_alloy+af_heart) or weighted combinations (e.g., af_bella(2)+af_sky(1)).'
											)}
										</div>

										{#if !isKokoroCombinationInputValid && kokoroCombinationError}
											<p id="kokoro-combination-error" class="mt-1 text-xs text-red-500 dark:text-red-400">
												{kokoroCombinationError}
											</p>
										{/if}

										{#if kokoroVoiceCombinations.length > 0}
											<div class="mt-3 p-2 bg-gray-100 dark:bg-gray-800 rounded-lg">
												<div class="text-xs font-medium mb-1.5">{$i18n.t('Voice Distribution')}</div>
												{#each kokoroVoiceCombinations as combo (combo.name)}
													<div class="flex justify-between text-xs">
														<span>{combo.name}:</span>
														<span>{combo.percentage.toFixed(1)}%</span>
													</div>
												{/each}
											</div>
										{/if}
									</div>
								{/if}

								<div class="mt-2 mb-2 flex w-full justify-between items-center">
									<div class="text-xs font-medium">{$i18n.t('Enable Text Normalization')}</div>
									<label class="relative inline-flex items-center cursor-pointer">
										<input
											type="checkbox"
											class="sr-only peer"
											bind:checked={TTS_KOKORO_ENABLE_NORMALIZATION}
										/>
										<div class="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600" />
									</label>
								</div>
								<div class="mt-2 mb-1 text-xs text-gray-400 dark:text-gray-500">
									{$i18n.t(
										'Disable text normalization if words are missing or timestamps are incorrect in the generated audio.'
									)}
								</div>
							</div>
							<div class="w-full">
								<div class=" mb-1.5 text-xs font-medium">{$i18n.t('TTS Model')}</div>
								<div class="flex w-full">
									<div class="flex-1">
										<select
											class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden"
											bind:value={TTS_MODEL}
											required
										>
											<option value="">{$i18n.t('Select a model')}</option>
											{#each models as model (model.id)}
												<option value={model.id} selected={TTS_MODEL === model.id}>
													{model.id}
												</option>
											{/each}
										</select>
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
											required
										/>

										<datalist id="voice-list">
											{#each voices as voice (voice.id)}
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
