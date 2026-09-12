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
	<rect x="2" y="4" width="20" height="16" rx="3" fill="none" />
	<!-- The "1" -->
	<path stroke-linecap="round" stroke-linejoin="round" d="M7.5 9v6M6 10.5l1.5-1.5" />
	<!-- The ":" -->
	<path
		stroke-linecap="round"
		stroke-linejoin="round"
		d="M12 10.5v.01M12 13.5v.01"
		stroke-width="2"
	/>
	<!-- The other "1" -->
	<path stroke-linecap="round" stroke-linejoin="round" d="M16.5 9v6M15 10.5l1.5-1.5" />
</svg>
