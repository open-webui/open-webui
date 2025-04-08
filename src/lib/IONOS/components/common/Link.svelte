<script lang="ts">
	/**
	 * No link text color for default state (i.e. to embed in fine print block text).
	 */
	export let passive: boolean = false;
	export let href: string = '';
</script>

<a
	{...$$restProps}
	{href}
	class={passive
		? "underline hover:text-blue-600 active:text-blue-500 visited:text-blue-950"
		: "text-blue-950 hover:text-blue-600 active:text-blue-500 hover:underline visited:text-blue-950"}
	target="_blank"
	rel="noreferrer"
>
	<slot />
</a>
