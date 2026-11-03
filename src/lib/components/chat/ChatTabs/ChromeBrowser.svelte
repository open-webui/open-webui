<script lang="ts">
	import { onMount, tick } from 'svelte';
	import FrameCanvas from './FrameCanvas.svelte';
	import type RFB from '@novnc/novnc';
	export let streamUrl: string;
	export let active = true;
	export let mobile = false;
	export let quality: 'low' | 'balanced' | 'crisp' = 'balanced';
	export let onState: (state: {
		url: string;
		title: string;
		canGoBack: boolean;
		canGoForward: boolean;
	}) => void;
	export let onError: (error: string) => void = () => {};
	export let onStatus: (status: string) => void = () => {};
	let surface: HTMLDivElement;
	let frame = '';
	let frames: FrameCanvas;
	let transport = '';
	let vncSurface: HTMLDivElement;
	let viewer: RFB | null = null;
	let vncSocket: WebSocket | null = null;
	let vncGeneration = 0;
	let vncRetry: ReturnType<typeof setTimeout>;
	let width = 1024;
	let height = 768;
	let socket: WebSocket | null = null;
	let disposed = false;
	let retry: ReturnType<typeof setTimeout>;
	let attempts = 0;
	let hasConnected = false;
	let pendingNavigation: string | null = null;
	const pressedModifiers = new Map<string, number>();
	const releaseModifiers = () => {
		for (const [code, keysym] of pressedModifiers) viewer?.sendKey(keysym, code, false);
		pressedModifiers.clear();
	};
	const stopVnc = () => {
		vncGeneration++;
		clearTimeout(vncRetry);
		releaseModifiers();
		viewer?.disconnect();
		viewer = null;
		vncSocket?.close();
		vncSocket = null;
	};
	const startVnc = async () => {
		if (!active || disposed || vncSocket || transport !== 'vnc' || !vncSurface) return;
		const generation = ++vncGeneration;
		onError('');
		onStatus('Connecting…');
		try {
			const { default: RFB } = await import('@novnc/novnc');
			if (generation !== vncGeneration) return;
			const url = new URL(streamUrl.replace(/\/stream$/, '/vnc'), window.location.origin);
			url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
			const channel = new WebSocket(url);
			vncSocket = channel;
			channel.onopen = () => {
				if (generation !== vncGeneration) return;
				viewer = new RFB(vncSurface, channel);
				viewer.scaleViewport = true;
				viewer.resizeSession = false;
				viewer.qualityLevel = { low: 4, balanced: 6, crisp: 9 }[quality];
				viewer.addEventListener('connect', () => onStatus(''));
			};
			channel.onclose = (event) => {
				if (generation !== vncGeneration) return;
				stopVnc();
				if (event.code >= 4000 && event.code < 5000) {
					onStatus('');
					onError('Browser opened in another viewer. Reopen this tab.');
				} else if (active && !disposed) {
					onStatus('Reconnecting…');
					vncRetry = setTimeout(startVnc, 2000);
				}
			};
		} catch (error) {
			if (generation === vncGeneration) {
				onStatus('');
				onError(error instanceof Error ? error.message : String(error));
			}
		}
	};
	export const command = (type: string, values: Record<string, unknown> = {}) => {
		if (socket?.readyState === WebSocket.OPEN) {
			socket.send(JSON.stringify({ type, ...values }));
		} else if (type === 'navigate') {
			pendingNavigation = values.url as string;
		}
	};
	const resize = () => {
		if (!surface) return;
		const bounds = surface.getBoundingClientRect();
		if (!bounds.width || !bounds.height) return;
		width = mobile ? 390 : Math.max(240, Math.round(bounds.width));
		height = mobile ? 844 : Math.max(200, Math.round(bounds.height));
		command('viewport', { width, height, mobile });
	};
	$: if (socket) command('visibility', { visible: active });
	$: if (surface && active) {
		mobile;
		resize();
	}
	$: if (socket) command('quality', { quality });
	$: if (viewer) viewer.qualityLevel = { low: 4, balanced: 6, crisp: 9 }[quality];
	$: if (active && transport === 'vnc' && vncSurface) void startVnc();
	$: if (!active) stopVnc();
	const modifiers = (e: MouseEvent | KeyboardEvent) =>
		(e.altKey ? 1 : 0) | (e.ctrlKey ? 2 : 0) | (e.metaKey ? 4 : 0) | (e.shiftKey ? 8 : 0);
	const mouse = (event: MouseEvent, type: string) => {
		if (transport === 'vnc') return;
		const image = surface.querySelector(transport === 'jpeg' ? 'img' : 'canvas');
		if (!image) return;
		const box = image.getBoundingClientRect();
		event.preventDefault();
		if (type === 'mousePressed') surface.focus();
		command('mouse', {
			event: type,
			x: Math.max(0, Math.min(width, ((event.clientX - box.left) * width) / box.width)),
			y: Math.max(0, Math.min(height, ((event.clientY - box.top) * height) / box.height)),
			button: ['left', 'middle', 'right'][event.button] ?? 'none',
			buttons: event.buttons,
			clickCount: type === 'mouseMoved' ? 0 : event.detail || 1,
			modifiers: modifiers(event)
		});
	};
	const key = (event: KeyboardEvent, type: string) => {
		if (transport === 'vnc') {
			// Keep browser editing shortcuts on CDP; VNC handles pointer input directly.
			event.stopPropagation();
			const keysym = { Shift: 0xffe1, Control: 0xffe3, Alt: 0xffe9, Meta: 0xffeb }[event.key];
			if (keysym) {
				const down = type === 'keyDown';
				viewer?.sendKey(keysym, event.code, down);
				if (down) pressedModifiers.set(event.code, keysym);
				else pressedModifiers.delete(event.code);
			}
		}
		if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'v') return;
		event.preventDefault();
		const editing =
			(event.ctrlKey || event.metaKey) &&
			(
				{ a: 'selectAll', c: 'copy', x: 'cut', z: event.shiftKey ? 'redo' : 'undo' } as Record<
					string,
					string
				>
			)[event.key.toLowerCase()];
		command('key', {
			event: type,
			key: event.key,
			code: event.code,
			windowsVirtualKeyCode: event.keyCode,
			modifiers: modifiers(event),
			...(editing ? { commands: [editing] } : {}),
			text:
				type === 'keyDown' && event.key.length === 1 && !event.ctrlKey && !event.metaKey
					? event.key
					: undefined
		});
	};
	onMount(() => {
		onStatus('Connecting…');
		const connect = () => {
			const url = new URL(streamUrl, window.location.origin);
			url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
			socket = new WebSocket(url);
			const channel = socket;
			socket.binaryType = 'arraybuffer';
			socket.onopen = () => {
				onError('');
				command('frames');
				resize();
				command('quality', { quality });
				command('visibility', { visible: active });
				if (pendingNavigation) {
					command('navigate', { url: pendingNavigation });
					pendingNavigation = null;
				}
			};
			socket.onmessage = async (event) => {
				try {
					if (event.data instanceof ArrayBuffer) {
						await tick();
						if (disposed || socket !== channel) return;
						await frames.draw(event.data);
						if (disposed || socket !== channel) return;
						command('frameAck');
						onStatus('');
						return;
					}
					const message = JSON.parse(event.data);
					if (message.type === 'frame' || message.type === 'state') {
						hasConnected = true;
						attempts = 0;
						if (message.type === 'frame' || message.transport !== 'vnc') onStatus('');
					}
					if (message.type === 'frame') frame = `data:image/jpeg;base64,${message.data}`;
					if (message.type === 'state') {
						transport = message.transport ?? 'jpeg';
						onState(message);
						onError(message.error || '');
					}
				} catch (error) {
					onError(error instanceof Error ? error.message : String(error));
				}
			};
			socket.onclose = (event) => {
				if (disposed) return;
				stopVnc();
				transport = '';
				if (event.code >= 4000 && event.code < 5000) {
					onStatus('');
					onError(
						event.code === 4000
							? 'Browser opened in another viewer.'
							: 'Browser session expired. Reopen this tab.'
					);
					return;
				}
				onError('');
				onStatus(hasConnected ? 'Reconnecting…' : 'Connecting…');
				retry = setTimeout(connect, Math.min(1000 * 2 ** attempts++, 10000));
			};
		};
		connect();
		const observer = new ResizeObserver(resize);
		observer.observe(surface);
		return () => {
			disposed = true;
			onStatus('');
			clearTimeout(retry);
			observer.disconnect();
			stopVnc();
			socket?.close();
		};
	});
