<script>
	import { onDestroy } from 'svelte';
	import { marked } from 'marked';
	import { replaceTokens, processResponseContent } from '$lib/utils';
	import { user } from '$lib/stores';

	import markedExtension from '$lib/utils/marked/extension';
	import markedKatexExtension from '$lib/utils/marked/katex-extension';
	import { disableSingleTilde } from '$lib/utils/marked/strikethrough-extension';
	import { mentionExtension } from '$lib/utils/marked/mention-extension';
	import colonFenceExtension from '$lib/utils/marked/colon-fence-extension';

	import MarkdownTokens from './Markdown/MarkdownTokens.svelte';
	import footnoteExtension from '$lib/utils/marked/footnote-extension';
	import citationExtension from '$lib/utils/marked/citation-extension';

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
	let lastContent = '';
	let lastParsedContent = '';

	const options = {
		throwOnError: false,
		breaks: true
	};

	marked.use(markedKatexExtension(options));
	marked.use(markedExtension(options));
	marked.use(citationExtension(options));
	marked.use(footnoteExtension(options));
	marked.use(colonFenceExtension(options));
	marked.use(disableSingleTilde);
	marked.use({
		extensions: [
			mentionExtension({ triggerChar: '@' }),
			mentionExtension({ triggerChar: '#' }),
			mentionExtension({ triggerChar: '$' })
		]
	});

	const MAX_TOOL_IMAGES = 5;

	const stripOldToolImages = (str) => {
		const matches = [];
		let searchPos = 0;
		while (true) {
			const pos = str.indexOf('files="', searchPos);
			if (pos === -1) break;
			const valueStart = pos + 7;
			const valueEnd = str.indexOf('"', valueStart);
			if (valueEnd === -1) break;
			const value = str.substring(valueStart, valueEnd);
			if (value.includes('data:image/')) {
				matches.push({ valueStart, valueEnd });
			}
			searchPos = valueEnd + 1;
		}

		if (matches.length <= MAX_TOOL_IMAGES) return str;

		const cutoff = matches.length - MAX_TOOL_IMAGES;
		let result = str;
		for (let i = cutoff - 1; i >= 0; i--) {
			const m = matches[i];
			result = result.substring(0, m.valueStart) + result.substring(m.valueEnd);
		}
		return result;
	};

	const parseTokens = () => {
		if (content === lastContent) return;
		lastContent = content;

		let processed = replaceTokens(processResponseContent(content), model?.name, $user?.name);
		processed = stripOldToolImages(processed);
		if (processed === lastParsedContent) return;
		lastParsedContent = processed;

		tokens = marked.lexer(processed);
	};

	const updateHandler = (content) => {
		if (content) {
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
	};

	$: updateHandler(content);

	// Throttle parsing to once per animation frame while streaming
	$: onDestroy(() => {
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
