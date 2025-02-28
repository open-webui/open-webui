<script lang="ts">
	interface Props {
		children?: import('svelte').Snippet;
	}

	let { children }: Props = $props();
</script>

<div class=" self-center font-semibold line-clamp-1 flex gap-1 items-center">
	{@render children?.()}
</div>
