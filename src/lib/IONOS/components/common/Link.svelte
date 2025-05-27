<script lang="ts">
	/**
	 * No link text color for default state (i.e. to embed in fine print block text).
	 */
	export let passive: boolean = false;
	export let href: string = '';
	export let className: string = '';

	let classes = `${(passive
		? "underline hover:text-blue-400 active:text-blue-400 disabled:text-gray-450"
		: "text-blue-700 hover:text-blue-400 active:text-blue-400 hover:underline visited:text-blue-700 disabled:text-gray-450")} ${className}`;
</script>

{#if href !== ''}
	<a
		{...$$restProps}
		{href}
		class={classes}
		target="_blank"
		rel="noreferrer"
	>
		<slot />
	</a>
{:else}
	<button
		on:click|preventDefault
		{...$$restProps}
		class={classes}
	>
		<slot />
	</button>
{/if}
