<script lang="ts">
	import { onMount, onDestroy, getContext } from 'svelte';
	import { Terminal } from '@xterm/xterm';
	import { FitAddon } from '@xterm/addon-fit';
	import { WebLinksAddon } from '@xterm/addon-web-links';
	import '@xterm/xterm/css/xterm.css';

	import { terminalServers, settings, selectedTerminalId, user } from '$lib/stores';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let overlay = false;
	export let chatId: string | null = null;

	let terminalEl: HTMLDivElement;
	let term: Terminal | null = null;
	let fitAddon: FitAddon | null = null;
	let ws: WebSocket | null = null;
	export let connected = false;
	export let connecting = false;
	let resizeObserver: ResizeObserver | null = null;
	let pingInterval: ReturnType<typeof setInterval> | null = null;

	// Resolve the active terminal server's info for the WebSocket URL
	const getTerminalInfo = (): { serverId: string; baseUrl: string } | null => {
		// System terminal (admin-configured, has an `id`)
		const systemTerminals = ($terminalServers ?? []).filter((t: any) => t.id);
		const systemMatch = systemTerminals.find((t: any) => t.id === $selectedTerminalId);
		if (systemMatch) {
			// For system terminals, WS goes through the Open WebUI backend proxy
			return { serverId: systemMatch.id, baseUrl: WEBUI_API_BASE_URL };
		}

		// Direct terminal (user-configured, matched by URL)
		const directTerminals = ($settings?.terminalServers ?? []).filter((s: any) => s.url);
		const directMatch = directTerminals.find((s: any) => s.url === $selectedTerminalId);
		if (directMatch) {
			// For direct terminals, construct WS URL from the server URL directly
			return { serverId: '__direct__', baseUrl: directMatch.url };
		}

		return null;
	};

	const connect = async () => {
		if (ws) disconnect();

		const info = getTerminalInfo();
		if (!info) return;

		connecting = true;

		const token = localStorage.getItem('token') ?? '';

		try {
			let sessionId: string;
			let wsUrl: string;
			let authToken: string;

			if (info.serverId === '__direct__') {
				// Direct connection to open-terminal
				const base = info.baseUrl.replace(/\/$/, '');
				const directTerminals = ($settings?.terminalServers ?? []).filter((s: any) => s.url);
				const directMatch = directTerminals.find((s: any) => s.url === $selectedTerminalId);
				const apiKey = directMatch?.key ?? '';
				authToken = apiKey;

				// Create session
				const createHeaders: Record<string, string> = { Authorization: `Bearer ${apiKey}` };
				if (chatId) createHeaders['X-Session-Id'] = chatId;
				const res = await fetch(`${base}/api/terminals`, {
					method: 'POST',
					headers: createHeaders
				});
				if (!res.ok) throw new Error(`Failed to create session: ${res.status}`);
				const session = await res.json();
				sessionId = session.id;

				const wsBase = base.replace(/^https:/, 'wss:').replace(/^http:/, 'ws:');
				wsUrl = `${wsBase}/api/terminals/${sessionId}`;
			} else {
				// System terminal — proxy through Open WebUI backend
				const base = info.baseUrl.replace(/\/$/, '');
				authToken = token;

				// Create session via proxy
				const proxyHeaders: Record<string, string> = { Authorization: `Bearer ${token}` };
				if (chatId) proxyHeaders['X-Session-Id'] = chatId;
				const res = await fetch(`${base}/terminals/${info.serverId}/api/terminals`, {
					method: 'POST',
					headers: proxyHeaders
				});
				if (!res.ok) throw new Error(`Failed to create session: ${res.status}`);
				const session = await res.json();
				sessionId = session.id;

				const wsBase = base.replace(/^https:/, 'wss:').replace(/^http:/, 'ws:');
				wsUrl = `${wsBase}/terminals/${info.serverId}/api/terminals/${sessionId}`;
			}

			ws = new WebSocket(wsUrl);
			ws.binaryType = 'arraybuffer';

			ws.onopen = () => {
				// First-message auth (no token in URL)
				if (ws) {
					ws.send(JSON.stringify({ type: 'auth', token: authToken }));
				}
				connected = true;
				connecting = false;
				// Focus the terminal so it receives keyboard input immediately
				term?.focus();
				// Send initial resize
				if (term && ws) {
					ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }));
				}
				// Keepalive ping to prevent idle timeout from proxies/LBs
				if (pingInterval) clearInterval(pingInterval);
				pingInterval = setInterval(() => {
					if (ws && ws.readyState === WebSocket.OPEN) {
						ws.send(JSON.stringify({ type: 'ping' }));
					}
				}, 25000);
			};

			ws.onmessage = (event) => {
				if (term) {
					if (event.data instanceof ArrayBuffer) {
						term.write(new Uint8Array(event.data));
					} else {
						term.write(event.data);
					}
				}
			};

			ws.onclose = () => {
				connected = false;
				connecting = false;
				if (term) {
					term.write('\r\n\x1b[90m[Connection closed]\x1b[0m\r\n');
				}
			};

			ws.onerror = () => {
				connected = false;
				connecting = false;
			};
		} catch (err) {
			connecting = false;
			if (term) {
				term.write(`\r\n\x1b[31m[Error: ${err}]\x1b[0m\r\n`);
			}
		}
	};

	const disconnect = () => {
		if (pingInterval) {
			clearInterval(pingInterval);
			pingInterval = null;
		}
		if (ws) {
			ws.close();
			ws = null;
		}
		connected = false;
		connecting = false;
	};

	const initTerminal = () => {
		if (!terminalEl || term) return;

		term = new Terminal({
			cursorBlink: true,
			fontSize: 13,
			fontFamily:
				"'JetBrains Mono', 'Fira Code', 'Cascadia Code', Menlo, Monaco, 'Courier New', monospace",
			theme: {
				background: '#000000',
				foreground: '#c0c0c0',
				cursor: '#ffffff',
				cursorAccent: '#000000',
				selectionBackground: '#444444',
				selectionForeground: '#ffffff',
				black: '#000000',
				red: '#cd0000',
				green: '#00cd00',
				yellow: '#cdcd00',
				blue: '#0000ee',
				magenta: '#cd00cd',
				cyan: '#00cdcd',
				white: '#e5e5e5',
				brightBlack: '#7f7f7f',
				brightRed: '#ff0000',
				brightGreen: '#00ff00',
				brightYellow: '#ffff00',
				brightBlue: '#5c5cff',
				brightMagenta: '#ff00ff',
				brightCyan: '#00ffff',
				brightWhite: '#ffffff'
			},
			allowProposedApi: true,
			scrollback: 5000
		});

		fitAddon = new FitAddon();
		term.loadAddon(fitAddon);
		term.loadAddon(new WebLinksAddon());

		term.open(terminalEl);

		// Fit after a frame so the container has dimensions
		requestAnimationFrame(() => {
			fitAddon?.fit();
		});

		// Forward keystrokes to WebSocket
		term.onData((data) => {
			if (ws && ws.readyState === WebSocket.OPEN) {
				ws.send(new TextEncoder().encode(data));
			}
		});

		// Forward binary data (e.g. paste with special chars)
		term.onBinary((data) => {
			if (ws && ws.readyState === WebSocket.OPEN) {
				const buffer = new Uint8Array(data.length);
				for (let i = 0; i < data.length; i++) {
					buffer[i] = data.charCodeAt(i) & 0xff;
				}
				ws.send(buffer);
			}
		});

		// Ensure all key events are processed by xterm.js and not intercepted
		// by the browser or surrounding UI (fixes vi/vim keystroke handling).
		term.attachCustomKeyEventHandler(() => true);

		// Handle resize
		term.onResize(({ cols, rows }) => {
			if (ws && ws.readyState === WebSocket.OPEN) {
				ws.send(JSON.stringify({ type: 'resize', cols, rows }));
			}
		});

		// Watch container size changes
		resizeObserver = new ResizeObserver(() => {
			requestAnimationFrame(() => {
				fitAddon?.fit();
			});
		});
		resizeObserver.observe(terminalEl);

		// Connection is handled by the reactive block below (which fires
		// when `term` is set here), so we intentionally do NOT call
		// connect() to avoid creating a duplicate WebSocket whose onclose
		// handler would write a spurious "[Connection closed]" message.
	};

	// Reconnect when the selected terminal changes
	$: if ($selectedTerminalId !== undefined && term) {
		// Clear the terminal screen and reconnect to the new server
		disconnect();
		term.clear();
		if ($selectedTerminalId) {
			connect();
		}
	}

	onMount(() => {
		initTerminal();
	});

	onDestroy(() => {
		disconnect();
		resizeObserver?.disconnect();
		term?.dispose();
		term = null;
		fitAddon = null;
	});
</script>

<div class="h-full min-h-0 relative">
	<div bind:this={terminalEl} class="absolute inset-0 px-0.5" class:pointer-events-none={overlay} />
</div>
