<script lang="ts">
	import type { UserMediaStream } from './Connection/base';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	export let entry: UserMediaStream;

	let videoEl: HTMLVideoElement;
	let videoPlaying = false;

	$: if (videoEl && entry.stream) {
		if (videoEl.srcObject !== entry.stream) {
			videoPlaying = false;
			videoEl.srcObject = entry.stream;
			videoEl.play().catch((err) => {
				console.warn(`[call] VideoStream play() failed trackId=${entry.trackId}`, err);
			});
		}
	}

	$: videoLive = entry.state === 'on' && videoPlaying;
</script>

<div class="relative w-full h-full flex items-center justify-center p-2">
	<video
		class="w-full h-full object-contain rounded-xl border border-gray-700/50 bg-gray-900 shadow-lg"
		class:hidden={!videoLive}
		autoplay
		playsinline
		muted
		bind:this={videoEl}
		on:playing={() => (videoPlaying = true)}
	></video>

	{#if !videoLive && entry.user}
		<div
			class="absolute inset-0 flex items-center justify-center rounded-xl border border-gray-700/50 bg-gray-900 shadow-lg"
		>
			<img
				class="size-20 rounded-full object-cover"
				src={`${WEBUI_API_BASE_URL}/users/${entry.user.id}/profile/image`}
				alt={entry.user.name}
			/>
		</div>
	{/if}

	{#if entry.user}
		<div
			class="absolute bottom-4 left-4 flex items-center gap-2 bg-black/60 backdrop-blur-sm rounded-lg px-2.5 py-1.5"
		>
			<span class="text-white text-xs font-medium truncate max-w-[120px]">
				{entry.user.name}
			</span>
		</div>
	{/if}
</div>
