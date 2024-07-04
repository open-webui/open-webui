<script lang="ts">
	export let open = false;
	export let className = '';

	// Manage the max-height of the collapsible content for snappy transitions
	let contentElement: HTMLElement;
	let maxHeight = '0px'; // Initial max-height

	$: if (contentElement?.scrollHeight) {
		if (open) {
			// Ensure the element is visible before measuring
			maxHeight = `${contentElement.scrollHeight}px`;
		} else {
			maxHeight = '0px';
		}
	}
</script>

<div class={className}>
	<button on:click={() => (open = !open)}>
		<slot name="head" />
	</button>
	<div bind:this={contentElement} class={`collapsible-content ${open ? 'mt-1' : '!mt-0'}`} style="max-height: {maxHeight};">
		<slot name="content" />
	</div>
</div>

<style>
	.collapsible-content {
		overflow: hidden;
		transition: all 0.3s ease-out;
		max-height: 0;
	}
</style>
