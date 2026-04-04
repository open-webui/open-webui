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

	let localStream: MediaStream | null = null;
	let localVideoEl: HTMLVideoElement;
	let remoteAudioEl: HTMLAudioElement;

	const connection = createConnection(ConnectionType.SFU);

	// subscribe to connection stores
	let connected = false;
	let remoteVideoStreams: UserMediaStream[] = [];
	let remoteAudioStream: MediaStream = new MediaStream();

	const unsubConnected = connection.connected.subscribe((v) => (connected = v));
	const unsubVideoStreams = connection.remoteVideoStreams.subscribe((v) => (remoteVideoStreams = v));
	const unsubAudioStream = connection.remoteAudioStream.subscribe((v) => (remoteAudioStream = v));
	const unsubError = connection.error.subscribe((msg) => {
		if (msg) {
			toast.error(msg);
			connection.error.set(null);
		}
	});

	// sync local preview
	$: if (localVideoEl && localStream) {
		if (localVideoEl.srcObject !== localStream) {
			localVideoEl.srcObject = localStream;
			localVideoEl.play().catch(() => {});
		}
	}

	// sync remote audio
	$: if (remoteAudioEl && remoteAudioStream) {
		if (remoteAudioEl.srcObject !== remoteAudioStream) {
			remoteAudioEl.srcObject = remoteAudioStream;
			remoteAudioEl.play().catch(() => {});
		}
	}

	// toggle local tracks
	$: if (localStream) {
		localStream.getAudioTracks().forEach((t) => (t.enabled = enableAudio));
		localStream.getVideoTracks().forEach((t) => (t.enabled = enableVideo));
	}

	const initHandler = async () => {
		try {
			localStream = await navigator.mediaDevices.getUserMedia({
				video: enableVideo,
				audio: enableAudio
			});
		} catch (err: any) {
			if (err.name === 'NotAllowedError') {
				toast.error('Camera/microphone permission was denied');
			} else if (err.name === 'NotFoundError') {
				toast.error('No camera or microphone found');
			} else {
				toast.error(`Could not access media devices: ${err.message}`);
			}
			return;
		}

		console.log(
			'[call] creating connection with local media:',
			localStream.getTracks().map((t) => t.kind)
		);

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
				{#each remoteVideoStreams as { stream, user } (stream.id)}
					<div class="w-full h-full min-h-0 min-w-0 overflow-hidden">
						<VideoStream {stream} {user} />
					</div>
				{/each}
			</div>
		{/if}
	</div>

	<!-- hidden audio element for all remote audio -->
	<!-- svelte-ignore a11y-media-has-caption -->
	<audio autoplay bind:this={remoteAudioEl}></audio>

	<!-- local preview overlay -->
	<div
		class="absolute bottom-20 right-4 w-44 rounded-xl overflow-hidden shadow-xl border border-gray-700/50 bg-gray-900"
	>
		<video
			class="w-full aspect-video object-cover"
			autoplay
			playsinline
			muted
			bind:this={localVideoEl}
		></video>
	</div>
</div>
