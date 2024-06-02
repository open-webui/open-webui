<script lang="ts">
	import { getAudioConfig, updateAudioConfig, updateOpenAIAudioConfig } from '$lib/apis/audio';
	import { Alltalk } from '$lib/apis/audio/providers/alltalk/Alltalk';
	import { user, settings } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	export let saveSettings: Function;

	let alltalk: Alltalk = new Alltalk();

	// Audio

	let OpenAIUrl = '';
	let OpenAIKey = '';

	let STTEngines = ['', 'openai'];
	let STTEngine = '';

	let conversationMode = false;
	let speechAutoSend = false;
	let responseAutoPlayback = false;

	let TTSEngines = ['', 'openai', 'alltalk'];
	let TTSEngine = '';

	let voices = [];
	let speaker = '';
	let models = [];
	let model = '';

	const TTSEngineConfig = {
		openai: {
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
		},
		webapi: {
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
			alltalk.baseUrl = config.ALLTALK_API_BASE_URL;
			alltalk.currentVoice = config.ALLTALK_API_VOICE;
			alltalk.currentModel = config.ALLTALK_API_MODEL;
			alltalk.useDeepSpeed = config.ALLTALK_API_DEEPSPEED;
			alltalk.useLowVRAM = config.ALLTALK_API_LOW_VRAM;
			alltalk.setup();
		}
	};

	const updateConfigHandler = async () => {
		if (TTSEngine === 'openai') {
			const res = await updateAudioConfig(TTSEngine, localStorage.token, {
				url: OpenAIUrl,
				key: OpenAIKey,
				model: model,
				speaker: speaker
			});

			if (res) {
				assignConfig(res, 'openai');
			}
		}else if(TTSEngine === 'alltalk'){
			const res = await updateAudioConfig(TTSEngine, localStorage.token, {
				url: alltalk.baseUrl,
				model: model,
				speaker: alltalk.currentVoice,
				deepspeed: alltalk.useDeepSpeed,
				low_vram: alltalk.useLowVRAM
			});
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
		speaker = $settings?.audio?.speaker ?? '';
		model = $settings?.audio?.model ?? '';

		if (TTSEngine === 'openai') {
			TTSEngineConfig[TTSEngine].getVoices();
			TTSEngineConfig[TTSEngine].getModels();
		} else if(TTSEngine === 'alltalk'){
			await alltalk.setup();
			model = alltalk.currentModel;
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
				speaker: speaker !== '' ? speaker : undefined,
				model: model !== '' ? model : undefined
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
						on:change={(e) => {
							if (e.target.value === 'openai') {
								TTSEngineConfig.openai.getVoices();
								speaker = 'alloy';
								model = 'tts-1';
							} else if(TTSEngine === 'alltalk'){
								alltalk.getVoices();
								speaker = alltalk.currentVoice;
								model = alltalk.getModels();
							} else {
								TTSEngineConfig.webapi.getVoices();
								speaker = '';
							}
						}}
					>
						<!-- TODO iterate in a list -->
						<option value="">{$i18n.t('Default (Web API)')}</option>
						<option value="openai">{$i18n.t('Open AI')}</option>
						<option value="alltalk">{$i18n.t('All Talk TTS')}</option>
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
					<div class="mt-1 flex gap-2 mb-1">
						<input
							class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
							placeholder={$i18n.t('API Base URL')}
							bind:value={alltalk.baseUrl}
							required
						/>
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
							placeholder="Select a voice"
						>
							<option value="" selected>{$i18n.t('Default')}</option>
							{#each voices.filter((v) => v.localService === true) as voice}
								<option value={voice.name} class="bg-gray-100 dark:bg-gray-700">{voice.name}</option
								>
							{/each}
						</select>
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
							bind:value={speaker}
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
				<div class="flex w-full">
					<div class="flex-1">
						<input
							list="voice-list"
							class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
							bind:value={alltalk.currentVoice}
							placeholder="Select a voice"
						/>

						<datalist id="voice-list">
							{#each alltalk?.voicesList as voice}
								<option value={voice} />
							{/each}
						</datalist>
					</div>
					<button
						class="px-2.5 bg-gray-100 hover:bg-gray-200 text-gray-800 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-100 rounded-lg transition"
						type="button"
						on:click={() => {
							alltalk.getPreviewVoice(alltalk.currentVoice);
						}}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M17.25 9.75 19.5 12m0 0 2.25 2.25M19.5 12l2.25-2.25M19.5 12l-2.25 2.25m-10.5-6 4.72-4.72a.75.75 0 0 1 1.28.53v15.88a.75.75 0 0 1-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.009 9.009 0 0 1 2.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75Z"
							/>
						</svg>
					</button>
				</div>
			</div>
			<div>
				<div class=" mb-2.5 text-sm font-medium">{$i18n.t('Set Model')}</div>
				<div class="flex w-full">
					<div class="flex-1">
						<input
							list="model-list"
							class="w-full rounded-lg py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
							bind:value={alltalk.currentModel}
							placeholder="Select a model"
						/>

						<datalist id="model-list">
							{#each alltalk?.modelList as model}
								<option value={model} />
							{/each}
						</datalist>
					</div>
				</div>
			</div>
			<div class=" py-0.5 flex w-full justify-between">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('deepspeed status')}
				</div>

				<button
					class="p-1 px-3 text-xs flex rounded transition"
					on:click={() => {
						alltalk.useDeepSpeed = !alltalk.useDeepSpeed;
					}}
					type="button"
				>
					{#if alltalk.useDeepSpeed === true}
						<span class="ml-2 self-center">{$i18n.t('On')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Off')}</span>
					{/if}
				</button>
			</div>
			<div class=" py-0.5 flex w-full justify-between">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('use low vram mode')}
				</div>

				<button
					class="p-1 px-3 text-xs flex rounded transition"
					on:click={() => {
						alltalk.useLowVRAM = !alltalk.useLowVRAM;
					}}
					type="button"
				>
					{#if alltalk.useLowVRAM === true}
						<span class="ml-2 self-center">{$i18n.t('On')}</span>
					{:else}
						<span class="ml-2 self-center">{$i18n.t('Off')}</span>
					{/if}
				</button>
			</div>
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
