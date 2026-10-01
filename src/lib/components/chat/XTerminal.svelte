<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { Terminal } from '@xterm/xterm';
	import { FitAddon } from '@xterm/addon-fit';
	import { WebLinksAddon } from '@xterm/addon-web-links';
	import '@xterm/xterm/css/xterm.css';
	import { terminalRequest, type TerminalConnection } from '$lib/apis/terminal';
	import { connectedUserTerminals } from '$lib/stores';

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
	let pingInterval: ReturnType<typeof setInterval>;
	let destroyed = false;
	let sessionId = '';
	const terminalOwner = Symbol();

	function disconnect() {
		connectedUserTerminals.update((entries) => {
			entries.delete(terminalOwner);
			return entries;
		});
		connected = false;
		connecting = false;
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

	async function connect() {
		connecting = true;
		try {
			const session = await terminalRequest<{ id: string }>(connection, chatId, '/api/terminals', {
				method: 'POST'
			});
			sessionId = session.id;
			if (destroyed) {
				await terminalRequest(
					connection,
					chatId,
					`/api/terminals/${encodeURIComponent(sessionId)}`,
					{ method: 'DELETE' }
				);
				return;
			}
			const url = new URL(
				`${connection.baseUrl}/api/terminals/${encodeURIComponent(sessionId)}`,
				location.href
			);
			url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
			ws = new WebSocket(url);
			ws.binaryType = 'arraybuffer';
			ws.onopen = () => {
				if (destroyed) return;
				ws?.send(
					JSON.stringify({ type: 'auth', token: connection.key.trim(), chat_id: chatId ?? '' })
				);
				if (connection.selector && chatId) {
					const shell = { terminalId: connection.selector, chatId };
					connectedUserTerminals.update((entries) => entries.set(terminalOwner, shell));
				}
				connected = true;
				connecting = false;
				fit();
				if (active) term?.focus();
				if (term) ws?.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }));
				pingInterval = setInterval(() => {
					if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'ping' }));
				}, 25000);
			};
			ws.onmessage = (event) => {
				if (destroyed) return;
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

	onMount(() => {
		term = new Terminal({
			cursorBlink: !readOnly,
			disableStdin: readOnly,
			fontSize: 13,
			fontFamily:
				"'JetBrains Mono', 'Fira Code', 'Cascadia Code', Menlo, Monaco, 'Courier New', monospace",
			theme: {
				background: '#000000',
				foreground: '#c0c0c0',
				cursor: '#ffffff',
				selectionBackground: '#444444'
			},
			scrollback: 5000
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
		destroyed = true;
		disconnect();
		ws?.close();
		resizeObserver?.disconnect();
		term?.dispose();
		term = null;
	});
</script>

<div class="h-full min-h-0 relative">
	<div
		bind:this={terminalEl}
		class="absolute inset-0 px-0.5"
		class:pointer-events-none={overlay}
	></div>
</div>
