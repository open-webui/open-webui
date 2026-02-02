<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { KokoroTTS } from 'kokoro-js';

	import { user, settings, config } from '$lib/stores';
	import { getVoices as _getVoices } from '$lib/apis/audio';

	import Switch from '$lib/components/common/Switch.svelte';
	import { round } from '@huggingface/transformers';
	import Spinner from '$lib/components/common/Spinner.svelte';
	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	export let saveSettings: Function;

	// Audio
	let conversationMode = false;
	let speechAutoSend = false;
	let responseAutoPlayback = false;
	let nonLocalVoices = false;

	let STTEngine = '';

	let TTSEngine = '';
	let TTSEngineConfig = {};

	let TTSModel = null;
	let TTSModelProgress = null;
	let TTSModelLoading = false;

	let voices = [];
	let voice = '';

	// Audio speed control
	let playbackRate = 1;
	const speedOptions = [2, 1.75, 1.5, 1.25, 1, 0.75, 0.5];

	const getVoices = async () => {
		if (TTSEngine === 'browser-kokoro') {
			if (!TTSModel) {
				await loadKokoro();
			}

			voices = Object.entries(TTSModel.voices).map(([key, value]) => {
				return {
					id: key,
					name: value.name,
					localService: false
				};
			});
		} else {
			if ($config.audio.tts.engine === '') {
				const getVoicesLoop = setInterval(async () => {
					voices = await speechSynthesis.getVoices();

					// do your loop
					if (voices.length > 0) {
						clearInterval(getVoicesLoop);
					}
				}, 100);
			} else {
				const res = await _getVoices(localStorage.token).catch((e) => {
					toast.error(`${e}`);
				});

				if (res) {
					console.log(res);
					voices = res.voices;
				}
			}
		}
	};

	const toggleResponseAutoPlayback = async () => {
		responseAutoPlayback = !responseAutoPlayback;
		saveSettings({ responseAutoPlayback: responseAutoPlayback });
	};

	const toggleSpeechAutoSend = async () => {
		speechAutoSend = !speechAutoSend;
		saveSettings({ speechAutoSend: speechAutoSend });
	};

	onMount(async () => {
		playbackRate = $settings.audio?.tts?.playbackRate ?? 1;
		conversationMode = $settings.conversationMode ?? false;
		speechAutoSend = $settings.speechAutoSend ?? false;
		responseAutoPlayback = $settings.responseAutoPlayback ?? false;

		STTEngine = $settings?.audio?.stt?.engine ?? '';

		TTSEngine = $settings?.audio?.tts?.engine ?? '';
		TTSEngineConfig = $settings?.audio?.tts?.engineConfig ?? {};

		if ($settings?.audio?.tts?.defaultVoice === $config.audio.tts.voice) {
			voice = $settings?.audio?.tts?.voice ?? $config.audio.tts.voice ?? '';
		} else {
			voice = $config.audio.tts.voice ?? '';
		}

		nonLocalVoices = $settings.audio?.tts?.nonLocalVoices ?? false;

		await getVoices();
	});

	$: if (TTSEngine && TTSEngineConfig) {
		onTTSEngineChange();
	}

	const onTTSEngineChange = async () => {
		if (TTSEngine === 'browser-kokoro') {
			await loadKokoro();
		}
	};

	const loadKokoro = async () => {
		if (TTSEngine === 'browser-kokoro') {
			voices = [];

			if (TTSEngineConfig?.dtype) {
				TTSModel = null;
				TTSModelProgress = null;
				TTSModelLoading = true;

				const model_id = 'onnx-community/Kokoro-82M-v1.0-ONNX';

				TTSModel = await KokoroTTS.from_pretrained(model_id, {
					dtype: TTSEngineConfig.dtype, // Options: "fp32", "fp16", "q8", "q4", "q4f16"
					device: !!navigator?.gpu ? 'webgpu' : 'wasm', // Detect WebGPU
					progress_callback: (e) => {
						TTSModelProgress = e;
						console.log(e);
					}
				});

				await getVoices();

				// const rawAudio = await tts.generate(inputText, {
				// 	// Use `tts.list_voices()` to list all available voices
				// 	voice: voice
				// });

				// const blobUrl = URL.createObjectURL(await rawAudio.toBlob());
				// const audio = new Audio(blobUrl);

				// audio.play();
			}
		}
	};
