<script lang="ts">
	import { _alltalk, getAudioConfig, updateAudioConfig } from '$lib/apis/audio';
	import { user, settings } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { toast } from 'svelte-sonner';
	import Switch from '$lib/components/common/Switch.svelte';
	import { AllTalkConfigForm } from '$lib/apis/audio/providers/alltalk/Alltalk';
	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	export let saveSettings: Function;

	// Audio

	let OpenAIUrl = '';
	let OpenAIKey = '';
	let OpenAISpeaker = '';

	let STTEngines = ['', 'openai'];
	let STTEngine = '';

	let conversationMode = false;
	let speechAutoSend = false;
	let responseAutoPlayback = false;
	let nonLocalVoices = false;

	let TTSEngines = ['', 'openai', 'alltalk'];
	let TTSEngine = '';

	let voices = [];
	let speaker = '';
	let models = [];
	let model = '';

	const TTSEngineConfig = {
		webapi: {
			label: 'Default (Web API)',
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

	const toggleConversationMode = async () => {
		conversationMode = !conversationMode;

		if (conversationMode) {
			responseAutoPlayback = true;
			speechAutoSend = true;
		}

		saveSettings({
			conversationMode: conversationMode,
			responseAutoPlayback: responseAutoPlayback,
			speechAutoSend: speechAutoSend
		});
	};

	const toggleResponseAutoPlayback = async () => {
		responseAutoPlayback = !responseAutoPlayback;
		saveSettings({ responseAutoPlayback: responseAutoPlayback });
	};

	const toggleSpeechAutoSend = async () => {
		speechAutoSend = !speechAutoSend;
		saveSettings({ speechAutoSend: speechAutoSend });
	};

	const assignConfig = (config: any, provider: string) => {
		if (provider === 'openai') {
			OpenAIUrl = config.OPENAI_API_BASE_URL;
			OpenAIKey = config.OPENAI_API_KEY;
			model = config.OPENAI_API_MODEL;
			speaker = config.OPENAI_API_VOICE;
		}else if(provider === 'alltalk'){
			console.log("alltalk config: ", config);
			_alltalk.baseUrl = config.ALLTALK_API_BASE_URL;
			_alltalk.currentVoice = config.ALLTALK_API_VOICE;
			_alltalk.currentModel = config.ALLTALK_API_MODEL;
			_alltalk.useDeepSpeed = config.ALLTALK_API_DEEPSPEED;
			_alltalk.useLowVRAM = config.ALLTALK_API_LOW_VRAM;
			_alltalk.useStreamingMode = config.ALLTALK_API_USE_STREAMING;
			_alltalk.useNarrator = config.ALLTALK_API_USE_NARRATOR;
			_alltalk.narratorVoice = config.ALLTALK_API_NARRATOR_VOICE;
			_alltalk.setup();
		}
	};

	const updateConfigHandler = async () => {
		if (TTSEngine === 'openai') {
			const res = await updateAudioConfig(TTSEngine, localStorage.token, {
				url: OpenAIUrl,
				key: OpenAIKey,
				model: model,
				speaker: OpenAISpeaker
			});

			if (res) {
				assignConfig(res, 'openai');
			}
		}else if(TTSEngine === 'alltalk'){
			const res = await updateAudioConfig(TTSEngine, localStorage.token,
				new AllTalkConfigForm(
					_alltalk.baseUrl,
					_alltalk.currentModel,
					_alltalk.currentVoice,
					_alltalk.useDeepSpeed,
					_alltalk.useLowVRAM,
					_alltalk.useStreamingMode,
					_alltalk.useNarrator,
					_alltalk.narratorVoice
				)
			);
			assignConfig(res, 'alltalk');
			console.log("updating alltalk config: ", res);
		}
	};

	onMount(async () => {
		conversationMode = $settings.conversationMode ?? false;
		speechAutoSend = $settings.speechAutoSend ?? false;
		responseAutoPlayback = $settings.responseAutoPlayback ?? false;

		STTEngine = $settings?.audio?.STTEngine ?? '';
		TTSEngine = $settings?.audio?.TTSEngine ?? '';
		nonLocalVoices = $settings.audio?.nonLocalVoices ?? false;
		speaker = $settings?.audio?.speaker ?? '';
		model = $settings?.audio?.model ?? '';

		if (TTSEngine === 'openai') {
			TTSEngineConfig[TTSEngine].getVoices();
			TTSEngineConfig[TTSEngine].getModels();
		} else if(TTSEngine === 'alltalk'){
			await _alltalk.setup();
			model = _alltalk.currentModel;
			console.log("alltalk model: ", model);
		} else {
			TTSEngineConfig.webapi.getVoices();
		}

		if ($user.role === 'admin') {
			const res = await getAudioConfig(localStorage.token);

			if (res) {
				assignConfig(res.openai, 'openai');
				assignConfig(res.alltalk, 'alltalk');
			}
		}
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={async () => {
		if ($user.role === 'admin') {
			await updateConfigHandler();
		}
		saveSettings({
			audio: {
				STTEngine: STTEngine !== '' ? STTEngine : undefined,
				TTSEngine: TTSEngine !== '' ? TTSEngine : undefined,
				speaker:
					(TTSEngine === 'openai' ? OpenAISpeaker : speaker) !== ''
						? TTSEngine === 'openai'
							? OpenAISpeaker
							: speaker
						: undefined,
				model: model !== '' ? model : undefined,
				nonLocalVoices: nonLocalVoices
			}
		});
		dispatch('save');
	}}
>
	<div class=" space-y-3 pr-1.5 overflow-y-scroll max-h-[25rem]">
		<div>
			<div class=" mb-1 text-sm font-medium">{$i18n.t('STT Settings')}</div>

			<div class=" py-0.5 flex w-full justify-between">
				<div class=" self-center text-xs font-medium">{$i18n.t('Speech-to-Text Engine')}</div>
				<div class="flex items-center relative">
					<select
						class="dark:bg-gray-900 w-fit pr-8 rounded px-2 p-1 text-xs bg-transparent outline-none text-right"
						bind:value={STTEngine}
						placeholder="Select a mode"
						on:change={(e) => {
							if (e.target.value !== '') {
								navigator.mediaDevices.getUserMedia({ audio: true }).catch(function (err) {
									toast.error(
										$i18n.t(`Permission denied when accessing microphone: {{error}}`, {
											error: err
										})
									);
									STTEngine = '';
								});
							}
						}}
					>
						<option value="">{$i18n.t('Default (Web API)')}</option>
						<option value="whisper-local">{$i18n.t('Whisper (Local)')}</option>
					</select>
				</div>
			</div>

			<div class=" py-0.5 flex w-full justify-between">
				<div class=" self-center text-xs font-medium">{$i18n.t('Conversation Mode')}</div>

				<button
					class="p-1 px-3 text-xs flex rounded transition"
					on:click={() => {
						toggleConversationMode();
					}}
					type="button"
				>
					{#if conversationMode === true}
						<span class="ml-2 self-center">{$i18n.t('On')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Off')}</span>
					{/if}
				</button>
			</div>

			<div class=" py-0.5 flex w-full justify-between">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Auto-send input after 3 sec.')}
				</div>

				<button
					class="p-1 px-3 text-xs flex rounded transition"
					on:click={() => {
						toggleSpeechAutoSend();
					}}
					type="button"
				>
					{#if speechAutoSend === true}
						<span class="ml-2 self-center">{$i18n.t('On')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Off')}</span>
					{/if}
				</button>
			</div>
		</div>

		<div>
			<div class=" mb-1 text-sm font-medium">{$i18n.t('TTS Settings')}</div>

			<div class=" py-0.5 flex w-full justify-between">
				<div class=" self-center text-xs font-medium">{$i18n.t('Text-to-Speech Engine')}</div>
				<div class="flex items-center relative">
					<select
						class=" dark:bg-gray-900 w-fit pr-8 rounded px-2 p-1 text-xs bg-transparent outline-none text-right"
						bind:value={TTSEngine}
						placeholder="Select a mode"
						on:change={async (e) => {
							if (e.target.value === 'openai') {
								TTSEngineConfig.openai.getVoices();
								OpenAISpeaker = 'alloy';
								model = 'tts-1';
							} else if(TTSEngine === 'alltalk'){
								await _alltalk.getVoices();
								speaker = _alltalk.currentVoice;
								await _alltalk.getModels();
								console.log("alltalk model 2: ", model);
							} else {
								TTSEngineConfig.webapi.getVoices();
								speaker = '';
							}
						}}
					>
						{#each Object.keys(TTSEngineConfig) as engineName}
							<option value="{engineName}">{$i18n.t(TTSEngineConfig[engineName].label)}</option>
						{/each}
					</select>
				</div>
			</div>

			{#if $user.role === 'admin'}
				{#if TTSEngine === 'openai'}
					<div class="mt-1 flex gap-2 mb-1">
						<input
							class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
							placeholder={$i18n.t('API Base URL')}
							bind:value={OpenAIUrl}
							required
						/>

						<input
							class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
							placeholder={$i18n.t('API Key')}
							bind:value={OpenAIKey}
							required
						/>
					</div>
				{:else if TTSEngine === 'alltalk'}
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
			{/if}

			<div class=" py-0.5 flex w-full justify-between">
				<div class=" self-center text-xs font-medium">{$i18n.t('Auto-playback response')}</div>

				<button
					class="p-1 px-3 text-xs flex rounded transition"
					on:click={() => {
						toggleResponseAutoPlayback();
					}}
					type="button"
				>
					{#if responseAutoPlayback === true}
						<span class="ml-2 self-center">{$i18n.t('On')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Off')}</span>
					{/if}
				</button>
			</div>
		</div>

		<hr class=" dark:border-gray-700" />

		{#if TTSEngine === ''}
			<div>
				<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Set Voice')}</div>
				<div class="flex w-full">
					<div class="flex-1">
						<select
							class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
							bind:value={speaker}
						>
							<option value="" selected={speaker !== ''}>{$i18n.t('Default')}</option>
							{#each voices.filter((v) => nonLocalVoices || v.localService === true) as voice}
								<option
									value={voice.name}
									class="bg-gray-100 dark:bg-gray-700"
									selected={speaker === voice.name}>{voice.name}</option
								>
							{/each}
						</select>
					</div>
				</div>
				<div class="flex items-center justify-between mb-1">
					<div class="text-sm">
						{$i18n.t('Allow non-local voices')}
					</div>

					<div class="mt-1">
						<Switch bind:state={nonLocalVoices} />
					</div>
				</div>
			</div>
		{:else if TTSEngine === 'openai'}
			<div>
				<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Set Voice')}</div>
				<div class="flex w-full">
					<div class="flex-1">
						<input
							list="voice-list"
							class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
							bind:value={OpenAISpeaker}
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
			<div>
				<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Set Model')}</div>
				<div class="flex w-full">
					<div class="flex-1">
						<input
							list="model-list"
							class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
							bind:value={model}
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
		{:else if TTSEngine === 'alltalk'}
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

	<div class="flex justify-end text-sm font-medium">
		<button
			class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
