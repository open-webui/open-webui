import { writable, get } from 'svelte/store';

export const ttsState = writable({
    speakingIdx: undefined as number | undefined,
    isSpeaking: false,
    isLoading: false,
    audioParts: {} as Record<number, HTMLAudioElement | null>,
    currentMessageId: undefined as string | number | undefined,
});

// helper to play a given audio segment sequentially
export const playAudio = (idx: number) => {
    console.debug(`Speaking part ${idx + 1} of ${Object.keys(get(ttsState).audioParts).length}`);
    return new Promise<void>((res) => {
        
        const audio = get(ttsState).audioParts[idx];
        if (!audio) return res();
        
        ttsState.update(state => ({
            ...state,
            speakingIdx: idx,
            isSpeaking: true,
            isLoading: false,
        }));

        audio.play();
        audio.onended = async () => {
            await new Promise((r) => setTimeout(r, 300));
            if (Object.keys(get(ttsState).audioParts).length - 1 === idx) {
                ttsState.update(state => ({
                    ...state,
                    isSpeaking: false,
                }));
            }
            res();
        };
    });
};

// utility to fully stop all sounds and reset state
export const stopAllAudio = () => {
    try {
        speechSynthesis.cancel();
        Object.values(get(ttsState).audioParts).forEach((audio) => {
            if (audio) {
                audio.pause();
                audio.currentTime = 0;
            }
        });

        ttsState.update(state => ({
            ...state,
            speakingIdx: undefined,
            isSpeaking: false,
            isLoading: false,
            audioParts: {},
        }));
    } catch (error) {
        console.error(error);
    }
};