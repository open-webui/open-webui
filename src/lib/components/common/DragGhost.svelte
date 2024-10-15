<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

	export let x;
	export let y;

	let popupElement = null;

	onMount(() => {
		document.body.appendChild(popupElement);
		document.body.style.overflow = 'hidden';
	});

	onDestroy(() => {
		document.body.removeChild(popupElement);
		document.body.style.overflow = 'unset';
	});
</script>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-static-element-interactions -->

<div
	bind:this={popupElement}
	class=" absolute text-white z-[99999]"
	style="top: {y}px; left: {x}px;"
>
	<slot></slot>
</div>
