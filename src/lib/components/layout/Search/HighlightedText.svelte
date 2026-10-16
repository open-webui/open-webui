<script lang="ts">
	export let text = '';
	export let query = '';
	// Render text nodes, never HTML from a search result.
	$: terms = [...new Set(query.trim().split(/\s+/).filter(Boolean))].slice(0, 12);
	$: expression = terms.length
		? new RegExp(
				`(${terms.map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`,
				'gi'
			)
		: null;
	$: parts = expression ? text.split(expression) : [text];
</script>

{#each parts as part, index}{#if expression && index % 2 === 1}<mark>{part}</mark
		>{:else}{part}{/if}{/each}
