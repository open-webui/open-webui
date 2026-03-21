<script lang="ts">
	import Microphone from '../../icons/Microphone.svelte';
	import MicrophoneOff from '../../icons/MicrophoneOff.svelte';
	import VideoCamera from '../../icons/VideoCamera.svelte';
	import VideoCameraOff from '../../icons/VideoCameraOff.svelte';
	import PhoneHangup from '../../icons/PhoneHangup.svelte';

	export let videoEnabled = true;
	export let audioEnabled = true;

	export let onToggleVideo = (enabled: boolean) => {};
	export let onToggleAudio = (enabled: boolean) => {};
	export let onHangup = () => {};
</script>

<div class="w-full flex items-center justify-center gap-3 p-4">
	<button
		class="p-3 rounded-full bg-red-500/80 hover:bg-red-500 text-white transition"
		on:click={onHangup}
		title="Hang up"
	>
		<PhoneHangup className="size-5" />
	</button>

	<button
		class="p-3 rounded-full transition {audioEnabled
			? 'bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200'
			: 'bg-red-500 text-white'}"
		on:click={() => {
			audioEnabled = !audioEnabled;
			onToggleAudio(audioEnabled);
		}}
	>
		{#if audioEnabled}
			<Microphone className="size-5" />
		{:else}
			<MicrophoneOff className="size-5" />
		{/if}
	</button>

	<button
		class="p-3 rounded-full transition {videoEnabled
			? 'bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200'
			: 'bg-red-500 text-white'}"
		on:click={() => {
			videoEnabled = !videoEnabled;
			onToggleVideo(videoEnabled);
		}}
	>
		{#if videoEnabled}
			<VideoCamera className="size-5" />
		{:else}
			<VideoCameraOff className="size-5" />
		{/if}
	</button>
</div>
