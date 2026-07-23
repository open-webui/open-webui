<script lang="ts">
	export let className = 'size-4';
	export let strokeWidth = '1.5';
</script>

<svg
	class={className}
	aria-hidden="true"
	xmlns="http://www.w3.org/2000/svg"
	viewBox="0 0 24 24"
	stroke-width={strokeWidth}
	fill="none"
>
	<path d="M6 20L18 20" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" />
	<path
		d="M12 4V16M12 16L15.5 12.5M12 16L8.5 12.5"
		stroke="currentColor"
		stroke-linecap="round"
		stroke-linejoin="round"
	/>
</svg>
