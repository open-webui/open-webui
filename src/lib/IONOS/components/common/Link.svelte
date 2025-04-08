<script lang="ts">
	export let href: string = '';
</script>

<a
	{...$$restProps}
	{href}
	class="text-blue-950 hover:text-blue-600 active:text-blue-500 hover:underline visited:text-blue-950"
	target="_blank"
	rel="noreferrer"
>
	<slot />
</a>
