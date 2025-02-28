<script lang="ts">
	interface Props {
		className?: string;
		strokeWidth?: string;
	}

	let { className = 'w-4 h-4', strokeWidth = '1.5' }: Props = $props();
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
		d="M8 8v8m0-8a2 2 0 1 0 0-4 2 2 0 0 0 0 4Zm0 8a2 2 0 1 0 0 4 2 2 0 0 0 0-4Zm6-2a2 2 0 1 1 4 0 2 2 0 0 1-4 0Zm0 0h-1a5 5 0 0 1-5-5v-.5"
		stroke-linecap="round"
		stroke-linejoin="round"
	/>
</svg>
