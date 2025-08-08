<script>
	import { user } from '$lib/stores';
	import { processResponseContent, replaceTokens } from '$lib/utils';
	import { marked } from 'marked';

	import markedCodeExtension from '$lib/utils/marked/code-extension';
	import markedExtension from '$lib/utils/marked/extension';
	import markedKatexExtension from '$lib/utils/marked/katex-extension';

	import MarkdownTokens from './Markdown/MarkdownTokens.svelte';

	export let id = '';
	export let content;
	export let done = true;
	export let model = null;
	export let save = false;
	export let preview = false;

	export let sourceIds = [];

	export let onSave = () => {};
	export let onUpdate = () => {};

	export let onPreview = () => {};

	export let onSourceClick = () => {};
	export let onTaskClick = () => {};

	let tokens = [];

	const options = {
		throwOnError: false,
		breaks: true
	};

	marked.use(markedCodeExtension(options));
	marked.use(markedKatexExtension(options));
	marked.use(markedExtension(options));

	$: (async () => {
		if (content) {
			tokens = marked.lexer(
				replaceTokens(processResponseContent(content), sourceIds, model?.name, $user?.name)
			);
		}
	})();
</script>

{#key id}
	<MarkdownTokens
		{tokens}
		{id}
		{done}
		{save}
		{preview}
		{onTaskClick}
		{onSourceClick}
		{onSave}
		{onUpdate}
		{onPreview}
	/>
{/key}
