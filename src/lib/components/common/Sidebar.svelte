<script lang="ts">
	import { quadInOut, quintIn } from 'svelte/easing';
	import { fade, slide } from 'svelte/transition';

	export let show = false;
	export let side = 'right';
	export let width = '200px';

	export let className = '';
	export let duration = 100;
</script>

{#if show}
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		class="absolute z-20 top-0 right-0 left-0 bottom-0 bg-white/20 dark:bg-black/5 w-full min-h-full h-full flex justify-center overflow-hidden overscroll-contain"
		on:mousedown={() => {
			show = false;
		}}
		transition:fade={{ duration: duration }}
	/>

	<div
		class="absolute z-30 shadow-xl {side === 'right' ? 'right-0' : 'left-0'} top-0 bottom-0"
		transition:slide={{ duration: duration, easing: quadInOut, axis: side === 'right' ? 'x' : 'y' }}
	>
		<div class="{className} h-full" style="width: {show ? width : '0px'}">
			<slot />
		</div>
	</div>
{/if}
