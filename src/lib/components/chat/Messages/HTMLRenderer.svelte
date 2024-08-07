<script lang="ts">
	import Image from '$lib/components/common/Image.svelte';
	import CodeBlock from './CodeBlock.svelte';

	/* The html content of the tag */
	export let html; //: string;
	let parsedHTML = [html];

	export let images;
	export let codes;

	//  all images are in {{IMAGE_0}}, {{IMAGE_1}}....  format
	// all codes are in {{CODE_0}}, {{CODE_1}}....  format

	const rules = [];
	rules.forEach((rule) => {
		parsedHTML = parsedHTML.map((substr) => substr.split(rule.regex)).flat();
	});
</script>

{#each parsedHTML as part}
	{@const match = rules.find((rule) => rule.regex.test(part))}
	{#if match}
		<svelte:component this={match.component} {...match.props}>
			{@html part}
		</svelte:component>
	{:else}
		{@html part}
	{/if}
{/each}
