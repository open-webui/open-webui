// In the <script> section of Message.svelte

// ... other imports
import { activeTTSAudio } from '$lib/stores/ttsStore.js'; // ADD THIS
import { get } from 'svelte/store';                         // ADD THIS
import { getTTS, cancelTTS } from '$lib/apis/v1/tts';

// ... other variables

// REPLACE the existing 'speak' function and its related variables with this:
let audioLoading = false;

const speak = async () => {
	const currentAudio = get(activeTTSAudio);

	// If the audio for THIS message is already playing, stop it.
	if (currentAudio && currentAudio.id === `tts-${message.id}`) {
		currentAudio.pause();
		activeTTSAudio.set(null);
	} else {
		// If some other audio is playing, stop it first.
		if (currentAudio) {
			currentAudio.pause();
		}

		try {
			audioLoading = true;
			const [newAudio, error] = await getTTS(
				$page.data.models.find((m) => m.id === message.model)?.name ?? message.model,
				message.content
			);

			if (error) {
				alert(error);
				activeTTSAudio.set(null);
				return;
			}
			
			if (newAudio) {
				newAudio.id = `tts-${message.id}`; // Assign a unique ID to the audio object
				activeTTSAudio.set(newAudio); // Put the new audio object in the store
				newAudio.play();

				newAudio.addEventListener('ended', () => {
					// Check if the current audio in the store is still this one before clearing
					if (get(activeTTSAudio)?.id === `tts-${message.id}`) {
						activeTTSAudio.set(null);
					}
				});
				newAudio.addEventListener('pause', () => {
				    // This handles external pauses, like from the stopActiveTTS function
					if (get(activeTTSAudio)?.id === `tts-${message.id}`) {
						activeTTSAudio.set(null);
					}
				});
			}
		} catch (error) {
			console.error(error);
			activeTTSAudio.set(null);
		} finally {
			audioLoading = false;
		}
	}
};


// In the HTML part of Message.svelte, update the button logic to react to the store

// ... button element ...
<button ... on:click={speak} ...>
    {#if $activeTTSAudio && $activeTTSAudio.id === `tts-${message.id}`}
        <StopCircleIcon class="w-4 h-4" />
        <Tooltip>Stop</Tooltip>
    {:else if audioLoading}
        {:else}
        <SpeakerWaveIcon class="w-4 h-4" />
        <Tooltip>Text-to-Speech</Tooltip>
    {/if}
</button>