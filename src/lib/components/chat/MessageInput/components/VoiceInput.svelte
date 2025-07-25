<script lang="ts">
	import { createEventDispatcher, getContext, onDestroy } from 'svelte';
	import { toast } from 'svelte-sonner';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	
	import VoiceRecording from '../VoiceRecording.svelte';
	import Headphone from '$lib/components/icons/Headphone.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { settings, config } from '$lib/stores';
	import type { VoiceRecordingState } from '../types';
	
	export let recording = false;
	export let voiceEnabled = true;
	export let ttsEnabled = false;
	export let sttEnabled = false;
	
	const i18n: Writable<i18nType> = getContext('i18n');
	const dispatch = createEventDispatcher();
	
	let mediaRecorder: MediaRecorder | null = null;
	let audioChunks: Blob[] = [];
	let recordingStartTime = 0;
	
	$: voiceEnabled = sttEnabled && (
		$settings?.voice?.stt?.engine !== '' ||
		$config?.stt?.engine !== '' ||
		$settings?.voice?.stt?.enabled
	);
	
	$: ttsEnabled = 
		($config?.tts?.engine ?? false) ||
		($config?.audio?.tts?.engine ?? false) ||
		($settings?.voice?.tts?.enabled ?? false);
	
	async function startRecording() {
		try {
			const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
			mediaRecorder = new MediaRecorder(stream);
			audioChunks = [];
			
			mediaRecorder.ondataavailable = (event) => {
				if (event.data.size > 0) {
					audioChunks.push(event.data);
				}
			};
			
			mediaRecorder.onstop = async () => {
				const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
				const duration = Date.now() - recordingStartTime;
				
				dispatch('recordingComplete', { 
					blob: audioBlob, 
					duration: Math.floor(duration / 1000) 
				});
				
				// Clean up
				stream.getTracks().forEach(track => track.stop());
			};
			
			mediaRecorder.start();
			recordingStartTime = Date.now();
			recording = true;
			
			dispatch('recordingStart');
		} catch (error) {
			console.error('Failed to start recording:', error);
			toast.error($i18n.t('Failed to access microphone'));
		}
	}
	
	function stopRecording() {
		if (mediaRecorder && mediaRecorder.state !== 'inactive') {
			mediaRecorder.stop();
			recording = false;
			dispatch('recordingStop');
		}
	}
	
	function toggleRecording() {
		if (recording) {
			stopRecording();
		} else {
			startRecording();
		}
	}
	
	function toggleTTS() {
		dispatch('toggleTTS', { enabled: !ttsEnabled });
	}
	
	onDestroy(() => {
		if (recording) {
			stopRecording();
		}
	});
</script>

<div class="flex items-center gap-1">
	{#if voiceEnabled}
		<VoiceRecording
			bind:recording
			on:start={startRecording}
			on:stop={stopRecording}
		/>
	{/if}
	
	{#if ttsEnabled}
		<Tooltip content={$i18n.t('Text-to-Speech')}>
			<button
				type="button"
				class="p-1.5 rounded-lg transition-colors text-gray-500 hover:bg-gray-100 
					   dark:text-gray-400 dark:hover:bg-gray-800"
				on:click={toggleTTS}
			>
				<Headphone class="w-4 h-4" />
			</button>
		</Tooltip>
	{/if}
</div>