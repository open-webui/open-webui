<script lang="ts">
	import { fade, slide } from 'svelte/transition';


	interface Props {
		show?: boolean;
		side?: string;
		width?: string;
		className?: string;
		duration?: number;
		children?: import('svelte').Snippet;
	}

	let {
		show = $bindable(false),
		side = 'right',
		width = '200px',
		className = '',
		duration = 100,
		children
	}: Props = $props();
</script>

{#if show}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="absolute z-20 top-0 right-0 left-0 bottom-0 bg-white/20 dark:bg-black/5 w-full min-h-full h-full flex justify-center overflow-hidden overscroll-contain"
		onmousedown={() => {
			show = false;
		}}
		transition:fade={{ duration: duration }}
	></div>

	<div
		class="absolute z-30 shadow-xl {side === 'right' ? 'right-0' : 'left-0'} top-0 bottom-0"
		transition:slide={{ duration: duration, axis: side === 'right' ? 'x' : 'y' }}
	>
		<div class="{className} h-full" style="width: {show ? width : '0px'}">
			{@render children?.()}
		</div>
	</div>
{/if}
