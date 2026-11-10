<script lang="ts">
	import { onDestroy } from 'svelte';
	import FrameCanvas from './FrameCanvas.svelte';
	export let send: (message: Record<string, unknown>) => void;
	let surface: HTMLDivElement;
	let frames: FrameCanvas;
	let pending: Record<string, unknown> | null = null;
	let frame = 0;
	export const draw = (packet: ArrayBuffer) => frames.draw(packet);
	const flush = () => {
		cancelAnimationFrame(frame);
		if (pending) send(pending);
		pending = null;
		frame = 0;
	};
	const pointer = (event: PointerEvent) => {
		const canvas = surface.querySelector('canvas');
		if (!canvas) return;
		const box = canvas.getBoundingClientRect();
		const x = Math.max(
			0,
			Math.min(
				canvas.width - 1,
				Math.floor(((event.clientX - box.left) * canvas.width) / box.width)
			)
		);
		const y = Math.max(
			0,
			Math.min(
				canvas.height - 1,
				Math.floor(((event.clientY - box.top) * canvas.height) / box.height)
			)
		);
		if (event.type === 'pointerdown') {
			surface.focus();
			surface.setPointerCapture(event.pointerId);
		}
		pending = { type: 'mouse', x, y, buttons: event.buttons };
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
	};
	onDestroy(release);
</script>

<svelte:window on:blur={release} />

<div
	bind:this={surface}
	class="flex h-full w-full touch-none items-start justify-center overflow-hidden outline-none"
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
		const canvas = surface.querySelector('canvas');
		if (!canvas) return;
		const box = canvas.getBoundingClientRect();
		flush();
		send({
			type: 'mouse',
			x: Math.max(
				0,
				Math.min(
					canvas.width - 1,
					Math.floor(((event.clientX - box.left) * canvas.width) / box.width)
				)
			),
			y: Math.max(
				0,
				Math.min(
					canvas.height - 1,
					Math.floor(((event.clientY - box.top) * canvas.height) / box.height)
				)
			),
			buttons: event.buttons,
			deltaX: Math.sign(event.deltaX) * Math.ceil(Math.abs(event.deltaX) / 100),
			deltaY: Math.sign(event.deltaY) * Math.ceil(Math.abs(event.deltaY) / 100)
		});
	}}
>
	<FrameCanvas bind:this={frames} />
</div>
