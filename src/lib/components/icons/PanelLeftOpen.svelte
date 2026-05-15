<script lang="ts">
	export let className = 'size-5';
	export let strokeWidth = '1.5';
</script>

<svg
	aria-hidden="true"
	xmlns="http://www.w3.org/2000/svg"
	fill="none"
	viewBox="0 0 24 24"
	stroke-width={strokeWidth}
	stroke="currentColor"
	class={className}
>
	<rect
		x="3"
		y="3"
		width="18"
		height="18"
		rx="2"
		ry="2"
		stroke-linecap="round"
		stroke-linejoin="round"
	/>
	<path d="M9 3v18" stroke-linecap="round" stroke-linejoin="round" />
	<path d="m14 9 3 3-3 3" stroke-linecap="round" stroke-linejoin="round" />
</svg>
