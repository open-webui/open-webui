<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { Terminal } from '@xterm/xterm';
	import { FitAddon } from '@xterm/addon-fit';
	import { WebLinksAddon } from '@xterm/addon-web-links';
	import { WebglAddon } from '@xterm/addon-webgl';
	import '@xterm/xterm/css/xterm.css';
	import {
		terminalRequest,
		TerminalRequestError,
		type TerminalConnection
	} from '$lib/apis/terminal';
	import { assignTerminalChat, openTerminalSocket } from '$lib/apis/terminal/socket';

	export let connection: TerminalConnection;
	export let chatId: string | null = null;
	export let overlay = false;
	export let active = true;
	export let readOnly = false;
	export let connected = false;
	export let connecting = false;

	let terminalEl: HTMLDivElement;
	let term: Terminal | null = null;
	let fitAddon: FitAddon;
	let ws: WebSocket | null = null;
	let resizeObserver: ResizeObserver;
	let themeObserver: MutationObserver;
	let pingInterval: ReturnType<typeof setInterval>;
	let destroyed = false;
	export let sessionId = '';
	export let onUnavailable: (message: string, status?: number) => void = () => {};
	let sessionChatId = chatId;
	let bindingChat: Promise<void> | null = null;
	let finishConnection: (ready: boolean) => void;
	const connectionReady = new Promise<boolean>((resolve) => (finishConnection = resolve));
	let reportedActive: boolean | null = null;
	let cursor = 0;
	let outputEnd: number | null = null;
	let outputPending = Promise.resolve();
	let outputBatch = outputPending;
	let outputBatchBytes = 0;
	let reconnectTimer: ReturnType<typeof setTimeout>;
	let reconnectDelay = 1000;
	let reconnecting = false;

	export async function bindChat(id: string) {
		if (readOnly || destroyed || sessionChatId === id) return;
		if (sessionChatId) throw new Error('Terminal already belongs to another chat');
		if (!(await connectionReady) || !ws) throw new Error('Terminal is not connected');
		if (!bindingChat) {
			bindingChat = assignTerminalChat(ws, id)
				.then(() => {
					sessionChatId = id;
				})
				.finally(() => {
					bindingChat = null;
				});
		}
		await bindingChat;
		if (sessionChatId !== id) throw new Error('Terminal already belongs to another chat');
	}

	function reportActivity(visible: boolean) {
		if (readOnly || !connected || ws?.readyState !== WebSocket.OPEN) return;
		const isActive = visible && !document.hidden;
		if (reportedActive === isActive) return;
		ws.send(JSON.stringify({ type: 'activity', active: isActive }));
		reportedActive = isActive;
	}
	const reportVisibility = () => reportActivity(active);

	function disconnect() {
		finishConnection(false);
		connected = false;
		connecting = false;
		reportedActive = null;
		clearInterval(pingInterval);
	}

	export function write(output: string) {
		if (!term || destroyed) return;
		const following = term.buffer.active.viewportY >= term.buffer.active.baseY;
		term.write(output, () => {
			if (following) term?.scrollToBottom();
		});
	}

	function fit() {
		if (active && terminalEl?.clientWidth && terminalEl?.clientHeight) fitAddon?.fit();
	}

	function updateTheme() {
		if (!term) return;
		term.options.theme = document.documentElement.classList.contains('dark')
			? {
					background: '#00000000',
					foreground: '#c0c0c0',
					cursor: '#ffffff',
					cursorAccent: '#171717',
					selectionBackground: '#444444'
				}
			: {
					background: '#ffffff',
					foreground: '#171717',
					cursor: '#171717',
					cursorAccent: '#ffffff',
					selectionBackground: '#bfdbfe'
				};
	}

	async function connect() {
		connecting = true;
		try {
			if (!sessionId) throw new Error('Session no longer available');
			await terminalRequest(
				connection,
				sessionChatId,
				`/api/terminals/${encodeURIComponent(sessionId)}`
			);
			if (destroyed) return;
			ws = openTerminalSocket(
				connection,
				sessionChatId,
				`/api/terminals/${encodeURIComponent(sessionId)}`,
				() => {
					if (destroyed) return;
					connected = true;
					reconnecting = false;
					finishConnection(true);
					connecting = false;
					reportActivity(active);
					fit();
					if (active) term?.focus();
					if (term) ws?.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }));
					pingInterval = setInterval(() => {
						if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'ping' }));
					}, 25000);
				},
				{ resume: true, cursor, flow_control: true }
			);
			const socket = ws;
			let flowControlled = false;
			let ackPending = false;
			ws.onmessage = (event) => {
				if (destroyed) return;
				if (typeof event.data === 'string') {
					try {
						const message = JSON.parse(event.data);
						if (message.type === 'chat') return;
						if (message.type === 'flow_control') {
							flowControlled = true;
							return;
						}
						if (message.type === 'output') {
							outputEnd = message.end;
							if (message.truncated) write('\r\n[Earlier output is no longer available]\r\n');
							return;
						}
					} catch {
						/* Render non-JSON terminal output below. */
					}
				}
				if (event.data instanceof ArrayBuffer) {
					const data = new Uint8Array(event.data);
					const end = outputEnd;
					outputEnd = null;
					// Let xterm batch parsing instead of scheduling a timer for every chunk.
					outputPending = outputBatch.then(
						() =>
							new Promise<void>((resolve) => {
								if (!term || destroyed) {
									resolve();
									return;
								}
								term.write(data, () => {
									if (end !== null) cursor = end;
									if (flowControlled && end !== null && !ackPending) {
										ackPending = true;
										queueMicrotask(() => {
											ackPending = false;
											if (socket.readyState === WebSocket.OPEN)
												socket.send(JSON.stringify({ type: 'ack', cursor }));
										});
									}
									reconnectDelay = 1000;
									resolve();
								});
							})
					);
					outputBatchBytes += data.byteLength;
					if (outputBatchBytes >= 64 * 1024) {
						outputBatch = outputPending;
						outputBatchBytes = 0;
					}
				} else write(event.data);
			};
			ws.onclose = async (event) => {
				disconnect();
				await outputPending;
				if (destroyed) return;
				if (event.code === 1000 || [4001, 4003, 4004].includes(event.code)) {
					reconnecting = false;
					onUnavailable(
						event.code === 4001 || event.code === 4003
							? 'Terminal access denied'
							: 'Session no longer available',
						event.code === 4001 || event.code === 4003 ? 403 : 404
					);
					write(
						event.code === 4001 || event.code === 4003
							? '\r\n[Terminal access denied. Check your sign-in and permissions.]\r\n'
							: '\r\n[Session no longer available.]\r\n'
					);
					return;
				}
				reconnecting = true;
				reconnectTimer = setTimeout(() => void connect(), reconnectDelay);
				reconnectDelay = Math.min(reconnectDelay * 2, 10000);
			};
			ws.onerror = () => {
				if (destroyed) return;
				disconnect();
			};
		} catch (error) {
			if (destroyed) return;
			disconnect();
			onUnavailable(
				String(error),
				error instanceof TerminalRequestError ? error.status : undefined
			);
			write(`\r\n\x1b[31m[${error}]\x1b[0m\r\n`);
		}
	}

	$: if (active && term) requestAnimationFrame(fit);
	$: if (connected) reportActivity(active);

	onMount(() => {
		document.addEventListener('visibilitychange', reportVisibility);
		term = new Terminal({
			allowTransparency: true,
			cursorBlink: !readOnly,
			disableStdin: readOnly,
			fontSize: 13,
			fontFamily:
				"'JetBrains Mono', 'Fira Code', 'Cascadia Code', Menlo, Monaco, 'Courier New', monospace",
			minimumContrastRatio: 4.5,
			scrollback: 5000
		});
		updateTheme();
		themeObserver = new MutationObserver(updateTheme);
		themeObserver.observe(document.documentElement, {
			attributes: true,
			attributeFilter: ['class']
		});
		fitAddon = new FitAddon();
		term.loadAddon(fitAddon);
		term.loadAddon(new WebLinksAddon());
		term.open(terminalEl);
		try {
			const webgl = new WebglAddon();
			webgl.onContextLoss(() => webgl.dispose());
			term.loadAddon(webgl);
		} catch {
			// Keep the default renderer when WebGL is unavailable.
		}
		resizeObserver = new ResizeObserver(fit);
		resizeObserver.observe(terminalEl);
		requestAnimationFrame(fit);
		if (!readOnly) {
			term.onData((data) => {
				if (ws?.readyState === WebSocket.OPEN) ws.send(new TextEncoder().encode(data));
			});
			term.onBinary((data) => {
				if (ws?.readyState === WebSocket.OPEN)
					ws.send(Uint8Array.from(data, (char) => char.charCodeAt(0) & 0xff));
			});
			term.onResize(({ cols, rows }) => {
				if (active && ws?.readyState === WebSocket.OPEN)
					ws.send(JSON.stringify({ type: 'resize', cols, rows }));
			});
			connect();
		}
	});

	onDestroy(() => {
		document.removeEventListener('visibilitychange', reportVisibility);
		destroyed = true;
		clearTimeout(reconnectTimer);
		disconnect();
		ws?.close();
		resizeObserver?.disconnect();
		themeObserver?.disconnect();
		term?.dispose();
		term = null;
	});
</script>

<div class="terminal-view h-full min-h-0 relative bg-white dark:bg-transparent">
	{#if reconnecting}
		<div
			class="absolute top-1 right-2 z-10 rounded bg-white/90 px-2 py-1 text-xs text-gray-600 dark:bg-gray-900/90 dark:text-gray-300"
			role="status"
		>
			Connection interrupted. Reconnecting to the same terminal…
		</div>
	{/if}
	<div
		bind:this={terminalEl}
		class="absolute inset-0 pl-2 pr-0.5"
		class:pointer-events-none={overlay}
	></div>
</div>

<style>
	.terminal-view :global(.xterm-viewport) {
		background-color: transparent;
	}
</style>
