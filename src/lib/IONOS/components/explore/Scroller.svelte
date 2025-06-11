<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { ScrollerItem } from './scrollerItem.d.ts';

	const dispatcher = createEventDispatcher();

	// Pixels per second
	const speed: number = 25;

	export let direction = 'left';
	export let items: ScrollerItem[] = [];

	let el: HTMLElement|null = null;

	function setAnimationPlayState(newState: string): void {
		if (el) {
			el.style.animationPlayState = newState;
		}
	}

	let scrollWidth: number;
	let fullWidth: number;
	let duration: number;

	$: {
		scrollWidth = items.length > 0 ? el?.scrollWidth ?? 0 : 0;
		fullWidth = scrollWidth / 2;
		duration = fullWidth / speed;
	}
</script>

<div
	class="full-width overflow-hidden position-relative my-5"
	role="marquee"
	on:mouseenter={() => { setAnimationPlayState('paused'); }}
	on:mouseleave={() => { setAnimationPlayState('running'); }}
	>
	<div
		bind:this={el}
		class="flex will-change-transform whitespace-nowrap {direction === 'left' ? 'slide-left' : 'slide-right'}"
		style:animation-duration={`${duration}s`}
		style:width={`${fullWidth * 2}px`}
	>
		{#each items as { id, text }}
			<button
				on:click={() => { dispatcher('click', id); }}
				data-id={id}
				class="flex justify-items-center items-center bg-white rounded-md h-20 mx-2 last:m-0 px-6 py-4 cursor-pointer"
			>
				<span class="w-full text-xs text-wrap text-blue-800 font-['OpenSans']">{ text } →</span>
			</button>
		{/each}
		{#each items as { id, text }}
			<button
				on:click={() => { dispatcher('click', id); }}
				data-id={id}
				class="flex justify-items-center items-center bg-white rounded-md h-20 mx-2 last:m-0 px-6 py-4 cursor-pointer"
			>
				<span class="w-full text-xs text-wrap text-blue-800 font-['OpenSans']">{ text } →</span>
			</button>
		{/each}
	</div>
</div>

<style>
.slide-left {
    animation: slide-left linear infinite;
}

.slide-right {
    animation: slide-right linear infinite;
}

span {
	width: 280px;
}

@keyframes slide-left {
    0% {
        transform: translateX(0);
    }
    100% {
        transform: translateX(-50%);
    }
}

@keyframes slide-right {
    0% {
        transform: translateX(-50%);
    }
    100% {
        transform: translateX(0);
    }
}
</style>
