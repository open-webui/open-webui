<script lang="ts">
	interface Props {
		className?: string;
		strokeWidth?: string;
	}

	let { className = 'size-3', strokeWidth = '1.5' }: Props = $props();
</script>

<svg
	xmlns="http://www.w3.org/2000/svg"
	fill="none"
	viewBox="0 0 24 24"
	stroke-width={strokeWidth}
	stroke="currentColor"
	class={className}
>
	<path
		stroke-linecap="round"
		stroke-linejoin="round"
		d="m3.75 13.5 10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75Z"
	/>
</svg>
