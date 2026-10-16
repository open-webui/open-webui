<script context="module">
	import { marked } from 'marked';

	import markedExtension from '$lib/utils/marked/extension';
	import markedKatexExtension from '$lib/utils/marked/katex-extension';
	import { disableSingleTilde } from '$lib/utils/marked/strikethrough-extension';
	import { mentionExtension } from '$lib/utils/marked/mention-extension';
	import colonFenceExtension from '$lib/utils/marked/colon-fence-extension';
	import footnoteExtension from '$lib/utils/marked/footnote-extension';
	import citationExtension from '$lib/utils/marked/citation-extension';

	const options = {
		throwOnError: false
	};

	marked.use(markedKatexExtension(options));
	marked.use(markedExtension(options));
	marked.use(citationExtension(options));
	marked.use(footnoteExtension(options));
	marked.use(colonFenceExtension(options));
	marked.use(disableSingleTilde);
	// Also set by RichTextInput, but messages can render before any input mounts.
	marked.use({ breaks: true });
	marked.use({
		extensions: [
			mentionExtension({ triggerChar: '@' }),
			mentionExtension({ triggerChar: '#' }),
			mentionExtension({ triggerChar: '$' })
		]
	});
</script>

<script>
	import { onDestroy, setContext } from 'svelte';
	import { replaceTokens, processResponseContent } from '$lib/utils';
	import { user } from '$lib/stores';

	import MarkdownTokens from './Markdown/MarkdownTokens.svelte';

	export let id = '';
	export let chatId = '';
	export let messageId = '';
	export let content;
	export let done = true;
	export let model = null;
	export let save = false;
	export let preview = false;
	export let compactPreview = false;

	export let paragraphTag = 'p';
	export let editCodeBlock = true;
	export let topPadding = false;
	export let allowEmbeds = false;
	export let allowHtml = true;
	export let allowRemoteContent = true;

	setContext('markdown', {
		get allowRemoteContent() {
			return allowRemoteContent;
		}
	});

	export let sourceIds = [];

	export let onSave = () => {};
	export let onUpdate = () => {};

	export let onPreview = () => {};

	export let onSourceClick = () => {};
	export let onTaskClick = () => {};
	export let onToolCallResolved = () => {};

	let tokens = [];
	let pendingUpdate = null;
	let lastContent = '';
	let lastParsedContent = '';

	const parseTokens = () => {
		if (content === lastContent) return;
		lastContent = content;

		const processed = replaceTokens(processResponseContent(content), model?.name, $user?.name);
		if (processed === lastParsedContent) return;
		lastParsedContent = processed;

		tokens = marked.lexer(processed);
		if (!allowHtml || !allowRemoteContent) {
			marked.walkTokens(tokens, (token) => {
				if (
					(!allowHtml && token.type === 'html') ||
					(!allowRemoteContent &&
						['html', 'image', 'iframe', 'mention', 'details', 'colonFence'].includes(token.type))
				) {
					const raw = token.raw;
					// Drop child tokens too, so blocked content cannot render through a nested renderer.
					for (const key of Object.keys(token)) Reflect.deleteProperty(token, key);
					Object.assign(token, { type: 'text', raw, text: raw });
				}
			});
		}
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
	onDestroy(() => {
		cancelAnimationFrame(pendingUpdate);
	});
</script>

{#key id}
	<MarkdownTokens
		{tokens}
		{id}
		{chatId}
		{messageId}
		{done}
		{save}
		{preview}
		{compactPreview}
		{paragraphTag}
		{editCodeBlock}
		{sourceIds}
		{topPadding}
		{allowEmbeds}
		{onTaskClick}
		{onSourceClick}
		{onToolCallResolved}
		{onSave}
		{onUpdate}
		{onPreview}
	/>
{/key}