</script>

<svelte:window on:blur={releaseModifiers} />

<div
	bind:this={surface}
	class="flex h-full w-full items-start justify-center overflow-hidden outline-none"
	tabindex="0"
	role="application"
	aria-label="Browser page"
	on:keydown|capture={(event) => key(event, 'keyDown')}
	on:keyup|capture={(event) => key(event, 'keyUp')}
	on:blur|capture={releaseModifiers}
	on:paste={(event) => {
		event.preventDefault();
		command('paste', { text: event.clipboardData?.getData('text/plain') ?? '' });
	}}
	on:mousedown={(event) => mouse(event, 'mousePressed')}
	on:mouseup={(event) => mouse(event, 'mouseReleased')}
	on:mousemove={(event) => mouse(event, 'mouseMoved')}
	on:contextmenu|preventDefault
	on:wheel|preventDefault={(event) => {
		if (transport === 'vnc') return;
		const box = surface
			.querySelector(transport === 'jpeg' ? 'img' : 'canvas')
			?.getBoundingClientRect();
		if (!box) return;
		command('mouse', {
			event: 'mouseWheel',
			x: ((event.clientX - box.left) * width) / box.width,
			y: ((event.clientY - box.top) * height) / box.height,
			deltaX: event.deltaX,
			deltaY: event.deltaY,
			modifiers: modifiers(event)
		});
	}}
>
	{#if transport === 'vnc'}
		<div bind:this={vncSurface} class="vnc h-full w-full"></div>
	{:else if transport === 'frames'}
		<FrameCanvas bind:this={frames} />
	{:else if frame}<img
			src={frame}
			alt="Browser page"
			draggable="false"
			class="max-h-full max-w-full select-none"
			style:aspect-ratio={`${width}/${height}`}
		/>{/if}
</div>

<style>
	.vnc > :global(div) {
		background: transparent !important;
	}
	.vnc :global(canvas) {
		margin: 0 auto !important;
	}
</style>
