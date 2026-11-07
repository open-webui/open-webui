<script lang="ts">
	import { getContext, onMount, tick } from 'svelte';
	import NativeDesktop from './NativeDesktop.svelte';
	import DesktopAudio from './DesktopAudio.svelte';
	import { toast } from 'svelte-sonner';
	import type RFB from '@novnc/novnc';
	import Icon from '../FileNav/Icon.svelte';
	import { terminalRequest, type TerminalConnection } from '$lib/apis/terminal';
	import { openTerminalSocket } from '$lib/apis/terminal/socket';

	const i18n = getContext<any>('i18n');
	export let connection: TerminalConnection;
	export let chatId: string | null = null;
	export let active = true;
	export let overlay = false;
	let mounted = false;
	let container: HTMLDivElement;
	let fullscreen = false;
	let fullscreenEnabled = false;
	let surface: HTMLDivElement;
	let native: NativeDesktop;
	let transport = 'vnc';
	let audioAvailable = false;
	const send = (message: Record<string, unknown>) => {
		if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(message));
	};
	let socket: WebSocket | null = null;
	let viewer: RFB | null = null;
	let error = '';
	let status = '';
	let generation = 0;
	let connecting = false;
	let retry: ReturnType<typeof setTimeout>;

	const syncFullscreenCursor = () => {
		const cursor = viewer?._cursor._canvas;
		// noVNC's touch cursor lives on body, outside the fullscreen panel.
		if (cursor?.isConnected) (fullscreen ? container : document.body).appendChild(cursor);
	};
	const fullscreenChanged = () => {
		fullscreen = document.fullscreenElement === container;
		syncFullscreenCursor();
	};
	const toggleFullscreen = async () => {
		try {
			if (document.fullscreenElement === container) await document.exitFullscreen();
			else await container.requestFullscreen();
		} catch (reason) {
			toast.error(reason instanceof Error ? reason.message : String(reason));
		}
	};

	const disconnect = () => {
		generation++;
		connecting = false;
		clearTimeout(retry);
		viewer?.disconnect();
		viewer = null;
		socket?.close();
		socket = null;
	};
	const connect = async () => {
		if (!mounted || !active || socket || connecting) return;
		connecting = true;
		const version = ++generation;
		error = '';
		status = $i18n.t('Connecting…');
		try {
			const info = await terminalRequest<{ transport?: string; audio?: boolean }>(
				connection,
				chatId,
				'/desktop'
			);
			if (version !== generation) return;
			transport = info.transport ?? 'vnc';
			audioAvailable = info.audio === true;
			await tick();
			if (version !== generation) return;
			if (transport === 'frames') {
				socket = openTerminalSocket(connection, chatId, '/desktop/stream');
				let framePending = Promise.resolve();
				socket.onmessage = async (event) => {
					if (version !== generation) return;
					try {
						framePending = framePending.then(() => {
							if (version !== generation) return;
							return native.draw(event.data);
						});
						await framePending;
						if (version !== generation) return;
						send({ type: 'frameAck', window: 3 });
						status = '';
					} catch (reason) {
						if (version === generation)
							error = reason instanceof Error ? reason.message : String(reason);
					}
				};
			} else {
				const { default: RFB } = await import('@novnc/novnc');
				if (version !== generation) return;
				socket = openTerminalSocket(connection, chatId, '/desktop/stream', (channel) => {
					if (version !== generation) return;
					viewer = new RFB(surface, channel);
					const cursor = viewer._cursor;
					const detachCursor = cursor.detach.bind(cursor);
					cursor.detach = () => {
						// noVNC removes this canvas from body, including on a server disconnect.
						if (cursor._canvas.parentElement === container)
							document.body.appendChild(cursor._canvas);
						detachCursor();
					};
					viewer.scaleViewport = true;
					viewer.resizeSession = false;
					viewer.qualityLevel = 6;
					viewer.addEventListener('connect', () => {
						status = '';
						syncFullscreenCursor();
					});
					viewer.addEventListener('securityfailure', () => {
						error = $i18n.t('Desktop connection failed.');
					});
				});
			}
			socket.addEventListener('close', (event) => {
				if (version !== generation) return;
				viewer?.disconnect();
				viewer = null;
				socket = null;
				if (event.code >= 4000 && event.code < 5000) {
					error = $i18n.t('Desktop access denied. Reopen this tab.');
					status = '';
				} else {
					status = $i18n.t('Reconnecting…');
					retry = setTimeout(connect, 2000);
				}
			});
		} catch (reason) {
			if (version === generation) {
				error = reason instanceof Error ? reason.message : String(reason);
				status = '';
			}
		} finally {
			if (version === generation) connecting = false;
		}
	};
	const paste = (text: string, shift = false) => {
		if (transport === 'frames') {
			send({ type: 'paste', text });
			return;
		}
		if (!viewer) return;
		viewer.clipboardPasteFrom(text);
		viewer.sendKey(0xffe3, 'ControlLeft', true);
		if (shift) viewer.sendKey(0xffe1, 'ShiftLeft', true);
		viewer.sendKey(0x76, 'KeyV');
		if (shift) viewer.sendKey(0xffe1, 'ShiftLeft', false);
		viewer.sendKey(0xffe3, 'ControlLeft', false);
	};
	$: if (mounted) {
		if (active) void connect();
		else disconnect();
	}
	onMount(() => {
		mounted = true;
		fullscreenEnabled = document.fullscreenEnabled;
		return () => {
			mounted = false;
			disconnect();
		};
	});
