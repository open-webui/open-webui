<script>
	import { marked } from 'marked';
	import markedKatex from '$lib/utils/marked/katex-extension';
	import { replaceTokens, processResponseContent } from '$lib/utils';
	import { user } from '$lib/stores';

	import MarkdownTokens from './Markdown/MarkdownTokens.svelte';

	export let id;
	export let content;
	export let model = null;

	let tokens = [];

	const options = {
		throwOnError: false
	};

	marked.use(markedKatex(options));

	$: (async () => {
		if (content) {
			tokens = marked.lexer(
				replaceTokens(processResponseContent(content), model?.name, $user?.name)
			);
		}
	})();
</script>

{#key id}
	<MarkdownTokens {tokens} {id} />
{/key}
