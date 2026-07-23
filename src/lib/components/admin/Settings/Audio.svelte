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
	import Switch from '$lib/components/common/Switch.svelte';
	import TTSVoiceInput from '$lib/components/workspace/Models/TTSVoiceInput.svelte';

	import { TTS_RESPONSE_SPLIT } from '$lib/types';

	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import SettingsSelect from '$lib/components/common/SettingsSelect.svelte';
	import AdminSettingField from './AdminSettingField.svelte';
	import AdminSettingRow from './AdminSettingRow.svelte';
	import AdminSettingSection from './AdminSettingSection.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let saveHandler: () => void;

	// Audio
	let TTS_OPENAI_API_BASE_URL = '';
	let TTS_OPENAI_API_KEY = '';
	let TTS_API_KEY = '';
	let TTS_ENGINE = '';
	let TTS_MODEL = '';
	let TTS_VOICE = '';
	let TTS_OPENAI_PARAMS = '';
	let TTS_SPLIT_ON: TTS_RESPONSE_SPLIT = TTS_RESPONSE_SPLIT.PUNCTUATION;
	let TTS_AZURE_SPEECH_REGION = '';
	let TTS_AZURE_SPEECH_BASE_URL = '';
	let TTS_AZURE_SPEECH_OUTPUT_FORMAT = '';
	let TTS_MISTRAL_API_KEY = '';
	let TTS_MISTRAL_API_BASE_URL = '';

	let STT_OPENAI_API_BASE_URL = '';
	let STT_OPENAI_API_KEY = '';
	let STT_OPENAI_API_REQUEST_FORMAT = 'multipart';
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
	let STT_MISTRAL_API_KEY = '';
	let STT_MISTRAL_API_BASE_URL = '';
	let STT_MISTRAL_USE_CHAT_COMPLETIONS = false;

	let STT_WHISPER_MODEL_LOADING = false;

	type Voice = {
		id: string;
		name?: string;
		description?: string;
		meta?: {
			description?: string;
		};
	};

	// eslint-disable-next-line no-undef
	let voices: SpeechSynthesisVoice[] = [];
	let providerVoices: Voice[] = [];
	let models: Awaited<ReturnType<typeof _getModels>>['models'] = [];
	const inputClass =
		'w-full h-7 rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';
	const textareaClass =
		'w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors placeholder:text-gray-300 focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:placeholder:text-gray-700 dark:focus:border-blue-500';
	const linkedHelpClass =
		'text-[0.6875rem] text-gray-400 dark:text-gray-600 [&_a]:text-gray-600 [&_a]:hover:underline dark:[&_a]:text-gray-300';

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
			providerVoices = [];

			const getVoicesLoop = setInterval(() => {
				voices = speechSynthesis.getVoices();

				// do your loop
				if (voices.length > 0) {
					clearInterval(getVoicesLoop);
					voices.sort((a, b) => a.name.localeCompare(b.name, $i18n.resolvedLanguage));
				}
			}, 100);
		} else {
			voices = [];

			const res = await _getVoices(localStorage.token).catch((e) => {
				toast.error(`${e}`);
			});

			if (res) {
				console.log(res);
				providerVoices = res.voices ?? [];
				providerVoices.sort((a, b) =>
					(a.name ?? a.id).localeCompare(b.name ?? b.id, $i18n.resolvedLanguage)
				);
			}
		}
	};

	const updateConfigHandler = async () => {
		let openaiParams = {};
		try {
			openaiParams = TTS_OPENAI_PARAMS ? JSON.parse(TTS_OPENAI_PARAMS) : {};
			TTS_OPENAI_PARAMS = JSON.stringify(openaiParams, null, 2);
		} catch (e) {
			toast.error($i18n.t('Invalid JSON format for Parameters'));
			return;
		}

		const res = await updateAudioConfig(localStorage.token, {
			tts: {
				OPENAI_API_BASE_URL: TTS_OPENAI_API_BASE_URL,
				OPENAI_API_KEY: TTS_OPENAI_API_KEY,
				OPENAI_PARAMS: openaiParams,
				API_KEY: TTS_API_KEY,
				ENGINE: TTS_ENGINE,
				MODEL: TTS_MODEL,
				VOICE: TTS_VOICE,
				AZURE_SPEECH_REGION: TTS_AZURE_SPEECH_REGION,
				AZURE_SPEECH_BASE_URL: TTS_AZURE_SPEECH_BASE_URL,
				AZURE_SPEECH_OUTPUT_FORMAT: TTS_AZURE_SPEECH_OUTPUT_FORMAT,
				MISTRAL_API_KEY: TTS_MISTRAL_API_KEY,
				MISTRAL_API_BASE_URL: TTS_MISTRAL_API_BASE_URL,
				SPLIT_ON: TTS_SPLIT_ON
			},
			stt: {
				OPENAI_API_BASE_URL: STT_OPENAI_API_BASE_URL,
				OPENAI_API_KEY: STT_OPENAI_API_KEY,
				OPENAI_API_REQUEST_FORMAT: STT_OPENAI_API_REQUEST_FORMAT,
				ENGINE: STT_ENGINE,
				MODEL: STT_MODEL,
				SUPPORTED_CONTENT_TYPES: STT_SUPPORTED_CONTENT_TYPES.split(','),
				WHISPER_MODEL: STT_WHISPER_MODEL,
				DEEPGRAM_API_KEY: STT_DEEPGRAM_API_KEY,
				AZURE_API_KEY: STT_AZURE_API_KEY,
				AZURE_REGION: STT_AZURE_REGION,
				AZURE_LOCALES: STT_AZURE_LOCALES,
				AZURE_BASE_URL: STT_AZURE_BASE_URL,
				AZURE_MAX_SPEAKERS: STT_AZURE_MAX_SPEAKERS,
				MISTRAL_API_KEY: STT_MISTRAL_API_KEY,
				MISTRAL_API_BASE_URL: STT_MISTRAL_API_BASE_URL,
				MISTRAL_USE_CHAT_COMPLETIONS: STT_MISTRAL_USE_CHAT_COMPLETIONS
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
			TTS_OPENAI_PARAMS = JSON.stringify(res?.tts?.OPENAI_PARAMS ?? '', null, 2);
			TTS_API_KEY = res.tts.API_KEY;

			TTS_ENGINE = res.tts.ENGINE;
			TTS_MODEL = res.tts.MODEL;
			TTS_VOICE = res.tts.VOICE;

			TTS_SPLIT_ON = res.tts.SPLIT_ON || TTS_RESPONSE_SPLIT.PUNCTUATION;

			TTS_AZURE_SPEECH_REGION = res.tts.AZURE_SPEECH_REGION;
			TTS_AZURE_SPEECH_BASE_URL = res.tts.AZURE_SPEECH_BASE_URL;
			TTS_AZURE_SPEECH_OUTPUT_FORMAT = res.tts.AZURE_SPEECH_OUTPUT_FORMAT;
			TTS_MISTRAL_API_KEY = res.tts.MISTRAL_API_KEY;
			TTS_MISTRAL_API_BASE_URL = res.tts.MISTRAL_API_BASE_URL;

			STT_OPENAI_API_BASE_URL = res.stt.OPENAI_API_BASE_URL;
			STT_OPENAI_API_KEY = res.stt.OPENAI_API_KEY;
			STT_OPENAI_API_REQUEST_FORMAT = res.stt.OPENAI_API_REQUEST_FORMAT || 'multipart';

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
			STT_MISTRAL_API_KEY = res.stt.MISTRAL_API_KEY;
			STT_MISTRAL_API_BASE_URL = res.stt.MISTRAL_API_BASE_URL;
			STT_MISTRAL_USE_CHAT_COMPLETIONS = res.stt.MISTRAL_USE_CHAT_COMPLETIONS;
		}

		await getVoices();
		await getModels();
	});
</script>

<form
	class="flex h-full flex-col justify-between text-sm"
	on:submit|preventDefault={async () => {
		await updateConfigHandler();
		dispatch('save');
	}}
>
	<h2 class="text-sm font-medium text-gray-900 dark:text-white mb-4">{$i18n.t('Audio')}</h2>

	<div class="flex-1 min-h-0 overflow-y-auto scrollbar-hover pr-1.5">
		<AdminSettingSection title={$i18n.t('Speech-to-Text')} first>
			<AdminSettingRow
				label={$i18n.t('Speech-to-Text Engine')}
				description={$i18n.t('Choose the transcription provider used for audio input.')}
			>
				<SettingsSelect bind:value={STT_ENGINE} placeholder={$i18n.t('Select an engine')}>
					<option value="">{$i18n.t('Whisper (Local)')}</option>
					<option value="openai">{$i18n.t('OpenAI')}</option>
					<option value="web">{$i18n.t('Web API')}</option>
					<option value="deepgram">{$i18n.t('Deepgram')}</option>
					<option value="azure">{$i18n.t('Azure AI Speech')}</option>
					<option value="mistral">{$i18n.t('MistralAI')}</option>
				</SettingsSelect>
			</AdminSettingRow>

			{#if STT_ENGINE !== 'web'}
				<AdminSettingField
					label={$i18n.t('Supported MIME Types')}
					description={$i18n.t('Comma-separated audio or video MIME types accepted for upload.')}
				>
					<input
						class={inputClass}
						bind:value={STT_SUPPORTED_CONTENT_TYPES}
						placeholder={$i18n.t('e.g., audio/wav,audio/mpeg,video/* (leave blank for defaults)')}
					/>
				</AdminSettingField>
			{/if}

			{#if STT_ENGINE === 'openai'}
				<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
					<AdminSettingField label={$i18n.t('API Base URL')}>
						<input
							class={inputClass}
							placeholder={$i18n.t('API Base URL')}
							bind:value={STT_OPENAI_API_BASE_URL}
							required
						/>
					</AdminSettingField>
					<AdminSettingField label={$i18n.t('API Key')}>
						<SensitiveInput
							variant="settings"
							placeholder={$i18n.t('API Key')}
							bind:value={STT_OPENAI_API_KEY}
						/>
					</AdminSettingField>
				</div>

				<AdminSettingRow
					label={$i18n.t('Request Format')}
					description={$i18n.t('Select how audio is sent to the OpenAI-compatible endpoint.')}
				>
					<SettingsSelect bind:value={STT_OPENAI_API_REQUEST_FORMAT}>
						<option value="multipart">{$i18n.t('Multipart Upload')}</option>
						<option value="json">{$i18n.t('JSON Base64')}</option>
					</SettingsSelect>
				</AdminSettingRow>

				<AdminSettingField label={$i18n.t('STT Model')}>
					<input
						list="stt-openai-model-list"
						class={inputClass}
						bind:value={STT_MODEL}
						placeholder={$i18n.t('Select a model')}
					/>
					<datalist id="stt-openai-model-list">
						<option value="whisper-1"></option>
					</datalist>
				</AdminSettingField>
			{:else if STT_ENGINE === 'deepgram'}
				<AdminSettingField label={$i18n.t('API Key')}>
					<SensitiveInput
						variant="settings"
						placeholder={$i18n.t('API Key')}
						bind:value={STT_DEEPGRAM_API_KEY}
					/>
				</AdminSettingField>

				<AdminSettingField
					label={$i18n.t('STT Model')}
					description={$i18n.t('Leave model field empty to use the default model.')}
				>
					<input
						class={inputClass}
						bind:value={STT_MODEL}
						placeholder={$i18n.t('Select a model (optional)')}
					/>
					<div class="mt-1 {linkedHelpClass}">
						<a href="https://developers.deepgram.com/docs/models" target="_blank">
							{$i18n.t('Click here to see available models.')}
						</a>
					</div>
				</AdminSettingField>
			{:else if STT_ENGINE === 'azure'}
				<AdminSettingField label={$i18n.t('API Key')}>
					<SensitiveInput
						variant="settings"
						placeholder={$i18n.t('API Key')}
						bind:value={STT_AZURE_API_KEY}
						required
					/>
				</AdminSettingField>

				<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
					<AdminSettingField label={$i18n.t('Azure Region')}>
						<input
							class={inputClass}
							bind:value={STT_AZURE_REGION}
							placeholder={$i18n.t('e.g., westus (leave blank for eastus)')}
						/>
					</AdminSettingField>
					<AdminSettingField label={$i18n.t('Language Locales')}>
						<input
							class={inputClass}
							bind:value={STT_AZURE_LOCALES}
							placeholder={$i18n.t('e.g., en-US,ja-JP (leave blank for auto-detect)')}
						/>
					</AdminSettingField>
					<AdminSettingField label={$i18n.t('Endpoint URL')}>
						<input
							class={inputClass}
							bind:value={STT_AZURE_BASE_URL}
							placeholder={$i18n.t('(leave blank for to use commercial endpoint)')}
						/>
					</AdminSettingField>
					<AdminSettingField label={$i18n.t('Max Speakers')}>
						<input
							class={inputClass}
							bind:value={STT_AZURE_MAX_SPEAKERS}
							placeholder={$i18n.t('e.g., 3, 4, 5 (leave blank for default)')}
						/>
					</AdminSettingField>
				</div>
			{:else if STT_ENGINE === 'mistral'}
				<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
					<AdminSettingField label={$i18n.t('API Base URL')}>
						<input
							class={inputClass}
							placeholder={$i18n.t('API Base URL')}
							bind:value={STT_MISTRAL_API_BASE_URL}
							required
						/>
					</AdminSettingField>
					<AdminSettingField label={$i18n.t('API Key')}>
						<SensitiveInput
							variant="settings"
							placeholder={$i18n.t('API Key')}
							bind:value={STT_MISTRAL_API_KEY}
						/>
					</AdminSettingField>
				</div>

				<AdminSettingField
					label={$i18n.t('STT Model')}
					description={$i18n.t('Leave empty to use the default model (voxtral-mini-latest).')}
				>
					<input class={inputClass} bind:value={STT_MODEL} placeholder="voxtral-mini-latest" />
					<div class="mt-1 {linkedHelpClass}">
						<a href="https://docs.mistral.ai/capabilities/audio_transcription" target="_blank">
							{$i18n.t('Learn more about Voxtral transcription.')}
						</a>
					</div>
				</AdminSettingField>

				<AdminSettingRow
					label={$i18n.t('Use Chat Completions API')}
					description={$i18n.t(
						'Use /v1/chat/completions endpoint instead of /v1/audio/transcriptions for potentially better accuracy.'
					)}
				>
					<Switch bind:state={STT_MISTRAL_USE_CHAT_COMPLETIONS} />
				</AdminSettingRow>
			{:else if STT_ENGINE === ''}
				<AdminSettingField
					label={$i18n.t('STT Model')}
					description={$i18n.t('Open WebUI uses faster-whisper internally.')}
				>
					<div class="flex w-full gap-2">
						<input
							class={inputClass}
							placeholder={$i18n.t('Set whisper model')}
							bind:value={STT_WHISPER_MODEL}
						/>
						<button
							class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-gray-500 transition-colors hover:bg-black/5 hover:text-gray-900 disabled:opacity-50 dark:text-gray-500 dark:hover:bg-white/5 dark:hover:text-white"
							type="button"
							on:click={() => {
								sttModelUpdateHandler();
							}}
							disabled={STT_WHISPER_MODEL_LOADING}
							aria-label={$i18n.t('Update model')}
						>
							{#if STT_WHISPER_MODEL_LOADING}
								<Spinner />
							{:else}
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 16 16"
									fill="currentColor"
									class="size-4"
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
					<div class="mt-1 {linkedHelpClass}">
						<a href="https://github.com/SYSTRAN/faster-whisper" target="_blank">
							{$i18n.t(
								'Click here to learn more about faster-whisper and see the available models.'
							)}
						</a>
					</div>
				</AdminSettingField>
			{/if}
		</AdminSettingSection>

		<AdminSettingSection title={$i18n.t('Text-to-Speech')}>
			<AdminSettingRow
				label={$i18n.t('Text-to-Speech Engine')}
				description={$i18n.t('Choose the speech provider used for assistant audio output.')}
			>
				<SettingsSelect
					bind:value={TTS_ENGINE}
					placeholder={$i18n.t('Select a mode')}
					on:change={async (e) => {
						await updateConfigHandler();
						await getVoices();
						await getModels();

						const value = (e.currentTarget as HTMLSelectElement).value;

						if (value === 'openai') {
							TTS_VOICE = 'alloy';
							TTS_MODEL = 'tts-1';
						} else if (value === 'mistral') {
							TTS_VOICE = '';
							TTS_MODEL = 'voxtral-mini-tts-2603';
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
					<option value="mistral">{$i18n.t('MistralAI')}</option>
				</SettingsSelect>
			</AdminSettingRow>

			{#if TTS_ENGINE === 'openai'}
				<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
					<AdminSettingField label={$i18n.t('API Base URL')}>
						<input
							class={inputClass}
							placeholder={$i18n.t('API Base URL')}
							bind:value={TTS_OPENAI_API_BASE_URL}
							required
						/>
					</AdminSettingField>
					<AdminSettingField label={$i18n.t('API Key')}>
						<SensitiveInput
							variant="settings"
							placeholder={$i18n.t('API Key')}
							bind:value={TTS_OPENAI_API_KEY}
						/>
					</AdminSettingField>
				</div>
			{:else if TTS_ENGINE === 'elevenlabs'}
				<AdminSettingField label={$i18n.t('API Key')}>
					<SensitiveInput
						variant="settings"
						placeholder={$i18n.t('API Key')}
						bind:value={TTS_API_KEY}
						required
					/>
				</AdminSettingField>
			{:else if TTS_ENGINE === 'azure'}
				<AdminSettingField label={$i18n.t('API Key')}>
					<SensitiveInput
						variant="settings"
						placeholder={$i18n.t('API Key')}
						bind:value={TTS_API_KEY}
						required
					/>
				</AdminSettingField>

				<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
					<AdminSettingField label={$i18n.t('Azure Region')}>
						<input
							class={inputClass}
							bind:value={TTS_AZURE_SPEECH_REGION}
							placeholder={$i18n.t('e.g., westus (leave blank for eastus)')}
						/>
					</AdminSettingField>
					<AdminSettingField label={$i18n.t('Endpoint URL')}>
						<input
							class={inputClass}
							bind:value={TTS_AZURE_SPEECH_BASE_URL}
							placeholder={$i18n.t('(leave blank for to use commercial endpoint)')}
						/>
					</AdminSettingField>
				</div>
			{:else if TTS_ENGINE === 'mistral'}
				<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
					<AdminSettingField label={$i18n.t('API Base URL')}>
						<input
							class={inputClass}
							placeholder={$i18n.t('API Base URL')}
							bind:value={TTS_MISTRAL_API_BASE_URL}
							required
						/>
					</AdminSettingField>
					<AdminSettingField label={$i18n.t('API Key')}>
						<SensitiveInput
							variant="settings"
							placeholder={$i18n.t('API Key')}
							bind:value={TTS_MISTRAL_API_KEY}
						/>
					</AdminSettingField>
				</div>
			{/if}

			{#if TTS_ENGINE === ''}
				<AdminSettingField label={$i18n.t('TTS Voice')}>
					<SettingsSelect bind:value={TTS_VOICE} className="w-full">
						<option value="" selected={TTS_VOICE !== ''}>{$i18n.t('Default')}</option>
						{#each voices as voice}
							<option
								value={voice.voiceURI}
								class="bg-gray-100 dark:bg-gray-700"
								selected={TTS_VOICE === voice.voiceURI}>{voice.name}</option
							>
						{/each}
					</SettingsSelect>
				</AdminSettingField>
			{:else if TTS_ENGINE === 'transformers'}
				<AdminSettingField
					label={$i18n.t('TTS Model')}
					description={$i18n.t('Open WebUI uses SpeechT5 and CMU Arctic speaker embeddings.')}
				>
					<input
						list="tts-transformers-model-list"
						class={inputClass}
						bind:value={TTS_MODEL}
						placeholder={$i18n.t('CMU ARCTIC speaker embedding name')}
					/>
					<datalist id="tts-transformers-model-list">
						<option value="tts-1"></option>
					</datalist>
					<div class="mt-1 {linkedHelpClass}">
						{$i18n.t('To learn more about SpeechT5,')}
						<a href="https://github.com/microsoft/SpeechT5" target="_blank">
							{$i18n.t('click here')}.
						</a>
						{$i18n.t('To see the available CMU Arctic speaker embeddings,')}
						<a href="https://huggingface.co/datasets/Matthijs/cmu-arctic-xvectors" target="_blank">
							{$i18n.t('click here')}.
						</a>
					</div>
				</AdminSettingField>
			{:else if TTS_ENGINE === 'openai'}
				<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
					<AdminSettingField label={$i18n.t('TTS Voice')}>
						<TTSVoiceInput
							bind:value={TTS_VOICE}
							voices={providerVoices}
							placeholder={$i18n.t('Select a voice')}
							className={inputClass}
						/>
					</AdminSettingField>
					<AdminSettingField label={$i18n.t('TTS Model')}>
						<input
							list="tts-model-list"
							class={inputClass}
							bind:value={TTS_MODEL}
							placeholder={$i18n.t('Select a model')}
						/>
					</AdminSettingField>
				</div>
				<AdminSettingField
					label={$i18n.t('Additional Parameters')}
					description={$i18n.t(
						'Enter additional OpenAI-compatible TTS request parameters as JSON.'
					)}
				>
					<Textarea
						className={textareaClass}
						bind:value={TTS_OPENAI_PARAMS}
						placeholder={$i18n.t('Enter additional parameters in JSON format')}
					/>
				</AdminSettingField>
			{:else if TTS_ENGINE === 'elevenlabs' || TTS_ENGINE === 'mistral'}
				<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
					<AdminSettingField label={$i18n.t('TTS Voice')}>
						<TTSVoiceInput
							bind:value={TTS_VOICE}
							voices={providerVoices}
							placeholder={$i18n.t('Select a voice')}
							className={inputClass}
						/>
					</AdminSettingField>
					<AdminSettingField label={$i18n.t('TTS Model')}>
						<input
							list="tts-model-list"
							class={inputClass}
							bind:value={TTS_MODEL}
							placeholder={$i18n.t('Select a model')}
						/>
					</AdminSettingField>
				</div>
			{:else if TTS_ENGINE === 'azure'}
				<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
					<AdminSettingField label={$i18n.t('TTS Voice')}>
						<TTSVoiceInput
							bind:value={TTS_VOICE}
							voices={providerVoices}
							placeholder={$i18n.t('Select a voice')}
							className={inputClass}
						/>
					</AdminSettingField>
					<AdminSettingField label={$i18n.t('Output format')}>
						<input
							class={inputClass}
							bind:value={TTS_AZURE_SPEECH_OUTPUT_FORMAT}
							placeholder={$i18n.t('Select an output format')}
						/>
						<div class="mt-1 {linkedHelpClass}">
							<a
								href="https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-text-to-speech?tabs=streaming#audio-outputs"
								target="_blank"
							>
								{$i18n.t('Available list')}
							</a>
						</div>
					</AdminSettingField>
				</div>
			{/if}

			<datalist id="tts-model-list">
				{#each models as model}
					<option value={model.id} class="bg-gray-50 dark:bg-gray-700"></option>
				{/each}
			</datalist>

			<AdminSettingRow
				label={$i18n.t('Response Splitting')}
				description={$i18n.t(
					"Control how message text is split for TTS requests. 'Punctuation' splits into sentences, 'paragraphs' splits into paragraphs, and 'none' keeps the message as a single string."
				)}
			>
				<SettingsSelect
					aria-label={$i18n.t('Select how to split message text for TTS requests')}
					bind:value={TTS_SPLIT_ON}
				>
					{#each Object.values(TTS_RESPONSE_SPLIT) as split}
						<option value={split}>{$i18n.t(split.charAt(0).toUpperCase() + split.slice(1))}</option>
					{/each}
				</SettingsSelect>
			</AdminSettingRow>
		</AdminSettingSection>
	</div>
	<div class="flex justify-end pt-6 text-sm font-normal">
		<button
			class="px-3.5 py-1.5 text-sm font-normal bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
