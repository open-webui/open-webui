<script lang="ts">
	interface Props {
		className?: string;
		strokeWidth?: string;
	}

	let { className = 'size-4', strokeWidth = '1.5' }: Props = $props();
</script>

<svg
	class={className}
	fill="none"
	stroke="currentColor"
	stroke-width={strokeWidth}
	viewBox="0 0 24 24"
	xmlns="http://www.w3.org/2000/svg"
>
	<path d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" stroke-linecap="round" stroke-linejoin="round" />
</svg>
