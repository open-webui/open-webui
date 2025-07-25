<script lang="ts">
	import DOMPurify from 'dompurify';
	import { toast } from 'svelte-sonner';

	import type { Token } from 'marked';
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	import { WEBUI_BASE_URL } from '$lib/constants';
	import { copyToClipboard, unescapeHtml } from '$lib/utils';

	import PiiAwareInlineText from './PiiAwareInlineText.svelte';
	import CodespanToken from './MarkdownInlineTokens/CodespanToken.svelte';

	import Image from '$lib/components/common/Image.svelte';
	import KatexRenderer from './KatexRenderer.svelte';
	import Source from './Source.svelte';
	import HtmlToken from './HTMLToken.svelte';
	import TextToken from './MarkdownInlineTokens/TextToken.svelte';

	export let id: string;
	export let done = true;
	export let tokens: Token[];
	export let onSourceClick: Function = () => {};
	export let conversationId: string = '';
</script>

{#each tokens as token}
	{#if token.type === 'escape'}
		<PiiAwareInlineText
			text={unescapeHtml(token.text ?? '')}
			id={`${id}-text-${token.type}`}
			{conversationId}
			{done}
		/>
	{:else if token.type === 'html'}
		<HtmlToken {id} {token} {onSourceClick} {conversationId} {done} />
	{:else if token.type === 'link'}
		{#if token.tokens}
			<a href={token.href} target="_blank" rel="nofollow" title={token.title}>
				<svelte:self id={`${id}-a`} tokens={token.tokens} {onSourceClick} {conversationId} {done} />
			</a>
		{:else}
			<a href={token.href} target="_blank" rel="nofollow" title={token.title}>
				<PiiAwareInlineText text={token.text ?? ''} id={`${id}-a-text`} {conversationId} {done} />
			</a>
		{/if}
	{:else if token.type === 'image'}
		<Image src={token.href} alt={token.text} />
	{:else if token.type === 'strong'}
		<strong><svelte:self id={`${id}-strong`} tokens={token.tokens} {onSourceClick} {conversationId} {done} /></strong>
	{:else if token.type === 'em'}
		<em><svelte:self id={`${id}-em`} tokens={token.tokens} {onSourceClick} {conversationId} {done} /></em>
	{:else if token.type === 'codespan'}
		<CodespanToken {token} {done} />
	{:else if token.type === 'br'}
		<br />
	{:else if token.type === 'del'}
		<del><svelte:self id={`${id}-del`} tokens={token.tokens} {onSourceClick} {conversationId} {done} /></del>
	{:else if token.type === 'inlineKatex'}
		{#if token.text}
			<KatexRenderer content={token.text} displayMode={false} />
		{/if}
	{:else if token.type === 'iframe'}
		<iframe
			src="{WEBUI_BASE_URL}/api/v1/files/{token.fileId}/content"
			title={token.fileId}
			width="100%"
			frameborder="0"
		></iframe>
	{:else if token.type === 'text'}
		<PiiAwareInlineText
			text={token.raw ?? ''}
			id={`${id}-text-${token.type}`}
			{conversationId}
			{done}
		/>
	{/if}
{/each}
