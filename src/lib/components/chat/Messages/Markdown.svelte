<script>
	import { marked } from 'marked';
	import { replaceTokens, processResponseContent } from '$lib/utils';
	import { user } from '$lib/stores';
	import { onMount, onDestroy } from 'svelte';

	import markedExtension from '$lib/utils/marked/extension';
	import markedKatexExtension from '$lib/utils/marked/katex-extension';
	import { mentionExtension } from '$lib/utils/marked/mention-extension';

	import MarkdownTokens from './Markdown/MarkdownTokens.svelte';

	export let id = '';
	export let content;
	export let done = true;
	export let model = null;
	export let save = false;
	export let preview = false;

	export let editCodeBlock = true;
	export let topPadding = false;

	export let sourceIds = [];

	export let onSave = () => {};
	export let onUpdate = () => {};

	export let onPreview = () => {};
	export let onSourceClick = () => {};
	export let onTaskClick = () => {};

	let tokens = [];
	let pendingContent = null;
	let parseTimeout = null;
	let lastParsedContent = '';

	// Throttle interval in ms - parse less frequently during streaming
	const STREAMING_THROTTLE = 100; // 10 updates per second max during streaming
	const DONE_DELAY = 50; // Small delay when done to ensure final parse

	const options = {
		throwOnError: false,
		breaks: true
	};

	marked.use(markedKatexExtension(options));
	marked.use(markedExtension(options));
	marked.use({
		extensions: [mentionExtension({ triggerChar: '@' }), mentionExtension({ triggerChar: '#' })]
	});

	const parseContent = (contentToParse) => {
		if (contentToParse && contentToParse !== lastParsedContent) {
			lastParsedContent = contentToParse;
			tokens = marked.lexer(
				replaceTokens(processResponseContent(contentToParse), sourceIds, model?.name, $user?.name)
			);
		}
	};

	const scheduleParse = () => {
		// If done, clear any pending timeouts and parse immediately with minimal delay
		if (done) {
			if (parseTimeout) {
				clearTimeout(parseTimeout);
			}
			parseTimeout = setTimeout(() => {
				if (pendingContent !== null) {
					parseContent(pendingContent);
					pendingContent = null;
				}
				parseTimeout = null;
			}, DONE_DELAY);
			return;
		}

		// During streaming, act as a true throttle (not a debounce)
		// If a timeout is already scheduled, do nothing and let it fire
		if (parseTimeout) {
			return;
		}

		parseTimeout = setTimeout(() => {
			if (pendingContent !== null) {
				parseContent(pendingContent);
				pendingContent = null;
			}
			parseTimeout = null;
		}, STREAMING_THROTTLE);
	};

	// Use a reactive statement that just schedules parsing instead of doing it immediately
	$: {
		if (content) {
			pendingContent = content;
			scheduleParse();
		}
	}

	onDestroy(() => {
		if (parseTimeout) {
			clearTimeout(parseTimeout);
		}
	});
</script>

{#key id}
	<MarkdownTokens
		{tokens}
		{id}
		{done}
		{save}
		{preview}
		{editCodeBlock}
		{topPadding}
		{onTaskClick}
		{onSourceClick}
		{onSave}
		{onUpdate}
		{onPreview}
	/>
{/key}
