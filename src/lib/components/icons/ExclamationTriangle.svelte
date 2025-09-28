<script lang="ts">
	export let size: 'sm' | 'md' | 'lg' | null = null;
	export let className: string = '';
	export let strokeWidth = '1.5';
</script>

<svg
	xmlns="http://www.w3.org/2000/svg"
	fill="none"
	viewBox="0 0 24 24"
	stroke-width={strokeWidth}
	stroke="currentColor"
	class="{size === 'sm'
		? 'w-5 h-5'
		: size === 'md'
		? 'w-6 h-6'
		: size === 'lg'
		? 'w-7 h-7'
		: ''} {className}"
>
	<path
		stroke-linecap="round"
		stroke-linejoin="round"
		d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
	/>
</svg>