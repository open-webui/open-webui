<script lang="ts">
	/**
	 * No link text color for default state (i.e. to embed in fine print block text).
	 */
	export let passive: boolean = false;
	export let href: string = '';
	export let className: string = '';
</script>

<a
	on:click
	{...$$restProps}
	{href}
	class={`${(passive
		? "underline hover:text-blue-400 active:text-blue-400 disabled:text-gray-450"
		: "text-blue-700 hover:text-blue-400 active:text-blue-400 hover:underline visited:text-blue-700 disabled:text-gray-450")} ${className}`}
	target="_blank"
	rel="noreferrer"
>
	<slot />
</a>
