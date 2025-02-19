<script lang="ts">
	export let className = 'size-4';
	export let strokeWidth = '1.5';
</script>

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class={className}>
	<g
		fill="none"
		stroke="currentColor"
		stroke-linecap="round"
		stroke-linejoin="round"
		stroke-width={strokeWidth}
	>
		<rect width="18" height="18" x="3" y="3" rx="2" />
		<path d="M9 3v18m7-6l-3-3l3-3" />
	</g>
</svg>
