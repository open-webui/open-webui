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
	<path
		stroke-linecap="round"
		stroke-linejoin="round"
		d="m6.75 7.5 3 2.25-3 2.25m4.5 0h3m-9 8.25h13.5A2.25 2.25 0 0 0 21 18V6a2.25 2.25 0 0 0-2.25-2.25H5.25A2.25 2.25 0 0 0 3 6v12a2.25 2.25 0 0 0 2.25 2.25Z"
	/>
</svg>
