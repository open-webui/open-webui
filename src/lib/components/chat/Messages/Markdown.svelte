<script>
	import { marked } from 'marked';
	import { replaceTokens, processResponseContent } from '$lib/utils';
	import { user } from '$lib/stores';
	
	import markedExtension from '$lib/utils/marked/extension';
	import markedKatexExtension from '$lib/utils/marked/katex-extension';

	import MarkdownTokens from './Markdown/MarkdownTokens.svelte';
	import { createEventDispatcher, getContext } from 'svelte';

	const dispatch = createEventDispatcher();

	export let id;
	export let content;
	export let model = null;
	export let save = false;

	let tokens = [];

	const options = {
		throwOnError: false
	};

	marked.use(markedKatexExtension(options));
	marked.use(markedExtension(options));

	$: (async () => {
		if (content) {
			tokens = marked.lexer(
				replaceTokens(processResponseContent(content), model?.name, $user?.name)
			);

			//find markdown tables in content
			const markdownTables = tokens.filter(token => token.type === 'table');
			if(markdownTables?.length > 0)
			{
				//get containsMarkdownTable context 
				const markdownTableTokens = getContext('markdownTableTokens');
				markdownTableTokens.set(markdownTables)
			};
		}
	})();
</script>

{#key id}
	<MarkdownTokens
		{tokens}
		{id}
		{save}
		on:update={(e) => {
			dispatch('update', e.detail);
		}}
		on:code={(e) => {
			dispatch('code', e.detail);
		}}
	/>
{/key}
