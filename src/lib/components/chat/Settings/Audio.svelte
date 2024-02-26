<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	const dispatch = createEventDispatcher();

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

	onMount(async () => {
		let settings = JSON.parse(localStorage.getItem('settings') ?? '{}');

		conversationMode = settings.conversationMode ?? false;
		speechAutoSend = settings.speechAutoSend ?? false;
		responseAutoPlayback = settings.responseAutoPlayback ?? false;

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
			<div class=" mb-1 text-sm font-medium">STT Settings</div>

			<div class=" py-0.5 flex w-full justify-between">
				<div class=" self-center text-xs font-medium">Speech-to-Text Engine</div>
				<div class="flex items-center relative">
					<select
						class="w-fit pr-8 rounded px-2 p-1 text-xs bg-transparent outline-none text-right"
						bind:value={STTEngine}
						placeholder="Select a mode"
						on:change={(e) => {
							if (e.target.value !== '') {
								navigator.mediaDevices.getUserMedia({ audio: true }).catch(function (err) {
									toast.error(`Permission denied when accessing microphone: ${err}`);
									STTEngine = '';
								});
							}
						}}
					>
						<option value="">Default (Web API)</option>
						<option value="whisper-local">Whisper (Local)</option>
					</select>
				</div>
			</div>

			<div class=" py-0.5 flex w-full justify-between">
				<div class=" self-center text-xs font-medium">Conversation Mode</div>

				<button
					class="p-1 px-3 text-xs flex rounded transition"
					on:click={() => {
						toggleConversationMode();
					}}
					type="button"
				>
					{#if conversationMode === true}
						<span class="ml-2 self-center">On</span>
					{:else}
						<span class="ml-2 self-center">Off</span>
					{/if}
				</button>
			</div>

			<div class=" py-0.5 flex w-full justify-between">
				<div class=" self-center text-xs font-medium">Auto-send input after 3 sec.</div>

				<button
					class="p-1 px-3 text-xs flex rounded transition"
					on:click={() => {
						toggleSpeechAutoSend();
					}}
					type="button"
				>
					{#if speechAutoSend === true}
						<span class="ml-2 self-center">On</span>
					{:else}
						<span class="ml-2 self-center">Off</span>
					{/if}
				</button>
			</div>
		</div>

		<div>
			<div class=" mb-1 text-sm font-medium">TTS Settings</div>

			<div class=" py-0.5 flex w-full justify-between">
				<div class=" self-center text-xs font-medium">Text-to-Speech Engine</div>
				<div class="flex items-center relative">
					<select
						class="w-fit pr-8 rounded px-2 p-1 text-xs bg-transparent outline-none text-right"
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
						<option value="">Default (Web API)</option>
						<option value="openai">Open AI</option>
					</select>
				</div>
			</div>

			<div class=" py-0.5 flex w-full justify-between">
				<div class=" self-center text-xs font-medium">Auto-playback response</div>

				<button
					class="p-1 px-3 text-xs flex rounded transition"
					on:click={() => {
						toggleResponseAutoPlayback();
					}}
					type="button"
				>
					{#if responseAutoPlayback === true}
						<span class="ml-2 self-center">On</span>
					{:else}
						<span class="ml-2 self-center">Off</span>
					{/if}
				</button>
			</div>
		</div>

		<hr class=" dark:border-gray-700" />

		{#if TTSEngine === ''}
			<div>
				<div class=" mb-2.5 text-sm font-medium">Set Voice</div>
				<div class="flex w-full">
					<div class="flex-1">
						<select
							class="w-full rounded py-2 px-4 text-sm dark:text-gray-300 dark:bg-gray-800 outline-none"
							bind:value={speaker}
							placeholder="Select a voice"
						>
							<option value="" selected>Default</option>
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
				<div class=" mb-2.5 text-sm font-medium">Set Voice</div>
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
			class=" px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-gray-100 transition rounded"
			type="submit"
		>
			Save
		</button>
	</div>
</form>
