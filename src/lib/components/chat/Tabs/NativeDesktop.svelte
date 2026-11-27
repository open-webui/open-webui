<script lang="ts">
	import { onDestroy } from 'svelte';
	import FrameCanvas from './FrameCanvas.svelte';
	export let send: (message: Record<string, unknown>) => void;
	// The picture already includes the host's cursor.
	export let hideCursor = false;
	let surface: HTMLDivElement;
	let frames: FrameCanvas;
	let pending: Record<string, unknown> | null = null;
	let frame = 0;
	export const draw = (packet: ArrayBuffer) => frames.draw(packet);
	export const supportsH264 = () => frames.supportsH264();
	const flush = () => {
		cancelAnimationFrame(frame);
		if (pending) send(pending);
		pending = null;
		frame = 0;
	};
	const position = (event: MouseEvent) => {
		const canvas = surface.querySelector('canvas');
		const box = canvas?.getBoundingClientRect();
		if (!canvas || !box?.width || !box.height) return null;
		const x = Math.floor(((event.clientX - box.left) * canvas.width) / box.width);
		const y = Math.floor(((event.clientY - box.top) * canvas.height) / box.height);
		return {
			type: 'mouse',
			x: Math.max(0, Math.min(canvas.width - 1, x)),
			y: Math.max(0, Math.min(canvas.height - 1, y)),
			// Back and forward buttons have no desktop equivalent.
			buttons: event.buttons & 7
		};
	};
	const pointer = (event: PointerEvent) => {
		const mouse = position(event);
		if (!mouse) return;
		if (event.type === 'pointerdown') {
			surface.focus();
			surface.setPointerCapture(event.pointerId);
		}
		pending = mouse;
		if (event.type !== 'pointermove') flush();
		else if (!frame) frame = requestAnimationFrame(flush);
	};
	const release = () => {
		cancelAnimationFrame(frame);
		frame = 0;
		pending = null;
		send({ type: 'release' });
	};
	const key = (event: KeyboardEvent, down: boolean) => {
		if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'v') return;
		if (event.isComposing) return;
		event.preventDefault();
		flush();
		send({ type: 'key', code: event.code, down });
		// macOS never reports the release of a key pressed while Command is held.
		if (down && event.metaKey && !/^(Meta|Shift|Control|Alt)/.test(event.code))
			send({ type: 'key', code: event.code, down: false });
	};
	onDestroy(release);
</script>

<svelte:window on:blur={release} />

<div
	bind:this={surface}
	class="flex h-full w-full touch-none items-center justify-center overflow-hidden outline-none {hideCursor
		? '[&>canvas]:cursor-none'
		: ''}"
	role="application"
	aria-label="Desktop screen"
	tabindex="0"
	on:pointerdown|preventDefault={pointer}
	on:pointermove={pointer}
	on:pointerup={pointer}
	on:pointercancel={release}
	on:blur={release}
	on:keydown={(event) => key(event, true)}
	on:keyup={(event) => key(event, false)}
	on:contextmenu|preventDefault
	on:paste|preventDefault|stopPropagation={(event) =>
		send({ type: 'paste', text: event.clipboardData?.getData('text/plain') ?? '' })}
	on:wheel|preventDefault={(event) => {
		const mouse = position(event);
		if (!mouse) return;
		flush();
		const canvas = surface.querySelector('canvas')!;
		const box = canvas.getBoundingClientRect();
		// Some browsers report mouse wheels in lines or pages.
		const unit = [1, 16, box.height][event.deltaMode] * (canvas.width / box.width);
		send({
			...mouse,
			scrollX: event.deltaX * unit,
			scrollY: event.deltaY * unit,
			// Older servers scroll by notches instead.
			deltaX: Math.sign(event.deltaX) * Math.ceil(Math.abs(event.deltaX) / 100),
			deltaY: Math.sign(event.deltaY) * Math.ceil(Math.abs(event.deltaY) / 100)
		});
	}}
>
	<FrameCanvas bind:this={frames} />
</div>
