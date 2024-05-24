<script lang="ts">
	import { getAudioConfig, updateAudioConfig } from '$lib/apis/audio';
	import { user } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	export let saveSettings: Function;

	// Audio

	let OpenAIUrl = '';
	let OpenAIKey = '';

	let STTEngines = ['', 'openai'];
	let STTEngine = '';

	let conversationMode = false;
	let speechAutoSend = false;
	let responseAutoPlayback = false;

	let TTSEngines = ['', 'openai'];
	let TTSEngine = '';

	let voices = [];
	let speaker = '';
	let models = [];
	let model = '';

	const getOpenAIVoices = () => {
		voices = [
			{ name: 'alloy' },
			{ name: 'echo' },
			{ name: 'fable' },
			{ name: 'onyx' },
			{ name: 'nova' },
			{ name: 'shimmer' }
		];
	};

	const getOpenAIVoicesModel = () => {
		models = [{ name: 'tts-1' }, { name: 'tts-1-hd' }];
	};

	const getWebAPIVoices = () => {
		const getVoicesLoop = setInterval(async () => {
			voices = await speechSynthesis.getVoices();

			// do your loop
			if (voices.length > 0) {
				clearInterval(getVoicesLoop);
			}
		}, 100);
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

	const updateConfigHandler = async () => {
		if (TTSEngine === 'openai') {
			const res = await updateAudioConfig(localStorage.token, {
				url: OpenAIUrl,
				key: OpenAIKey,
				model: model,
				speaker: speaker
			});

			if (res) {
				OpenAIUrl = res.OPENAI_API_BASE_URL;
				OpenAIKey = res.OPENAI_API_KEY;
				model = res.OPENAI_API_MODEL;
				speaker = res.OPENAI_API_VOICE;
			}
		}
	};

	onMount(async () => {
		let settings = JSON.parse(localStorage.getItem('settings') ?? '{}');

		conversationMode = settings.conversationMode ?? false;
		speechAutoSend = settings.speechAutoSend ?? false;
		responseAutoPlayback = settings.responseAutoPlayback ?? false;

		STTEngine = settings?.audio?.STTEngine ?? '';
		TTSEngine = settings?.audio?.TTSEngine ?? '';
		speaker = settings?.audio?.speaker ?? '';
		model = settings?.audio?.model ?? '';

		if (TTSEngine === 'openai') {
			getOpenAIVoices();
			getOpenAIVoicesModel();
		} else {
			getWebAPIVoices();
		}

		if ($user.role === 'admin') {
			const res = await getAudioConfig(localStorage.token);

			if (res) {
				OpenAIUrl = res.OPENAI_API_BASE_URL;
				OpenAIKey = res.OPENAI_API_KEY;
				model = res.OPENAI_API_MODEL;
				speaker = res.OPENAI_API_VOICE;
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
								getOpenAIVoices();
								speaker = 'alloy';
								model = 'tts-1';
							} else {
								getWebAPIVoices();
								speaker = '';
							}
						}}
					>
						<option value="">{$i18n.t('Default (Web API)')}</option>
						<option value="openai">{$i18n.t('Open AI')}</option>
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
