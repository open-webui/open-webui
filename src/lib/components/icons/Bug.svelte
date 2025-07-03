<script>
	export let className = 'size-6';
	export let strokeWidth = '1.5';
</script>

<svg
	xmlns="http://www.w3.org/2000/svg"
	fill="none"
	viewBox="0 0 24 24"
	stroke="currentColor"
	class={className}
	stroke-width={strokeWidth}
	aria-hidden="true"
>
	<!-- Bug body segments -->
	<ellipse cx="12" cy="14.5" rx="5" ry="7" fill="currentColor" stroke="none" opacity="0.7" />
	<ellipse cx="12" cy="7.5" rx="3.5" ry="2.5" fill="currentColor" stroke="none" />

	<!-- Body segment lines -->
	<path stroke-linecap="round" d="M7.5 12h9M7.5 15.5h9M8 18h8" stroke-width="1" opacity="0.6" />

	<!-- Antennae -->
	<path stroke-linecap="round" stroke-linejoin="round" d="M10 5.5l-2.5-3.5m6.5 3.5l2.5-3.5" />

	<!-- Eyes -->
	<circle cx="10" cy="7" r="1" fill="currentColor" />
	<circle cx="14" cy="7" r="1" fill="currentColor" />

	<!-- Left legs -->
	<path
		stroke-linecap="round"
		stroke-linejoin="round"
		d="M7 10l-4.5-2.5m0 0l1.5 2.5M7 13.5l-5 0m0 0l1.5 2.5M7 17l-4.5 2.5m0 0l1.5-2.5"
	/>

	<!-- Right legs -->
	<path
		stroke-linecap="round"
		stroke-linejoin="round"
		d="M17 10l4.5-2.5m0 0l-1.5 2.5M17 13.5l5 0m0 0l-1.5 2.5M17 17l4.5 2.5m0 0l-1.5-2.5"
	/>

	<!-- Wing outline -->
	<path
		stroke-linecap="round"
		stroke-linejoin="round"
		d="M8.5 9c0-1.5 1.5-3 3.5-3s3.5 1.5 3.5 3"
		stroke-width="1.2"
		opacity="0.5"
	/>
</svg>
