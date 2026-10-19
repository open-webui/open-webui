<script lang="ts">
	import DOMPurify from 'dompurify';
	import { toast } from 'svelte-sonner';

	import type { Token, Tokens } from 'marked';
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';

	const i18n = getContext('i18n');
	const terminalDocument = getContext<
		| {
				localPath: (ref: string) => string | null;
				resolveImage: (ref: string) => Promise<string | null>;
		  }
		| undefined
	>('terminal-document');
	const markdown = getContext<
		| { allowRemoteContent: boolean; document?: boolean; parseInline?: (tokens: Token[]) => string }
		| undefined
	>('markdown');

	import { WEBUI_BASE_URL } from '$lib/constants';
	import { skills, terminalSkills } from '$lib/stores';
	import { copyToClipboard, safeLinkUrl, unescapeHtml } from '$lib/utils';

	import Image from '$lib/components/common/Image.svelte';
	import KatexRenderer from './KatexRenderer.svelte';
	import Source from './Source.svelte';
	import HtmlToken from './HTMLToken.svelte';
	import TextToken from './MarkdownInlineTokens/TextToken.svelte';
	import CodespanToken from './MarkdownInlineTokens/CodespanToken.svelte';
	import MentionToken from './MarkdownInlineTokens/MentionToken.svelte';
	import NoteLinkToken from './MarkdownInlineTokens/NoteLinkToken.svelte';
	import SourceToken from './SourceToken.svelte';

	export let id: string;
	export let done = true;
	export let tokens: Token[];
	export let sourceIds = [];
	export let onSourceClick: Function = () => {};

	/**
	 * Check if a URL is a same-origin note link and return the note ID if so.
	 */
	const getNoteIdFromHref = (href: string): string | null => {
		try {
			const url = new URL(href, window.location.origin);
			if (url.origin === window.location.origin) {
				const match = url.pathname.match(/^\/notes\/([^/]+)$/);
				if (match) {
					return match[1];
				}
			}
		} catch {
			// Invalid URL
		}
		return null;
	};

	const getLinkToken = (token: Tokens.Link | Tokens.Generic) => {
		const isAutolink = !token.raw.startsWith('[');
		const isBracketed = token.raw.startsWith('<');
		// Use the source URL: decoding marked's escaped text also changes literal entities.
		const text = isBracketed ? token.raw.slice(1, -1) : token.raw;
		const href = isBracketed ? token.href.replace(token.text, () => text) : token.href;
		return {
			isAutolink,
			href,
			safeHref: safeLinkUrl(href),
			noteId: getNoteIdFromHref(href),
			text: isAutolink ? text : token.text
		};
	};

	/**
	 * Handle link clicks - intercept same-origin app URLs for in-app navigation
	 */
	const handleLinkClick = (e: MouseEvent, href: string) => {
		try {
			const url = new URL(href, window.location.origin);
			// Check if same origin and an in-app route
			if (
				url.origin === window.location.origin &&
				(url.pathname.startsWith('/notes/') ||
					url.pathname.startsWith('/c/') ||
					url.pathname.startsWith('/channels/'))
			) {
				e.preventDefault();
				goto(url.pathname + url.search + url.hash);
			}
		} catch {
			// Invalid URL, let browser handle it
		}
	};
	$: inlineHtml =
		markdown?.document && tokens.some((token) => token.type === 'html')
			? DOMPurify.sanitize(markdown.parseInline?.(tokens) ?? '')
			: null;
</script>

<!-- Keep paired inline HTML tags together; sanitizing individual tags loses their contents. -->
{#if inlineHtml !== null}
	{@html inlineHtml}
{/if}{#each inlineHtml === null ? tokens : [] as token, tokenIdx (tokenIdx)}
	{#if token.type === 'escape'}
		{unescapeHtml(token.text)}
	{:else if token.type === 'html'}
		<HtmlToken {id} {token} {onSourceClick} />
	{:else if token.type === 'link'}
		{@const linkToken = getLinkToken(token)}
		{#if linkToken.noteId && !markdown?.document && markdown?.allowRemoteContent !== false}
			<NoteLinkToken noteId={linkToken.noteId} href={linkToken.href} />
		{:else if token.tokens && !linkToken.isAutolink}
			<a
				href={linkToken.safeHref}
				target="_blank"
				rel="nofollow"
				title={token.title}
				on:click={(e) => handleLinkClick(e, linkToken.href)}
			>
				<svelte:self id={`${id}-a`} tokens={token.tokens} {sourceIds} {onSourceClick} {done} />
			</a>
		{:else}
			<a
				href={linkToken.safeHref}
				target="_blank"
				rel="nofollow"
				title={token.title}
				on:click={(e) => handleLinkClick(e, linkToken.href)}>{linkToken.text}</a
			>
		{/if}
	{:else if token.type === 'image'}
		{#if terminalDocument?.localPath(token.href)}
			{#await terminalDocument.resolveImage(token.href)}
				<span class="text-xs text-gray-400">{token.text}</span>
			{:then url}
				{#if url}<img src={url} alt={token.text} data-terminal-resolved="true" />{:else}<span
						class="text-xs text-gray-400">Image unavailable: {token.text}</span
					>{/if}
			{/await}
		{:else}<Image src={token.href} alt={token.text} allowExternal={true} />{/if}
	{:else if token.type === 'strong'}
		<strong
			><svelte:self id={`${id}-strong`} tokens={token.tokens} {sourceIds} {onSourceClick} /></strong
		>
	{:else if token.type === 'em'}
		<em><svelte:self id={`${id}-em`} tokens={token.tokens} {sourceIds} {onSourceClick} /></em>
	{:else if token.type === 'codespan'}
		<CodespanToken {token} {done} />
	{:else if token.type === 'br'}
		<br />
	{:else if token.type === 'del'}
		<del><svelte:self id={`${id}-del`} tokens={token.tokens} {sourceIds} {onSourceClick} /></del>
	{:else if token.type === 'underline'}
		<u><svelte:self id={`${id}-underline`} tokens={token.tokens} {sourceIds} {onSourceClick} /></u>
	{:else if token.type === 'inlineKatex'}
		{#if token.text}
			<KatexRenderer content={token.text} displayMode={token?.displayMode ?? false} />
		{/if}
	{:else if token.type === 'iframe'}
		<iframe
			src="{WEBUI_BASE_URL}/api/v1/files/{token.fileId}/content"
			title={token.fileId}
			width="100%"
			frameborder="0"
			on:load={(e) => {
				try {
					e.currentTarget.style.height =
						e.currentTarget.contentWindow.document.body.scrollHeight + 20 + 'px';
				} catch {}
			}}
		></iframe>
	{:else if token.type === 'mention'}
		{#if token.triggerChar === '$' && ![...($skills ?? []), ...($terminalSkills ?? [])].some((skill) => skill.id === token.id && skill.is_active)}
			{token.raw}
		{:else}
			<MentionToken {token} />
		{/if}
	{:else if token.type === 'footnote'}
		{@html DOMPurify.sanitize(
			`<sup class="footnote-ref footnote-ref-text">${token.escapedText}</sup>`
		) || ''}
	{:else if token.type === 'citation'}
		{#if (sourceIds ?? []).length > 0}
			<SourceToken {id} {token} {sourceIds} onClick={onSourceClick} />
		{:else}
			<TextToken {token} {done} />
		{/if}
	{:else if token.type === 'text'}
		{#if markdown?.document}
			{unescapeHtml(token.text)}
		{:else}
			<TextToken {token} {done} />
		{/if}
	{/if}
{/each}
