<script lang="ts">
	import { marked } from 'marked';
	import type { Token } from 'marked';
	import { revertSanitizedResponseContent, unescapeHtml } from '$lib/utils';

	import { onMount, getContext, getAllContexts } from 'svelte';

	const context = getAllContexts();
	const i18n = getContext('i18n');

	import Image from '$lib/components/common/Image.svelte';
	import CodeBlock from '$lib/components/chat/Messages/CodeBlock.svelte';

	import MarkdownInlineTokens from '$lib/components/chat/Messages/MarkdownInlineTokens.svelte';

	export let id: string;
	export let tokens: Token[];
	export let top = true;

	let containerElement;

	const headerComponent = (depth: number) => {
		return 'h' + depth;
	};

	const renderer = new marked.Renderer();
	// For code blocks with simple backticks
	renderer.codespan = (code) => {
		return `<code class="codespan">${code.replaceAll('&amp;', '&')}</code>`;
	};

	let codes = [];
	renderer.code = (code, lang) => {
		codes.push({
			code: code,
			lang: lang
		});
		codes = codes;
		const codeId = `${id}-${codes.length}`;

		const interval = setInterval(() => {
			const codeElement = document.getElementById(`code-${codeId}`);
			if (codeElement) {
				clearInterval(interval);
				// If the code is already loaded, don't load it again
				if (codeElement.innerHTML) {
					return;
				}

				const element = new CodeBlock({
					target: codeElement,
					props: {
						id: `${id}-${codes.length}`,
						lang: lang,
						code: revertSanitizedResponseContent(code)
					},
					hydrate: true,
					$$inline: true,
					context: context
				});
			}
		}, 10);

		return `<div id="code-${id}-${codes.length}"></div>`;
	};

	let images = [];
	renderer.image = (href, title, text) => {
		images.push({
			href: href,
			title: title,
			text: text
		});
		images = images;

		const imageId = `${id}-${images.length}`;
		const interval = setInterval(() => {
			const imageElement = document.getElementById(`image-${imageId}`);
			if (imageElement) {
				clearInterval(interval);

				// If the image is already loaded, don't load it again
				if (imageElement.innerHTML) {
					return;
				}

				console.log('image', href, text);
				new Image({
					target: imageElement,
					props: {
						src: href,
						alt: text
					},
					$$inline: true
				});
			}
		}, 10);

		return `<div id="image-${id}-${images.length}"></div>`;
	};

	// Open all links in a new tab/window (from https://github.com/markedjs/marked/issues/655#issuecomment-383226346)
	const origLinkRenderer = renderer.link;
	renderer.link = (href, title, text) => {
		const html = origLinkRenderer.call(renderer, href, title, text);
		return html.replace(/^<a /, '<a target="_blank" rel="nofollow" ');
	};

	const { extensions, ...defaults } = marked.getDefaults() as marked.MarkedOptions & {
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		extensions: any;
	};

	$: if (tokens) {
		images = [];
		codes = [];
	}
</script>

<div bind:this={containerElement} class="flex flex-col">
	{#each tokens as token, tokenIdx (`${id}-${tokenIdx}`)}
		{#if token.type === 'code'}
			{#if token.lang === 'mermaid'}
				<pre class="mermaid">{revertSanitizedResponseContent(token.text)}</pre>
			{:else}
				<CodeBlock
					id={`${id}-${tokenIdx}`}
					lang={token?.lang ?? ''}
					code={revertSanitizedResponseContent(token?.text ?? '')}
				/>
			{/if}
		{:else}
			{@html marked.parse(token.raw, {
				...defaults,
				gfm: true,
				breaks: true,
				renderer
			})}
		{/if}
	{/each}
</div>
