<script lang="ts">
	interface Props {
		className?: string;
		strokeWidth?: string;
	}

	let { className = 'w-4 h-4', strokeWidth = '1.5' }: Props = $props();
</script>

<svg
	xmlns="http://www.w3.org/2000/svg"
	fill="none"
	viewBox="0 0 24 24"
	stroke-width={strokeWidth}
	stroke="currentColor"
	class={className}
>
	<path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
</svg>
