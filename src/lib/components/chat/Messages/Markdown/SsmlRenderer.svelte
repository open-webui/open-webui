<script lang="ts">
	import type { i18n as i18nType } from 'i18next';
	import { getContext } from 'svelte';
	import { type Writable } from 'svelte/store';

	const i18n = getContext<Writable<i18nType>>('i18n');

	import { settings, showCallOverlay } from '$lib/stores';

	import VoiceVisualiser from './VoiceVisualiser.svelte';

	import { TTSElement, TTSManager } from '$lib/utils/tts';

	export let content: string;
	const formattedContent = content
		.replace(/<[^>]*>/g, '')
		.replace(/\s*\n\s*|\s+/g, ' ')
		.replace(/\s+([.,!?;:])/g, '$1')
		.replace(/([.,!?;:])(?=\S)/g, '$1 ')
		.trim();

	export let done: boolean;

	let tts: undefined | TTSElement;

	let queuedSpeech = false;
	let loadingSpeech = false;
	let speaking = false;

	const toggleSpeakMessage = () => {
		if (tts && (queuedSpeech || loadingSpeech || speaking)) {
			TTSManager.cancel(tts);
			return;
		}

		tts = new TTSElement(content, true);

		tts.onLoading = () => {
			queuedSpeech = false;
			loadingSpeech = true;
		};
		tts.onSpeaking = () => {
			loadingSpeech = false;
			speaking = true;
		};
		tts.onFinish = () => {
			speaking = false;
		};
		tts.onCancel = () => {
			queuedSpeech = false;
			loadingSpeech = false;
			speaking = false;
		};

		queuedSpeech = true;
		TTSManager.queue(tts);
	};

	let showingTranscript = false;

	if (
		($settings?.audio?.ssml?.autoplay ?? $config.audio.ssml.autoplay) &&
		!($showCallOverlay && !($settings.audio?.ssml.overrideCall ?? $config.audio.ssml.overrideCall)) &&
		!done
	) {
		toggleSpeakMessage();
	}
</script>

{#if $settings?.audio?.ssml?.show ?? $config.audio.ssml.show}
	<div class="rounded-xl bg-gray-50 dark:bg-gray-850 w-fit my-1 p-2 flex flex-col">
		<button
			class="visible p-1.5 w-fit hover:bg-black/5 dark:hover:bg-white/5 rounded-lg dark:hover:text-white hover:text-black transition"
			aria-label={$i18n.t('Read Aloud')}
			on:click={toggleSpeakMessage}
		>
			<div class="flex flex-row items-center gap-1.5">
				{#if queuedSpeech}
					<svg
						fill="none"
						viewBox="0 0 24 24"
						aria-hidden="true"
						stroke-width="2.3"
						stroke="currentColor"
						class="w-4 h-4"
					>
						<path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6l4 2" />
						<circle cx="12" cy="12" r="10" />
					</svg>
				{:else if loadingSpeech}
					<svg
						class=" w-4 h-4"
						fill="currentColor"
						viewBox="0 0 24 24"
						aria-hidden="true"
						xmlns="http://www.w3.org/2000/svg"
					>
						<style>
							.spinner_S1WN {
								animation: spinner_MGfb 0.8s linear infinite;
								animation-delay: -0.8s;
							}

							.spinner_Km9P {
								animation-delay: -0.65s;
							}

							.spinner_JApP {
								animation-delay: -0.5s;
							}

							@keyframes spinner_MGfb {
								93.75%,
								100% {
									opacity: 0.2;
								}
							}
						</style>
						<circle class="spinner_S1WN" cx="4" cy="12" r="3" />
						<circle class="spinner_S1WN spinner_Km9P" cx="12" cy="12" r="3" />
						<circle class="spinner_S1WN spinner_JApP" cx="20" cy="12" r="3" />
					</svg>
				{:else if speaking}
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						aria-hidden="true"
						stroke-width="2.3"
						stroke="currentColor"
						class="w-4 h-4"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M17.25 9.75 19.5 12m0 0 2.25 2.25M19.5 12l2.25-2.25M19.5 12l-2.25 2.25m-10.5-6 4.72-4.72a.75.75 0 0 1 1.28.53v15.88a.75.75 0 0 1-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.009 9.009 0 0 1 2.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75Z"
						/>
					</svg>
				{:else}
					<svg
						xmlns="http://www.w3.org/2000/svg"
						fill="none"
						viewBox="0 0 24 24"
						aria-hidden="true"
						stroke-width="2.3"
						stroke="currentColor"
						class="w-4 h-4"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M19.114 5.636a9 9 0 010 12.728M16.463 8.288a5.25 5.25 0 010 7.424M6.75 8.25l4.72-4.72a.75.75 0 011.28.53v15.88a.75.75 0 01-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 012.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75z"
						/>
					</svg>
				{/if}

				<VoiceVisualiser className="w-40 h-8" animating={!loadingSpeech && speaking} />
			</div>
		</button>

		<button
			type="button"
			class="w-fit no-underline text-xs hover:underline cursor-pointer text-gray-400"
			on:click={() => {
				showingTranscript = !showingTranscript;
			}}
			aria-label={$i18n.t(showingTranscript ? 'Hide Transcript' : 'Show Transcript')}
		>
			{showingTranscript ? 'Hide transcript' : 'Show transcript'}
		</button>
		{#if showingTranscript}
			<div class="text-sm text-gray-300 break-words p-1 max-w-96">{formattedContent}</div>
		{/if}
	</div>
{/if}
