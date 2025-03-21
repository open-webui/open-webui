<!--
Animates the slotted text with a shape-changing gradient effect.
The gradient colors, rotation and dimension change with an animation.
-->

<script lang="ts">
	import { onMount } from 'svelte';

	const COLOR_STOPS = [
		// 0% through 100% equally divided
		'hsl(238.71deg 46.67% 70.18%)',
		'hsl(281.35deg 31.97% 52.78%)',
		'hsl(311.26deg 100% 34.33%)',
		'hsl(265.71deg 32.07% 61.05%)',
		'hsl(222.68deg 59.99% 36.91%)',
	];

	const CYCLE_DURATION = 5000;

	let el: HTMLElement|null = null;

	onMount(() => {

		const rotate = (elements: string[], offset: number = 0) => {
			const count = elements.length;
			return [...elements.slice(offset % (count - 1)), ...elements.slice(0, offset % (count - 1))];
		};

		const colorMapper = (value: string, index: number) => [`--color-${index + 1}`, value];

		const animation = Array(COLOR_STOPS.length).fill(0)
			.map((_, i) => rotate(COLOR_STOPS, i))
			.map((elements) => Object.fromEntries(elements.map(colorMapper)));

		const timing = {
			duration: CYCLE_DURATION,
			iterations: Infinity,
		};

		el?.animate([...animation, ...animation.toReversed()], timing);
	});
</script>

<div class="animated" bind:this={el}>
	<slot />
</div>

<style>
	@property --pos-x {
		syntax: '<percentage>';
		inherits: false;
		initial-value: 0%;
	}

	@property --pos-y {
		syntax: '<percentage>';
		inherits: false;
		initial-value: 0%;
	}

	@property --rotation {
		syntax: "<angle>";
		inherits: false;
		initial-value: 90deg;
	}

	@property --color-1 {
		syntax: '<color>';
		inherits: false;
		initial-value: rgba(255, 255, 255, 0);
	}

	@property --color-2 {
		syntax: '<color>';
		inherits: false;
		initial-value: rgba(255, 255, 255, 0);
	}

	@property --color-3 {
		syntax: '<color>';
		inherits: false;
		initial-value: rgba(255, 255, 255, 0);
	}

	@property --color-4 {
		syntax: '<color>';
		inherits: false;
		initial-value: rgba(255, 255, 255, 0);
	}

	@property --color-5 {
		syntax: '<color>';
		inherits: false;
		initial-value: rgba(255, 255, 255, 0);
	}

	@property --background-size {
		syntax: '<percentage>';
		inherits: false;
		initial-value: 0;
	}

	.animated {
		--pos-x: 50%;
		--pos-y: 10%;
		--rotation: 90deg;

		/* fallback  */
		color: #000;

		background-image: linear-gradient(var(--rotation), var(--color-1), var(--color-2), var(--color-3), var(--color-4), var(--color-5));
		background-size: 200% 100%;
		background-clip: text;
		/* required for Chrome */
		-webkit-text-fill-color: transparent;
	}
</style>
