<script lang="ts">
	export let token;
	export let onClick: Function = () => {};

	let id = '';
	function extractDataAttribute(input) {
		// Use a regular expression to extract the value of the `data` attribute
		const match = input.match(/data="([^"]*)"/);
		// Check if a match was found and return the first captured group
		return match ? match[1] : null;
	}

	$: id = extractDataAttribute(token.text);
</script>

<button
	class="text-xs font-medium px-1.5 py-0.5 dark:bg-white/5 dark:hover:bg-white/10 bg-black/5 hover:bg-black/10 transition rounded-lg"
	on:click={() => {
		onClick(id);
	}}
>
	{id}
</button>
