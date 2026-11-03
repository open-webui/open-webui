<script lang="ts">
	import { getContext, onDestroy } from 'svelte';
	import { toast } from 'svelte-sonner';
	import type { TerminalConnection } from '$lib/apis/terminal';
	import { openTerminalSocket } from '$lib/apis/terminal/socket';
	import Icon from '../FileNav/Icon.svelte';

	const i18n = getContext<any>('i18n');
	export let connection: TerminalConnection;
	export let chatId: string | null;
	export let fullscreenEnabled: boolean;
	const mime = 'audio/webm; codecs="opus"';
	let audio: HTMLAudioElement | null = null;
	let socket: WebSocket | null = null;
	let buffer: SourceBuffer | null = null;
	let queue: ArrayBuffer[] = [];
	let queuedBytes = 0;
	let url = '';

	const stop = () => {
		if (socket) {
			socket.onopen = socket.onmessage = socket.onclose = null;
			socket.close();
			socket = null;
		}
		if (buffer) buffer.onupdateend = buffer.onerror = null;
		buffer = null;
		queue = [];
		queuedBytes = 0;
		if (audio) {
			audio.onerror = null;
			audio.pause();
			audio.removeAttribute('src');
			audio.load();
			audio = null;
		}
		URL.revokeObjectURL(url);
		url = '';
	};
	const failed = () => {
		stop();
		toast.error($i18n.t('Desktop audio unavailable.'));
	};
	const append = () => {
		if (!audio || !buffer || buffer.updating) return;
		try {
			if (buffer.buffered.length) {
				const end = buffer.buffered.end(buffer.buffered.length - 1);
				// Stay near live audio and discard played media in long sessions.
				if (end - audio.currentTime > 0.5) audio.currentTime = end - 0.15;
				if (audio.currentTime - buffer.buffered.start(0) > 10) {
					buffer.remove(0, audio.currentTime - 5);
					return;
				}
			}
			const packet = queue.shift();
			if (packet) {
				queuedBytes -= packet.byteLength;
				buffer.appendBuffer(packet);
			}
		} catch {
			failed();
		}
	};
	const toggle = () => {
		if (audio) return stop();
		if (typeof MediaSource === 'undefined' || !MediaSource.isTypeSupported(mime)) {
			toast.error($i18n.t('Desktop audio is not supported by this browser.'));
			return;
		}
		const current = new Audio();
		audio = current;
		try {
			const source = new MediaSource();
			url = URL.createObjectURL(source);
			current.src = url;
			current.onerror = failed;
			source.addEventListener(
				'sourceopen',
				() => {
					if (audio !== current) return;
					try {
						buffer = source.addSourceBuffer(mime);
						buffer.onupdateend = append;
						buffer.onerror = failed;
						socket = openTerminalSocket(connection, chatId, '/desktop/audio');
						socket.onmessage = (event) => {
							if (!(event.data instanceof ArrayBuffer) || !event.data.byteLength) return failed();
							queuedBytes += event.data.byteLength;
							if (queuedBytes > 65536) return failed();
							queue.push(event.data);
							append();
						};
						socket.onclose = failed;
					} catch {
						failed();
					}
				},
				{ once: true }
			);
			void current.play().catch(() => {
				if (audio === current) failed();
			});
		} catch {
			failed();
		}
	};
	onDestroy(stop);
</script>

<button
	type="button"
	class="absolute top-1.5 flex h-6 w-6 items-center justify-center rounded-md text-gray-400/70 hover:bg-white/80 hover:text-gray-700 focus-visible:bg-white/80 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 dark:hover:bg-gray-900/80 dark:hover:text-gray-200 dark:focus-visible:bg-gray-900/80 {fullscreenEnabled
		? 'right-9'
		: 'right-1.5'}"
	aria-label={$i18n.t('Desktop audio')}
	aria-pressed={audio !== null}
	title={audio ? $i18n.t('Mute') : $i18n.t('Unmute')}
	on:click={toggle}
>
	<Icon name="speaker" size={12} />
	{#if !audio}<span class="absolute h-px w-4 -rotate-45 bg-current"></span>{/if}
</button>
