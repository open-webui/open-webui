<script lang="ts">
	export let className = 'w-4 h-4';
	export let strokeWidth = '1.5';
</script>

<svg
	class={className}
	aria-hidden="true"
	xmlns="http://www.w3.org/2000/svg"
	stroke-width={strokeWidth}
	fill="none"
	stroke="currentColor"
	viewBox="0 0 24 24"
>
	<!-- Top horizontal knob (left biased) -->
	<line x1="3" y1="8" x2="6" y2="8" stroke-linecap="round" />
	<line x1="12" y1="8" x2="21" y2="8" stroke-linecap="round" />
	<circle cx="9" cy="8" r="2.5" stroke="currentColor" fill="none" />

	<!-- Bottom horizontal knob (right biased) -->
	<line x1="3" y1="16" x2="12" y2="16" stroke-linecap="round" />
	<line x1="18" y1="16" x2="21" y2="16" stroke-linecap="round" />
	<circle cx="15" cy="16" r="2.5" stroke="currentColor" fill="none" />
</svg>
