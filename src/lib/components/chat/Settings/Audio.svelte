<script lang="ts">
	import { createEventDispatcher, onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	const dispatch = createEventDispatcher();

	const i18n = getContext('i18n');

	export let saveSettings: Function;

	// Audio

	let STTEngines = ['', 'openai'];
	let STTEngine = '';

	let conversationMode = false;
	let speechAutoSend = false;
	let responseAutoPlayback = false;

	let TTSEngines = ['', 'openai'];
	let TTSEngine = '';

	let voices = [];
	let speaker = '';
	let volume = '';
	let speechRate = '';
	let pitch = '';
	let notificationsPlayback = false;

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

	const toggleNotificationsPlayback = async () => {
		notificationsPlayback = !notificationsPlayback;
		saveSettings({ notificationsPlayback: notificationsPlayback });
	};

	onMount(async () => {
		let settings = JSON.parse(localStorage.getItem('settings') ?? '{}');

		conversationMode = settings.conversationMode ?? false;
		speechAutoSend = settings.speechAutoSend ?? false;
		responseAutoPlayback = settings.responseAutoPlayback ?? false;
		notificationsPlayback = settings.notificationsPlayback ?? false;

		STTEngine = settings?.audio?.STTEngine ?? '';
		TTSEngine = settings?.audio?.TTSEngine ?? '';
		speaker = settings?.audio?.speaker ?? '';

		if (TTSEngine === 'openai') {
			getOpenAIVoices();
		} else {
			getWebAPIVoices();
		}
	});
</script>

<form
	class="flex flex-col h-full justify-between space-y-3 text-sm"
	on:submit|preventDefault={() => {
		saveSettings({
			audio: {
				STTEngine: STTEngine !== '' ? STTEngine : undefined,
				TTSEngine: TTSEngine !== '' ? TTSEngine : undefined,
				speaker: speaker !== '' ? speaker : undefined
			}
		});
		dispatch('save');
	}}
>
	<div class=" space-y-3 pr-1.5 overflow-y-scroll max-h-80">
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

			<div class=" py-0.5 w-full justify-between">
				<div class="flex w-full justify-between">
					<div class=" self-center text-xs font-medium">{$i18n.t('Volume')}</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
						type="button"
						on:click={() => {
							volume = volume === '' ? 0.8 : '';
						}}
					>
						{#if volume === ''}
							<span class="ml-2 self-center"> {$i18n.t('Default')} </span>
						{:else}
							<span class="ml-2 self-center"> {$i18n.t('Custom')} </span>
						{/if}
					</button>
				</div>

				{#if volume !== ''}
					<div class="flex mt-0.5 space-x-2">
						<div class=" flex-1">
							<input
								id="steps-range"
								type="range"
								min="0.1"
								max="1"
								step="0.01"
								bind:value={volume}
								class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
							/>
						</div>
						<div>
							<input
								bind:value={volume}
								type="number"
								class=" bg-transparent text-center w-14"
								min="0.1"
								max="1"
								step="0.01"
							/>
						</div>
					</div>
				{/if}
			</div>

			<div class=" py-0.5 w-full justify-between">
				<div class="flex w-full justify-between">
					<div class=" self-center text-xs font-medium">{$i18n.t('Speech Rate')}</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
						type="button"
						on:click={() => {
							speechRate = speechRate === '' ? 100 : '';
						}}
					>
						{#if speechRate === ''}
							<span class="ml-2 self-center"> {$i18n.t('Default')} </span>
						{:else}
							<span class="ml-2 self-center"> {$i18n.t('Custom')} </span>
						{/if}
					</button>
				</div>

				{#if speechRate !== ''}
					<div class="flex mt-0.5 space-x-2">
						<div class=" flex-1">
							<input
								id="steps-range"
								type="range"
								min="1"
								max="100"
								step="0.01"
								bind:value={speechRate}
								class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
							/>
						</div>
						<div>
							<input
								bind:value={speechRate}
								type="number"
								class=" bg-transparent text-center w-14"
								min="1"
								max="100"
								step="0.01"
							/>
						</div>
					</div>
				{/if}
			</div>

			<div class=" py-0.5 w-full justify-between">
				<div class="flex w-full justify-between">
					<div class=" self-center text-xs font-medium">{$i18n.t('Pitch')}</div>

					<button
						class="p-1 px-3 text-xs flex rounded transition"
						type="button"
						on:click={() => {
							pitch = pitch === '' ? 100 : '';
						}}
					>
						{#if pitch === ''}
							<span class="ml-2 self-center"> {$i18n.t('Default')} </span>
						{:else}
							<span class="ml-2 self-center"> {$i18n.t('Custom')} </span>
						{/if}
					</button>
				</div>

				{#if pitch !== ''}
					<div class="flex mt-0.5 space-x-2">
						<div class=" flex-1">
							<input
								id="steps-range"
								type="range"
								min="0"
								max="100"
								step="0.01"
								bind:value={pitch}
								class="w-full h-2 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
							/>
						</div>
						<div>
							<input
								bind:value={pitch}
								type="number"
								class=" bg-transparent text-center w-14"
								min="0"
								max="100"
								step="0.01"
							/>
						</div>
					</div>
				{/if}
			</div>

			<div class=" py-0.5 flex w-full justify-between">
				<div class=" self-center text-xs font-medium">
					{$i18n.t('Enable Notifications Playback')}
				</div>

				<button
					class="p-1 px-3 text-xs flex rounded transition"
					on:click={() => {
						toggleNotificationsPlayback();
					}}
					type="button"
				>
					{#if notificationsPlayback === true}
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
							class="w-full rounded py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none"
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
						<select
							class="w-full rounded py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none"
							bind:value={speaker}
							placeholder="Select a voice"
						>
							{#each voices as voice}
								<option value={voice.name} class="bg-gray-100 dark:bg-gray-700">{voice.name}</option
								>
							{/each}
						</select>
					</div>
				</div>
			</div>
		{/if}
	</div>

	<div class="flex justify-end pt-3 text-sm font-medium">
		<button
			class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
			type="submit"
		>
			{$i18n.t('Save')}
		</button>
	</div>
</form>
