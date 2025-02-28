<script lang="ts">
	interface Props {
		className?: string;
		strokeWidth?: string;
	}

	let { className = 'size-5', strokeWidth = '2' }: Props = $props();
</script>

<svg
	class={className}
	fill="none"
	stroke="currentColor"
	stroke-width={strokeWidth}
	viewBox="0 0 24 24"
	xmlns="http://www.w3.org/2000/svg"
>
	<path
		d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25H12"
		stroke-linecap="round"
		stroke-linejoin="round"
	/>
</svg>
