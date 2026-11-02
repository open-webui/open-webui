<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { Terminal } from '@xterm/xterm';
	import { FitAddon } from '@xterm/addon-fit';
	import { WebLinksAddon } from '@xterm/addon-web-links';
	import '@xterm/xterm/css/xterm.css';
	import { terminalRequest, type TerminalConnection } from '$lib/apis/terminal';
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
	let sessionId = '';
	let sessionChatId = chatId;
	let bindingChat: Promise<void> | null = null;
	let finishConnection: (ready: boolean) => void;
	const connectionReady = new Promise<boolean>((resolve) => (finishConnection = resolve));
	let reportedActive: boolean | null = null;

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
			const session = await terminalRequest<{ id: string }>(
				connection,
				sessionChatId,
				'/api/terminals',
				{
					method: 'POST'
				}
			);
			sessionId = session.id;
			if (destroyed) {
				await terminalRequest(
					connection,
					sessionChatId,
					`/api/terminals/${encodeURIComponent(sessionId)}`,
					{ method: 'DELETE' }
				);
				return;
			}
			ws = openTerminalSocket(
				connection,
				sessionChatId,
				`/api/terminals/${encodeURIComponent(sessionId)}`,
				() => {
					if (destroyed) return;
					connected = true;
					finishConnection(true);
					connecting = false;
					reportActivity(active);
					fit();
					if (active) term?.focus();
					if (term) ws?.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }));
					pingInterval = setInterval(() => {
						if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'ping' }));
					}, 25000);
				}
			);
			ws.onmessage = (event) => {
				if (destroyed) return;
				if (typeof event.data === 'string') {
					try {
						if (JSON.parse(event.data).type === 'chat') return;
					} catch {
						/* Render non-JSON terminal output below. */
					}
				}
				if (event.data instanceof ArrayBuffer) term?.write(new Uint8Array(event.data));
				else write(event.data);
			};
			ws.onclose = () => {
				if (destroyed) return;
				disconnect();
				write('\r\n\x1b[90m[Connection closed]\x1b[0m\r\n');
			};
			ws.onerror = () => {
				if (destroyed) return;
				disconnect();
				write('\r\n\x1b[31m[Terminal connection failed]\x1b[0m\r\n');
			};
		} catch (error) {
			if (destroyed) return;
			disconnect();
			write(`\r\n\x1b[31m[${error}]\x1b[0m\r\n`);
		}
	}

	$: if (active && term) requestAnimationFrame(fit);
	$: if (connected) reportActivity(active);
	$: if (connected && chatId && !sessionChatId) {
		void bindChat(chatId).catch((error) => write(`\r\n[${error}]\r\n`));
	}

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
		disconnect();
		ws?.close();
		resizeObserver?.disconnect();
		themeObserver?.disconnect();
		term?.dispose();
		term = null;
	});
</script>

<div class="terminal-view h-full min-h-0 relative bg-white dark:bg-transparent">
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
