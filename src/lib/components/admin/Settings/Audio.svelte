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
	import { config } from '$lib/stores';

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
	let TTS_AZURE_SPEECH_OUTPUT_FORMAT = '';

	let STT_OPENAI_API_BASE_URL = '';
	let STT_OPENAI_API_KEY = '';
	let STT_ENGINE = '';
	let STT_MODEL = '';

	// eslint-disable-next-line no-undef
	let voices: SpeechSynthesisVoice[] = [];
	let models: Awaited<ReturnType<typeof _getModels>>['models'] = [];

	const getModels = async () => {
		if (TTS_ENGINE === '') {
			models = [];
		} else {
			const res = await _getModels(localStorage.token).catch((e) => {
				toast.error(e);
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
				}
			}, 100);
		} else {
			const res = await _getVoices(localStorage.token).catch((e) => {
				toast.error(e);
			});

			if (res) {
				console.log(res);
				voices = res.voices;
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
				MODEL: STT_MODEL
			}
		});

		if (res) {
			saveHandler();
			getBackendConfig()
				.then(config.set)
				.catch(() => {});
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

			TTS_AZURE_SPEECH_OUTPUT_FORMAT = res.tts.AZURE_SPEECH_OUTPUT_FORMAT;
			TTS_AZURE_SPEECH_REGION = res.tts.AZURE_SPEECH_REGION;

			STT_OPENAI_API_BASE_URL = res.stt.OPENAI_API_BASE_URL;
			STT_OPENAI_API_KEY = res.stt.OPENAI_API_KEY;

			STT_ENGINE = res.stt.ENGINE;
			STT_MODEL = res.stt.MODEL;
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
				<div class=" mb-1 text-sm font-medium">{$i18n.t('STT Settings')}</div>

				<div class=" py-0.5 flex w-full justify-between">
					<div class=" self-center text-xs font-medium">{$i18n.t('Speech-to-Text Engine')}</div>
					<div class="flex items-center relative">
						<select
							class="dark:bg-gray-900 cursor-pointer w-fit pr-8 rounded px-2 p-1 text-xs bg-transparent outline-none text-right"
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
								class="flex-1 w-full rounded-lg py-2 pl-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
								placeholder={$i18n.t('API Base URL')}
								bind:value={STT_OPENAI_API_BASE_URL}
								required
							/>

							<SensitiveInput placeholder={$i18n.t('API Key')} bind:value={STT_OPENAI_API_KEY} />
						</div>
					</div>

					<hr class=" dark:border-gray-850 my-2" />

					<div>
						<div class=" mb-1.5 text-sm font-medium">{$i18n.t('STT Model')}</div>
						<div class="flex w-full">
							<div class="flex-1">
								<input
									list="model-list"
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
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
							class=" dark:bg-gray-900 w-fit pr-8 cursor-pointer rounded px-2 p-1 text-xs bg-transparent outline-none text-right"
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
								class="flex-1 w-full rounded-lg py-2 pl-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
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
								class="flex-1 w-full rounded-lg py-2 pl-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
								placeholder={$i18n.t('API Key')}
								bind:value={TTS_API_KEY}
								required
							/>
						</div>
					</div>
				{:else if TTS_ENGINE === 'azure'}
					<div>
						<div class="mt-1 flex gap-2 mb-1">
							<input
								class="flex-1 w-full rounded-lg py-2 pl-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
								placeholder={$i18n.t('API Key')}
								bind:value={TTS_API_KEY}
								required
							/>
							<input
								class="flex-1 w-full rounded-lg py-2 pl-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
								placeholder={$i18n.t('Azure Region')}
								bind:value={TTS_AZURE_SPEECH_REGION}
								required
							/>
						</div>
					</div>
				{/if}

				<hr class=" dark:border-gray-850 my-2" />

				{#if TTS_ENGINE === ''}
					<div>
						<div class=" mb-1.5 text-sm font-medium">{$i18n.t('TTS Voice')}</div>
						<div class="flex w-full">
							<div class="flex-1">
								<select
									class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
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
										class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
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
							<div class=" mb-1.5 text-sm font-medium">{$i18n.t('TTS Model')}</div>
							<div class="flex w-full">
								<div class="flex-1">
									<input
										list="tts-model-list"
										class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
										bind:value={TTS_MODEL}
										placeholder="Select a model"
									/>

									<datalist id="tts-model-list">
										{#each models as model}
											<option value={model.id} />
										{/each}
									</datalist>
								</div>
							</div>
						</div>
					</div>
				{:else if TTS_ENGINE === 'elevenlabs'}
					<div class=" flex gap-2">
						<div class="w-full">
							<div class=" mb-1.5 text-sm font-medium">{$i18n.t('TTS Voice')}</div>
							<div class="flex w-full">
								<div class="flex-1">
									<input
										list="voice-list"
										class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
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
							<div class=" mb-1.5 text-sm font-medium">{$i18n.t('TTS Model')}</div>
							<div class="flex w-full">
								<div class="flex-1">
									<input
										list="tts-model-list"
										class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
										bind:value={TTS_MODEL}
										placeholder="Select a model"
									/>

									<datalist id="tts-model-list">
										{#each models as model}
											<option value={model.id} />
										{/each}
									</datalist>
								</div>
							</div>
						</div>
					</div>
				{:else if TTS_ENGINE === 'azure'}
					<div class=" flex gap-2">
						<div class="w-full">
							<div class=" mb-1.5 text-sm font-medium">{$i18n.t('TTS Voice')}</div>
							<div class="flex w-full">
								<div class="flex-1">
									<input
										list="voice-list"
										class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
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
							<div class=" mb-1.5 text-sm font-medium">
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
										class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
										bind:value={TTS_AZURE_SPEECH_OUTPUT_FORMAT}
										placeholder="Select a output format"
									/>
								</div>
							</div>
						</div>
					</div>
				{/if}

				<hr class="dark:border-gray-850 my-2" />

				<div class="pt-0.5 flex w-full justify-between">
					<div class="self-center text-xs font-medium">{$i18n.t('Response splitting')}</div>
					<div class="flex items-center relative">
						<select
							class="dark:bg-gray-900 w-fit pr-8 cursor-pointer rounded px-2 p-1 text-xs bg-transparent outline-none text-right"
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
			class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
