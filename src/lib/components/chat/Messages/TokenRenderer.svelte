<script lang="ts">
	import { revertSanitizedResponseContent } from '$lib/utils';

	import { marked } from 'marked';
	import CodeBlock from './CodeBlock.svelte';
	import Image from '$lib/components/common/Image.svelte';
	import { stringify } from 'postcss';

	export let token;
	export let tokenIdx = 0;
	export let id;

	const renderer = new marked.Renderer();

	// For code blocks with simple backticks
	renderer.codespan = (code) => {
		return `<code>${code.replaceAll('&amp;', '&')}</code>`;
	};

	// renderer.code = (code, lang) => {
	// 	const element = document.createElement('div');
	// 	new CodeBlock({
	// 		target: element,
	// 		props: {
	// 			id: `${id}-${tokenIdx}`,
	// 			lang: lang ?? '',
	// 			code: revertSanitizedResponseContent(code ?? '')
	// 		}
	// 	});
	// 	return element.innerHTML;
	// };

	// renderer.image = (href, title, text) => {
	// 	const element = document.createElement('pre');
	// 	new Image({
	// 		target: element,
	// 		props: {
	// 			src: href,
	// 			alt: text
	// 		}
	// 	});
	// 	return element.innerHTML;
	// };

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
</script>

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
