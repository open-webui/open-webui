<script lang="ts">
	export let className = 'size-4';
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
	<rect x="9" y="2" width="6" height="12" rx="3" />
	<path
		stroke-linecap="round"
		stroke-linejoin="round"
		d="M5 10v1a7 7 0 0 0 14 0v-1M12 18v4m0 0H9m3 0h3"
	/>
</svg>
