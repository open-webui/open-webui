<script lang="ts">
	import DOMPurify from 'dompurify';

	import { marked } from 'marked';
	import { createEventDispatcher, onMount } from 'svelte';

	const dispatch = createEventDispatcher();

	export let onClick: Function = () => {};
	export let title: string = 'HI';
	export let content: string;

	onMount(() => {
		const audio = new Audio(`/audio/notification.mp3`);
		audio.play();
	});
</script>

<button
	class="flex gap-2.5 text-left min-w-[var(--width)] w-full dark:bg-gray-850 dark:text-white bg-white text-black border border-gray-50 dark:border-gray-800 rounded-xl px-3.5 py-3.5"
	on:click={() => {
		onClick();
		dispatch('closeToast');
	}}
>
	<div class="flex-shrink-0 self-top -translate-y-0.5">
		<img src={'/static/favicon.png'} alt="favicon" class="size-7 rounded-full" />
	</div>

	<div>
		{#if title}
			<div class=" text-[13px] font-medium mb-0.5 line-clamp-1 capitalize">{title}</div>
		{/if}

		<div class=" line-clamp-2 text-xs self-center dark:text-gray-300 font-normal">
			{@html DOMPurify.sanitize(marked(content))}
		</div>
	</div>
</button>