</script>

<form
	class="flex flex-col h-full justify-between"
	on:submit|preventDefault={async () => {
		saveSettings({
			audio: {
				stt: {
					engine: STTEngine !== '' ? STTEngine : undefined
				},
				tts: {
					engine: TTSEngine !== '' ? TTSEngine : undefined,
					engineConfig: TTSEngineConfig,
					playbackRate: playbackRate,
					voice: voice !== '' ? voice : undefined,
					defaultVoice: $config?.audio?.tts?.voice ?? '',
					nonLocalVoices: $config.audio.tts.engine === '' ? nonLocalVoices : undefined
				}
			}
		});
		dispatch('save');
	}}
>
	<div class="space-y-6 overflow-y-auto">
		<!-- STT Settings Section -->
		<div class="space-y-4">
			<div>
				<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-1">
					{$i18n.t('STT Settings')}
				</h3>
				<p class="text-sm text-gray-500 dark:text-gray-400">
					Configure speech-to-text recognition
				</p>
			</div>

			{#if $config.audio.stt.engine !== 'web'}
				<!-- Speech-to-Text Engine -->
				<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
					<div class="flex items-center justify-between">
						<div>
							<div class="text-sm font-medium text-gray-900 dark:text-white">
								{$i18n.t('Speech-to-Text Engine')}
							</div>
							<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
								Select your preferred STT engine
							</div>
						</div>
						<select
							class="bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
							bind:value={STTEngine}
						>
							<option value="">{$i18n.t('Default')}</option>
							<option value="web">{$i18n.t('Web API')}</option>
						</select>
					</div>
				</div>
			{/if}

			<!-- Auto-Send After Transcription -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Instant Auto-Send After Voice Transcription')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Automatically send message after speech recognition
						</div>
					</div>
					<button
						class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 {speechAutoSend
							? 'bg-blue-600'
							: 'bg-gray-300 dark:bg-gray-700'}"
						on:click={() => {
							toggleSpeechAutoSend();
						}}
						type="button"
					>
						<span
							class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {speechAutoSend
								? 'translate-x-6'
								: 'translate-x-1'}"
						/>
					</button>
				</div>
			</div>
		</div>

		<!-- TTS Settings Section -->
		<div class="space-y-4 pt-2">
			<div>
				<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-1">
					{$i18n.t('TTS Settings')}
				</h3>
				<p class="text-sm text-gray-500 dark:text-gray-400">
					Configure text-to-speech synthesis
				</p>
			</div>

			<!-- Text-to-Speech Engine -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Text-to-Speech Engine')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Select your preferred TTS engine
						</div>
					</div>
					<select
						class="bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
						bind:value={TTSEngine}
					>
						<option value="">{$i18n.t('Default')}</option>
						<option value="browser-kokoro">{$i18n.t('Kokoro.js (Browser)')}</option>
					</select>
				</div>
			</div>

			{#if TTSEngine === 'browser-kokoro'}
				<!-- Kokoro.js Dtype -->
				<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
					<div class="flex items-center justify-between">
						<div>
							<div class="text-sm font-medium text-gray-900 dark:text-white">
								{$i18n.t('Kokoro.js Dtype')}
							</div>
							<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
								Data type precision for model computation
							</div>
						</div>
						<select
							class="bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
							bind:value={TTSEngineConfig.dtype}
						>
							<option value="" disabled selected>Select dtype</option>
							<option value="fp32">fp32</option>
							<option value="fp16">fp16</option>
							<option value="q8">q8</option>
							<option value="q4">q4</option>
						</select>
					</div>
				</div>
			{/if}

			<!-- Auto-playback Response -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Auto-playback response')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Automatically play audio for AI responses
						</div>
					</div>
					<button
						class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 {responseAutoPlayback
							? 'bg-blue-600'
							: 'bg-gray-300 dark:bg-gray-700'}"
						on:click={() => {
							toggleResponseAutoPlayback();
						}}
						type="button"
					>
						<span
							class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform {responseAutoPlayback
								? 'translate-x-6'
								: 'translate-x-1'}"
						/>
					</button>
				</div>
			</div>

			<!-- Playback Speed -->
			<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
				<div class="flex items-center justify-between">
					<div>
						<div class="text-sm font-medium text-gray-900 dark:text-white">
							{$i18n.t('Speech Playback Speed')}
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
							Adjust audio playback speed
						</div>
					</div>
					<select
						class="bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
						bind:value={playbackRate}
					>
						{#each speedOptions as option}
							<option value={option} selected={playbackRate === option}>{option}x</option>
						{/each}
					</select>
				</div>
			</div>
		</div>

		<!-- Voice Selection Section -->
		<div class="space-y-4 pt-2">
			<div>
				<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-1">
					{$i18n.t('Set Voice')}
				</h3>
				<p class="text-sm text-gray-500 dark:text-gray-400">
					Choose your preferred voice for text-to-speech
				</p>
			</div>

			{#if TTSEngine === 'browser-kokoro'}
				{#if TTSModel}
					<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
						<input
							list="voice-list"
							class="w-full px-3 py-2 text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
							bind:value={voice}
							placeholder="Select a voice"
						/>

						<datalist id="voice-list">
							{#each voices as voice}
								<option value={voice.id}>{voice.name}</option>
							{/each}
						</datalist>
					</div>
				{:else}
					<div
						class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4"
					>
						<div class="flex items-start gap-3">
							<div class="flex-shrink-0 mt-0.5">
								<Spinner className="size-5" />
							</div>
							<div class="flex-1">
								<div class="text-sm font-medium text-blue-900 dark:text-blue-100 mb-1 shimmer">
									{$i18n.t('Loading Kokoro.js...')}
									{TTSModelProgress && TTSModelProgress.status === 'progress'
										? `(${Math.round(TTSModelProgress.progress * 10) / 10}%)`
										: ''}
								</div>
								<div class="text-xs text-blue-800 dark:text-blue-200">
									{$i18n.t('Please do not close the settings page while loading the model.')}
								</div>
							</div>
						</div>
					</div>
				{/if}
			{:else if $config.audio.tts.engine === ''}
				<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4 space-y-3">
					<select
						class="w-full px-3 py-2 text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
						bind:value={voice}
					>
						<option value="" selected={voice !== ''}>{$i18n.t('Default')}</option>
						{#each voices.filter((v) => nonLocalVoices || v.localService === true) as _voice}
							<option value={_voice.name} selected={voice === _voice.name}>{_voice.name}</option>
						{/each}
					</select>

					<div class="flex items-center justify-between pt-2 border-t border-gray-200 dark:border-gray-700">
						<div class="text-xs text-gray-600 dark:text-gray-400">
							{$i18n.t('Allow non-local voices')}
						</div>
						<Switch bind:state={nonLocalVoices} />
					</div>
				</div>
			{:else if $config.audio.tts.engine !== ''}
				<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
					<input
						list="voice-list"
						class="w-full px-3 py-2 text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-700 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
						bind:value={voice}
						placeholder="Select a voice"
					/>

					<datalist id="voice-list">
						{#each voices as voice}
							<option value={voice.id}>{voice.name}</option>
						{/each}
					</datalist>
				</div>
			{/if}
		</div>
	</div>

	<!-- Save Button -->
	<div class="flex justify-end pt-6 border-t border-gray-200 dark:border-gray-700 mt-6">
		<button
			class="px-6 py-2.5 text-sm font-medium bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors shadow-sm hover:shadow-md focus:outline-none focus:ring-2 focus:ring-orange-500 focus:ring-offset-2"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>

<style>
	/* Custom scrollbar styling */
	::-webkit-scrollbar {
		width: 8px;
		height: 8px;
	}

	::-webkit-scrollbar-track {
		background: transparent;
	}

	::-webkit-scrollbar-thumb {
		background: rgba(156, 163, 175, 0.5);
		border-radius: 4px;
	}

	::-webkit-scrollbar-thumb:hover {
		background: rgba(156, 163, 175, 0.7);
	}

	:global(.dark) ::-webkit-scrollbar-thumb {
		background: rgba(75, 85, 99, 0.5);
	}

	:global(.dark) ::-webkit-scrollbar-thumb:hover {
		background: rgba(75, 85, 99, 0.7);
	}
</style>