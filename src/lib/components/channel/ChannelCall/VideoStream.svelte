<script lang="ts">
	import type { UserInfo } from './Connection/base';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	export let stream: MediaStream;
	export let user: UserInfo | null = null;

	let videoEl: HTMLVideoElement;
	let videoLive = false;

	$: if (videoEl && stream) {
		if (videoEl.srcObject !== stream) {
			videoEl.srcObject = stream;
			videoEl.play().catch(() => {});
		}

		// detect whether the video track is actively producing frames
		const videoTrack = stream.getVideoTracks()[0];
		if (videoTrack) {
			videoLive = videoTrack.enabled && !videoTrack.muted && videoTrack.readyState === 'live';

			videoTrack.onmute = () => (videoLive = false);
			videoTrack.onunmute = () => (videoLive = true);
			videoTrack.onended = () => (videoLive = false);
		} else {
			videoLive = false;
		}
	}
</script>

<div class="relative w-full h-full flex items-center justify-center p-2">
	<video
		class="w-full h-full object-contain rounded-xl border border-gray-700/50 bg-gray-900 shadow-lg"
		class:hidden={!videoLive}
		autoplay
		playsinline
		muted
		bind:this={videoEl}
	></video>

	{#if !videoLive && user}
		<!-- centered profile image when stream is loading or camera is off -->
		<div class="absolute inset-0 flex items-center justify-center rounded-xl border border-gray-700/50 bg-gray-900 shadow-lg">
			<img
				class="size-20 rounded-full object-cover"
				src={`${WEBUI_API_BASE_URL}/users/${user.id}/profile/image`}
				alt={user.name}
			/>
		</div>
	{/if}

	{#if user}
		<!-- bottom-left username overlay -->
		<div class="absolute bottom-4 left-4 flex items-center gap-2 bg-black/60 backdrop-blur-sm rounded-lg px-2.5 py-1.5">
			<span class="text-white text-xs font-medium truncate max-w-[120px]">
				{user.name}
			</span>
		</div>
	{/if}
</div>