</script>

<svelte:document on:fullscreenchange={fullscreenChanged} />

<div bind:this={container} class="relative h-full w-full min-h-0 bg-white dark:bg-gray-900">
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<div
		bind:this={surface}
		class="h-full w-full overflow-hidden"
		role="application"
		aria-label={$i18n.t('Desktop')}
		on:paste={(event) => {
			event.preventDefault();
			paste(event.clipboardData?.getData('text/plain') ?? '');
		}}
		on:keydown|capture={(event) => {
			if (
				(event.ctrlKey || event.metaKey) &&
				event.key.toLowerCase() === 'v' &&
				navigator.clipboard?.readText
			) {
				event.preventDefault();
				event.stopPropagation();
				void navigator.clipboard
					.readText()
					.then((text) => paste(text, event.shiftKey))
					.catch(() => {});
			}
		}}
	>
		{#if transport === 'frames'}<NativeDesktop bind:this={native} {send} />{/if}
	</div>
	{#if status || error}
		<div
			class="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-white/90 px-4 text-center text-xs text-gray-500 dark:bg-gray-900/90 dark:text-gray-400"
		>
			<span class={error ? '' : 'text-xs text-gray-400 dark:text-gray-500'}>{error || status}</span>
			{#if error}<button
					class="text-gray-700 hover:text-black dark:text-gray-300 dark:hover:text-white"
					on:click={connect}>{$i18n.t('Retry')}</button
				>{/if}
		</div>
	{/if}
	{#if audioAvailable && active && !status && !error}
		<DesktopAudio {connection} {chatId} {fullscreenEnabled} />
	{/if}
	{#if fullscreenEnabled}
		<button
			type="button"
			class="absolute right-1.5 top-1.5 flex h-6 w-6 items-center justify-center rounded-md text-gray-400/70 hover:bg-white/80 hover:text-gray-700 focus-visible:bg-white/80 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 dark:hover:bg-gray-900/80 dark:hover:text-gray-200 dark:focus-visible:bg-gray-900/80"
			aria-label={fullscreen ? $i18n.t('Exit full screen') : $i18n.t('Open in full screen')}
			title={fullscreen ? $i18n.t('Exit full screen') : $i18n.t('Open in full screen')}
			on:click={toggleFullscreen}
		>
			<Icon name={fullscreen ? 'collapse' : 'expand'} size={12} />
		</button>
	{/if}
	{#if overlay}<div class="absolute inset-0"></div>{/if}
</div>
