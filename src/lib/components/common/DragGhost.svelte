<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

	let { x, y, children } = $props();

	let popupElement = $state(null);

	onMount(() => {
		document.body.appendChild(popupElement);
		document.body.style.overflow = 'hidden';
	});

	onDestroy(() => {
		document.body.removeChild(popupElement);
		document.body.style.overflow = 'unset';
	});
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->

<div
	bind:this={popupElement}
	class="fixed top-0 left-0 w-screen h-[100dvh] z-50 touch-none pointer-events-none"
>
	<div class=" absolute text-white z-99999" style="top: {y + 10}px; left: {x + 10}px;">
		{@render children?.()}
	</div>
</div>
