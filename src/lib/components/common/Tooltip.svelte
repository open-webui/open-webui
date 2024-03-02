<script lang="ts">
	import { onDestroy } from 'svelte';
	import tippy from 'tippy.js';

	export let placement = 'top';
	export let content = `I'm a tooltip!`;

	let tooltipElement;
	let tooltipInstance;

	$: if (tooltipElement && content) {
		if (tooltipInstance) {
			tooltipInstance[0]?.destroy();
		}
		tooltipInstance = tippy(tooltipElement, {
			content: content,
			placement: placement,
			allowHTML: true
		});
	}

	onDestroy(() => {
		if (tooltipInstance) {
			tooltipInstance[0]?.destroy();
		}
	});
</script>

<div bind:this={tooltipElement}>
	<slot />
</div>
