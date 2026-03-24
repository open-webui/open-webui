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
	<circle cx="12" cy="12" r="8" stroke-linecap="round" stroke-linejoin="round" />
	<circle cx="12" cy="12" r="4" stroke-linecap="round" stroke-linejoin="round" />
	<circle cx="12" cy="12" r="1.5" stroke-linecap="round" stroke-linejoin="round" />
	<path d="M12 2v2" stroke-linecap="round" stroke-linejoin="round" />
	<path d="M22 12h-2" stroke-linecap="round" stroke-linejoin="round" />
	<path d="M12 20v2" stroke-linecap="round" stroke-linejoin="round" />
	<path d="M2 12h2" stroke-linecap="round" stroke-linejoin="round" />
</svg>
