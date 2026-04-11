<script lang="ts">
	import { onMount } from 'svelte';

	type TrailDot = {
		id: number;
		x: number;
		y: number;
		size: number;
		dx: number;
		dy: number;
		rotate: number;
	};

	const DOT_LIFE_MS = 650;
	const SPAWN_GAP_MS = 12;
	const MAX_DOTS = 20;

	let dots: TrailDot[] = [];
	let dotId = 0;
	let lastSpawnAt = 0;
	let prefersReducedMotion = false;

	function pruneDot(id: number) {
		dots = dots.filter((dot) => dot.id !== id);
	}

	function spawnDot(event: PointerEvent) {
		if (event.pointerType && event.pointerType !== 'mouse' && event.pointerType !== 'pen') {
			return;
		}

		const now = performance.now();
		if (now - lastSpawnAt < SPAWN_GAP_MS) {
			return;
		}
		lastSpawnAt = now;

		const size = 8 + Math.random() * 14;
		const dx = (Math.random() - 0.5) * 34;
		const dy = 16 + Math.random() * 26;

		const dot: TrailDot = {
			id: dotId++,
			x: event.clientX,
			y: event.clientY,
			size,
			dx,
			dy,
			rotate: Math.random() * 240 - 120
		};

		dots = [...dots, dot].slice(-MAX_DOTS);
		window.setTimeout(() => pruneDot(dot.id), DOT_LIFE_MS);
	}

	onMount(() => {
		prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
		if (prefersReducedMotion) {
			return;
		}

		const onPointerMove = (event: PointerEvent) => spawnDot(event);

		window.addEventListener('pointermove', onPointerMove, { passive: true });

		return () => {
			window.removeEventListener('pointermove', onPointerMove);
		};
	});
</script>

{#if !prefersReducedMotion}
	<div class="fixed inset-0 pointer-events-none z-[70] overflow-hidden">
		{#each dots as dot (dot.id)}
			<span
				class="trail-dot"
				style={`left:${dot.x}px; top:${dot.y}px; width:${dot.size}px; height:${dot.size}px; --trail-dx:${dot.dx}px; --trail-dy:${dot.dy}px; --trail-rotate:${dot.rotate}deg;`}
			/>
		{/each}
	</div>
{/if}

<style>
	.trail-dot {
		position: fixed;
		border-radius: 9999px;
		transform: translate(-50%, -50%);
		background:
			radial-gradient(circle at 35% 35%, rgba(255, 255, 255, 0.95) 0 12%, rgba(255, 0, 50, 0.95) 28%, rgba(255, 0, 50, 0.5) 56%, rgba(255, 0, 50, 0) 76%);
		box-shadow:
			0 0 10px rgba(255, 0, 50, 0.35),
			0 0 24px rgba(255, 0, 50, 0.2);
		filter: blur(0.2px);
		animation: trail-fade 650ms ease-out forwards;
		will-change: transform, opacity, filter;
		mix-blend-mode: screen;
	}

	@keyframes trail-fade {
		0% {
			opacity: 0;
			transform: translate(-50%, -50%) scale(0.15);
		}
		10% {
			opacity: 0.95;
		}
		100% {
			opacity: 0;
			transform: translate(
					calc(-50% + var(--trail-dx, 0px)),
					calc(-50% + var(--trail-dy, 24px))
				)
				rotate(var(--trail-rotate, 0deg))
				scale(0.1);
			filter: blur(2px);
		}
	}
</style>
