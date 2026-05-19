<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { config, socket } from '$lib/stores';
	import { toast } from 'svelte-sonner';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import VideoStream from './VideoStream.svelte';
	import { createConnection, ConnectionType } from './Connection';
	import type { UserMediaStream } from './Connection/base';

	export let channelId = '';
	export let enableVideo = true;
	export let enableAudio = true;
	export let screenSharing = false;
	export let onScreenShareStopped: () => void = () => {};

	let localStream: MediaStream | null = null;
	let localVideoEl: HTMLVideoElement;
	let localScreenVideoEl: HTMLVideoElement;
	let remoteAudioEl: HTMLAudioElement;

	const connection = createConnection(ConnectionType.SFU);

	let connected = false;
	let remoteVideoStreams: UserMediaStream[] = [];
	let remoteAudioStream: MediaStream = new MediaStream();
	let localScreenStream: MediaStream | null = null;

	const unsubConnected = connection.connected.subscribe((v) => (connected = v));
	const unsubVideoStreams = connection.remoteVideoStreams.subscribe(
		(v) => (remoteVideoStreams = v)
	);
	const unsubAudioStream = connection.remoteAudioStream.subscribe((v) => (remoteAudioStream = v));
	const unsubLocalScreenStream = connection.localScreenStream.subscribe(
		(v) => (localScreenStream = v)
	);
	const unsubError = connection.error.subscribe((msg) => {
		if (msg) {
			toast.error(msg);
			connection.error.set(null);
		}
	});

	$: if (localVideoEl && localStream) {
		if (localVideoEl.srcObject !== localStream) {
			localVideoEl.srcObject = localStream;
			localVideoEl.play().catch(() => {});
		}
	}

	$: if (remoteAudioEl && remoteAudioStream) {
		if (remoteAudioEl.srcObject !== remoteAudioStream) {
			remoteAudioEl.srcObject = remoteAudioStream;
			remoteAudioEl.play().catch(() => {});
		}
	}

	$: if (localScreenVideoEl && localScreenStream) {
		if (localScreenVideoEl.srcObject !== localScreenStream) {
			localScreenVideoEl.srcObject = localScreenStream;
			localScreenVideoEl.play().catch(() => {});
		}
	}

	$: connection.setTrackEnabled('audio', enableAudio);
	$: connection.setTrackEnabled('video', enableVideo);

	let previousScreenSharing = false;
	$: if (screenSharing !== previousScreenSharing) {
		previousScreenSharing = screenSharing;
		if (screenSharing) {
			connection.startScreenShare(onScreenShareStopped).catch(() => {
				// user cancelled or getDisplayMedia failed — reset the parent's flag
				onScreenShareStopped();
			});
		} else {
			connection.stopScreenShare();
		}
	}

	const initHandler = async () => {
		try {
			localStream = await navigator.mediaDevices.getUserMedia({
				video: enableVideo,
				audio: enableAudio
			});
		} catch (err: any) {
			// if video+audio failed, retry audio-only before giving up
			if (enableVideo && enableAudio) {
				try {
					localStream = await navigator.mediaDevices.getUserMedia({
						video: false,
						audio: true
					});
					enableVideo = false;
					toast.warning('Camera unavailable — joining with audio only');
				} catch {
					toast.error('Could not access microphone');
					return;
				}
			} else if (err.name === 'NotAllowedError') {
				toast.error('Camera/microphone permission was denied');
				return;
			} else if (err.name === 'NotFoundError') {
				toast.error('No camera or microphone found');
				return;
			} else {
				toast.error(`Could not access media devices: ${err.message}`);
				return;
			}
		}

		const iceServers = $config?.features?.ice_servers ?? [];

		connection.init({
			channelId,
			localStream,
			socket: $socket!,
			iceServers
		});
	};

	onMount(() => {
		initHandler();
	});

	onDestroy(() => {
		localStream?.getTracks().forEach((t) => t.stop());
		localStream = null;
		connection.destroy();
		unsubConnected();
		unsubVideoStreams();
		unsubAudioStream();
		unsubLocalScreenStream();
		unsubError();
	});
</script>

<div class="relative w-full h-full bg-gray-950 flex flex-col">
	<!-- remote streams grid; pt-8 compensates for Navbar's -mb-8 overlap -->
	<div class="flex-1 min-h-0 flex items-center justify-center p-4 pt-10">
		{#if !connected}
			<div class="flex flex-col items-center gap-3">
				<Spinner className="size-6 text-gray-400" />
			</div>
		{:else if remoteVideoStreams.length === 0}
			<div class="text-gray-500 text-sm">You're alone here.</div>
		{:else}
			<div
				class="grid gap-3 w-full h-full place-items-center"
				style="grid-template-columns: repeat({Math.min(
					remoteVideoStreams.length,
					3
				)}, 1fr); grid-template-rows: repeat({Math.ceil(remoteVideoStreams.length / 3)}, 1fr);"
			>
				{#each remoteVideoStreams as entry (entry.stream.id)}
					<div class="w-full h-full min-h-0 min-w-0 overflow-hidden">
						<VideoStream {entry} />
					</div>
				{/each}
			</div>
		{/if}
	</div>

	<!-- hidden audio element for all remote audio -->
	<!-- svelte-ignore a11y-media-has-caption -->
	<audio autoplay bind:this={remoteAudioEl}></audio>

	<!-- local preview overlay -->
	<div class="absolute bottom-20 right-4 flex flex-col gap-3 items-end">
		{#if enableVideo && localStream?.getVideoTracks().length}
			<div class="w-44 rounded-xl overflow-hidden shadow-xl border border-gray-700/50 bg-gray-900">
				<video
					class="w-full aspect-video object-cover"
					autoplay
					playsinline
					muted
					bind:this={localVideoEl}
				></video>
			</div>
		{/if}
		{#if localScreenStream}
			<div class="w-44 rounded-xl overflow-hidden shadow-xl border border-gray-700/50 bg-gray-900">
				<video
					class="w-full aspect-video object-cover"
					autoplay
					playsinline
					muted
					bind:this={localScreenVideoEl}
				></video>
			</div>
		{/if}
	</div>
</div>
