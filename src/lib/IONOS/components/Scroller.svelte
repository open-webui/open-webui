<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	const dispatcher = createEventDispatcher();

	// Pixels per second
	const speed = 25;

	export let direction = 'left';
	export let items;

	let el;

	$: scrollWidth = el?.scrollWidth;
	$: fullWidth = scrollWidth / 2;
	$: duration = fullWidth / speed;
</script>

<div
	class="full-width overflow-hidden position-relative my-5"
	on:mouseenter={() => { el.style.animationPlayState = 'paused'; }}
	on:mouseleave={() => { el.style.animationPlayState = 'running'; }}
	>
	<div
		bind:this={el}
		class="flex will-change-transform whitespace-nowrap {direction === 'left' ? 'slide-left' : 'slide-right'}"
		style:animation-duration={`${duration}s`}
		style:width={`${fullWidth * 2}px`}
	>
		{#each items as { id, text }}
			<span
				on:click={() => { dispatcher('click', id); }}
				data-id={id}
				class="flex justify-items-center items-center bg-white rounded-md h-20 mx-2 p-4 last:p-0 cursor-pointer"
			>
				<span class="w-full text-sm text-wrap">{ text } →</span>
			</span>
		{/each}
		{#each items as { id, text }}
			<span
				on:click={() => { dispatcher('click', id); }}
				data-id={id}
				class="flex justify-items-center items-center bg-white rounded-md h-20 mx-2 last:m-0 px-6 py-4 cursor-pointer"
			>
				<span class="w-full text-sm text-wrap">{ text } →</span>
			</span>
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
