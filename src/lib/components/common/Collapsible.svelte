<script lang="ts">
	import { slide } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';
	export let open = false;
	export let className = '';
</script>

<div class={className}>
	<button on:click={() => (open = !open)}>
		<slot />
	</button>

	{#if open}
		<div transition:slide={{ duration: 300, easing: quintOut, axis: 'y' }}>
			<slot name="content" />
		</div>
	{/if}
</div>
