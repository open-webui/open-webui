<script lang="ts">
	import { afterUpdate } from 'svelte';

	export let open = false;


	// Manage the max-height of the collapsible content for snappy transitions
	let contentElement: HTMLElement;
  	let maxHeight = '0px'; // Initial max-height
	// After any state update, adjust the max-height for the transition
	afterUpdate(() => {
		if (open) {
			// Ensure the element is visible before measuring
			maxHeight = `${contentElement.scrollHeight}px`;
		} else {
			maxHeight = '0px';
		}
  	});

</script>

<style>
	.collapsible-content {
	  overflow: hidden;
	  transition: max-height 0.3s ease-out;
	  max-height: 0;
	}
</style>

<div>
	<button on:click={() => open = !open}>
		<slot name="head"></slot>
	</button>
	<div bind:this={contentElement} class="collapsible-content" style="max-height: {maxHeight};">
		<slot name="content"></slot>
	</div>
</div>