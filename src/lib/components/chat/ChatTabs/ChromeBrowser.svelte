<script lang="ts">
	import { onMount } from 'svelte';
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
	let width = 1024;
	let height = 768;
	let socket: WebSocket | null = null;
	let disposed = false;
	let retry: ReturnType<typeof setTimeout>;
	let attempts = 0;
	let hasConnected = false;
	let pendingNavigation: string | null = null;
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
	const modifiers = (e: MouseEvent | KeyboardEvent) =>
		(e.altKey ? 1 : 0) | (e.ctrlKey ? 2 : 0) | (e.metaKey ? 4 : 0) | (e.shiftKey ? 8 : 0);
	const mouse = (event: MouseEvent, type: string) => {
		const image = surface.querySelector('img');
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
			socket.onopen = () => {
				onError('');
				resize();
				command('quality', { quality });
				command('visibility', { visible: active });
				if (pendingNavigation) {
					command('navigate', { url: pendingNavigation });
					pendingNavigation = null;
				}
			};
			socket.onmessage = (event) => {
				try {
					const message = JSON.parse(event.data);
					if (message.type === 'frame' || message.type === 'state') {
						hasConnected = true;
						attempts = 0;
						onStatus('');
					}
					if (message.type === 'frame') frame = `data:image/jpeg;base64,${message.data}`;
					if (message.type === 'state') {
						onState(message);
						onError(message.error || '');
					}
				} catch {
					/* Ignore malformed stream messages. */
				}
			};
			socket.onclose = (event) => {
				if (disposed) return;
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
			socket?.close();
		};
	});
</script>

<div
	bind:this={surface}
	class="flex h-full w-full items-start justify-center overflow-hidden outline-none"
	tabindex="0"
	role="application"
	aria-label="Browser page"
	on:keydown={(event) => key(event, 'keyDown')}
	on:keyup={(event) => key(event, 'keyUp')}
	on:paste={(event) => {
		event.preventDefault();
		command('paste', { text: event.clipboardData?.getData('text/plain') ?? '' });
	}}
	on:mousedown={(event) => mouse(event, 'mousePressed')}
	on:mouseup={(event) => mouse(event, 'mouseReleased')}
	on:mousemove={(event) => mouse(event, 'mouseMoved')}
	on:contextmenu|preventDefault
	on:wheel|preventDefault={(event) => {
		const box = surface.querySelector('img')?.getBoundingClientRect();
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
	{#if frame}<img
			src={frame}
			alt="Browser page"
			draggable="false"
			class="max-h-full max-w-full select-none"
			style:aspect-ratio={`${width}/${height}`}
		/>{/if}
</div>
