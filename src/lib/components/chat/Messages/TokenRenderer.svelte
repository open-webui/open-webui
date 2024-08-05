<script lang="ts">
	import { revertSanitizedResponseContent } from '$lib/utils';

	import { marked } from 'marked';
	import CodeBlock from './CodeBlock.svelte';
	import Image from '$lib/components/common/Image.svelte';

	export let token;
	export let tokenIdx = 0;
	export let id;

	let element;
	let content;

	const renderer = new marked.Renderer();

	// For code blocks with simple backticks
	renderer.codespan = (code) => {
		return `<code>${code.replaceAll('&amp;', '&')}</code>`;
	};

	let codes = [];
	renderer.code = (code, lang) => {
		codes.push({ code, lang, id: codes.length });
		codes = codes;
		return `{{@CODE ${codes.length - 1}}}`;
	};

	let images = [];
	renderer.image = (href, title, text) => {
		images.push({ href, title, text });
		images = images;
		return `{{@IMAGE ${images.length - 1}}}`;
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

	$: if (token) {
		images = [];
		codes = [];
		content = marked
			.parse(token.raw, {
				...defaults,
				gfm: true,
				breaks: true,
				renderer
			})
			.split(/({{@IMAGE [^}]+}}|{{@CODE [^}]+}})/g);
	}
</script>

<div bind:this={element}>
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
	{:else if token.type === 'image'}
		<Image src={token.href} alt={token.text} />
	{:else}
		{#each content as part}
			{@html part.startsWith('{{@IMAGE ') || part.startsWith('{{@CODE ') ? '' : part}

			{#if images.length > 0 && part.startsWith('{{@IMAGE ')}
				{@const img = images[parseInt(part.match(/{{@IMAGE (\d+)}}/)[1])]}

				<div class="mt-6">
					<Image src={img.href} text={img.text} />
				</div>
			{:else if codes.length > 0 && part.startsWith('{{@CODE ')}
				{@const _code = codes[parseInt(part.match(/{{@CODE (\d+)}}/)[1])]}
				<div class="my-10 -mb-6">
					<CodeBlock
						id={`${id}-${tokenIdx}-${_code.id}`}
						lang={_code.lang}
						code={revertSanitizedResponseContent(_code.code)}
					/>
				</div>
			{/if}
		{/each}
	{/if}
</div>
