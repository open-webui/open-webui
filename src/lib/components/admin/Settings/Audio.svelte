<script lang="ts">
	import { getAudioConfig, updateAudioConfig } from '$lib/apis/audio';
	import { user, settings, config } from '$lib/stores';
	import { createEventDispatcher, onMount, getContext } from 'svelte';
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

	const getOpenAIModels = () => {
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

	const updateConfigHandler = async () => {
		const res = await updateAudioConfig(localStorage.token, {
			tts: {
				OPENAI_API_BASE_URL: TTS_OPENAI_API_BASE_URL,
				OPENAI_API_KEY: TTS_OPENAI_API_KEY,
				ENGINE: TTS_ENGINE,
				MODEL: TTS_MODEL,
				VOICE: TTS_VOICE
			},
			stt: {
				OPENAI_API_BASE_URL: STT_OPENAI_API_BASE_URL,
				OPENAI_API_KEY: STT_OPENAI_API_KEY,
				ENGINE: STT_ENGINE,
				MODEL: STT_MODEL
			}
		});

		if (res) {
			toast.success('Audio settings updated successfully');

			config.set(await getBackendConfig());
		}
	};

	onMount(async () => {
		const res = await getAudioConfig(localStorage.token);

		if (res) {
			console.log(res);
			TTS_OPENAI_API_BASE_URL = res.tts.OPENAI_API_BASE_URL;
			TTS_OPENAI_API_KEY = res.tts.OPENAI_API_KEY;

			TTS_ENGINE = res.tts.ENGINE;
			TTS_MODEL = res.tts.MODEL;
			TTS_VOICE = res.tts.VOICE;

			STT_OPENAI_API_BASE_URL = res.stt.OPENAI_API_BASE_URL;
			STT_OPENAI_API_KEY = res.stt.OPENAI_API_KEY;

			STT_ENGINE = res.stt.ENGINE;
			STT_MODEL = res.stt.MODEL;
		}

		if (TTS_ENGINE === 'openai') {
			getOpenAIVoices();
			getOpenAIModels();
		} else {
			getWebAPIVoices();
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
							on:change={(e) => {
								if (e.target.value === 'openai') {
									getOpenAIVoices();
									TTS_VOICE = 'alloy';
									TTS_MODEL = 'tts-1';
								} else {
									getWebAPIVoices();
									TTS_VOICE = '';
								}
							}}
						>
							<option value="">{$i18n.t('Web API')}</option>
							<option value="openai">{$i18n.t('Open AI')}</option>
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
