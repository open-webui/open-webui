<script>
	import { onDestroy } from 'svelte';
	import { replaceTokens, processResponseContent } from '$lib/utils';
	import { lexer } from '$lib/utils/marked';
	import { user } from '$lib/stores';

	import MarkdownTokens from './Markdown/MarkdownTokens.svelte';

	export let id = '';
	export let content;
	export let done = true;
	export let model = null;
	export let save = false;
	export let preview = false;

	export let paragraphTag = 'p';
	export let editCodeBlock = true;
	export let topPadding = false;

	export let sourceIds = [];

	export let onSave = () => {};
	export let onUpdate = () => {};

	export let onPreview = () => {};

	export let onSourceClick = () => {};
	export let onTaskClick = () => {};

	let tokens = [];
	let pendingUpdate = null;

	const parseTokens = () => {
		tokens = lexer(replaceTokens(processResponseContent(content), model?.name, $user?.name));
	};

	// Throttle parsing to once per animation frame while streaming
	$: if (content) {
		if (done) {
			cancelAnimationFrame(pendingUpdate);
			pendingUpdate = null;
			parseTokens();
		} else if (!pendingUpdate) {
			pendingUpdate = requestAnimationFrame(() => {
				pendingUpdate = null;
				parseTokens();
			});
		}
	}

	onDestroy(() => {
		cancelAnimationFrame(pendingUpdate);
	});
</script>

{#key id}
	<MarkdownTokens
		{tokens}
		{id}
		{done}
		{save}
		{preview}
		{paragraphTag}
		{editCodeBlock}
		{sourceIds}
		{topPadding}
		{onTaskClick}
		{onSourceClick}
		{onSave}
		{onUpdate}
		{onPreview}
	/>
{/key}
