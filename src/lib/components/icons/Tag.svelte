<script lang="ts">
	export let className = 'size-4';
	export let strokeWidth = '1.8';
</script>

<svg
	xmlns="http://www.w3.org/2000/svg"
	fill="none"
	viewBox="0 0 24 24"
	stroke-width={strokeWidth}
	stroke="currentColor"
	class={className}
>
	<!-- Tag body with pointed end -->
	<path d="M4 12 L8 7 H21 V17 H8 L4 12 Z" stroke="currentColor" fill="none" />

	<!-- Tag hole -->
	<circle cx="10" cy="12" r="0.75" fill="currentColor" stroke="currentColor" />
</svg>
