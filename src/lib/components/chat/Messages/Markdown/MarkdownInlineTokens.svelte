<script lang="ts">
	import type { Token } from 'marked';
	import { goto } from '$app/navigation';

	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { terminalServers } from '$lib/stores';
	import { unescapeHtml } from '$lib/utils';

	import Image from '$lib/components/common/Image.svelte';
	import KatexRenderer from './KatexRenderer.svelte';
	import HtmlToken from './HTMLToken.svelte';
	import TextToken from './MarkdownInlineTokens/TextToken.svelte';
	import CodespanToken from './MarkdownInlineTokens/CodespanToken.svelte';
	import MentionToken from './MarkdownInlineTokens/MentionToken.svelte';
	import NoteLinkToken from './MarkdownInlineTokens/NoteLinkToken.svelte';
	import SourceToken from './SourceToken.svelte';

	export let id: string;
	export let done = true;
	export let tokens: Token[];
	export let sourceIds: string[] = [];
	export let onSourceClick: CallableFunction = () => {};

	type TerminalServerEntry = {
		id?: string | null;
		connection_type?: 'system' | 'direct';
	};

	type SandboxTarget = {
		terminalId: string | null;
		path: string;
	};

	const isAbsoluteSandboxPath = (path: string): boolean => {
		const normalized = path.replace(/\\/g, '/');
		return (
			normalized.startsWith('/') ||
			(normalized.length >= 3 &&
				normalized[1] === ':' &&
				normalized[2] === '/' &&
				/[A-Za-z]/.test(normalized[0]))
		);
	};

	const getSystemTerminalId = (terminalId: string | null): string | null => {
		if (!terminalId) {
			return null;
		}

		const terminal = (($terminalServers ?? []) as TerminalServerEntry[]).find(
			(server) => server?.id === terminalId && server?.connection_type !== 'direct'
		);
		return terminal?.id ?? null;
	};

	const getSandboxTerminalId = (): string | null => {
		const systemTerminals = (($terminalServers ?? []) as TerminalServerEntry[]).filter(
			(server) => server?.id && server?.connection_type !== 'direct'
		);
		return systemTerminals.length === 1 ? (systemTerminals[0].id ?? null) : null;
	};

	const normalizeExplicitSandboxPath = (path: string): string => {
		if (/^\/[A-Za-z]:\//.test(path)) {
			return path.slice(1);
		}

		return path;
	};

	const getSandboxTarget = (href: string): SandboxTarget | null => {
		if (!href?.startsWith('sandbox:')) {
			return null;
		}

		if (href.startsWith('sandbox://')) {
			const match = /^sandbox:\/\/([^/]+)(\/.*)$/.exec(href);
			if (!match) {
				return null;
			}

			try {
				const terminalId = decodeURIComponent(match[1]);
				const path = normalizeExplicitSandboxPath(decodeURIComponent(match[2]));
				if (!terminalId || !isAbsoluteSandboxPath(path) || path.includes('\0')) {
					return null;
				}
				return { terminalId, path };
			} catch {
				return null;
			}
		}

		try {
			const path = href.slice('sandbox:'.length);
			if (!isAbsoluteSandboxPath(path) || path.includes('\0')) {
				return null;
			}

			return { terminalId: null, path };
		} catch {
			return null;
		}
	};

	const resolveSandboxUrl = (href: string, download: boolean): string => {
		const target = getSandboxTarget(href);
		if (!target) {
			return href;
		}

		const terminalId = target.terminalId
			? getSystemTerminalId(target.terminalId)
			: getSandboxTerminalId();
		if (!terminalId) {
			return href;
		}

		const params = new URLSearchParams({
			path: target.path,
			download: download ? 'true' : 'false'
		});
		return `${WEBUI_API_BASE_URL}/terminals/${encodeURIComponent(terminalId)}/files/content?${params.toString()}`;
	};

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
</script>

{#each tokens as token, tokenIdx (tokenIdx)}
	{#if token.type === 'escape'}
		{unescapeHtml(token.text)}
	{:else if token.type === 'html'}
		<HtmlToken {id} {token} />
	{:else if token.type === 'link'}
		{@const href = resolveSandboxUrl(token.href, true)}
		{@const noteId = getNoteIdFromHref(href)}
		{#if noteId}
			<NoteLinkToken {noteId} {href} />
		{:else if token.tokens}
			<a
				{href}
				target="_blank"
				rel="nofollow"
				title={token.title}
				on:click={(e) => handleLinkClick(e, href)}
			>
				<svelte:self id={`${id}-a`} tokens={token.tokens} {onSourceClick} {done} />
			</a>
		{:else}
			<a
				{href}
				target="_blank"
				rel="nofollow"
				title={token.title}
				on:click={(e) => handleLinkClick(e, href)}>{token.text}</a
			>
		{/if}
	{:else if token.type === 'image'}
		<Image src={resolveSandboxUrl(token.href, false)} alt={token.text} />
	{:else if token.type === 'strong'}
		<strong><svelte:self id={`${id}-strong`} tokens={token.tokens} {onSourceClick} /></strong>
	{:else if token.type === 'em'}
		<em><svelte:self id={`${id}-em`} tokens={token.tokens} {onSourceClick} /></em>
	{:else if token.type === 'codespan'}
		<CodespanToken {token} {done} />
	{:else if token.type === 'br'}
		<br />
	{:else if token.type === 'del'}
		<del><svelte:self id={`${id}-del`} tokens={token.tokens} {onSourceClick} /></del>
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
				const iframe = e.currentTarget as HTMLIFrameElement;
				try {
					const body = iframe.contentWindow?.document.body;
					if (body) {
						iframe.style.height = body.scrollHeight + 20 + 'px';
					}
				} catch {
					// Cross-origin iframe content cannot be measured.
				}
			}}
		></iframe>
	{:else if token.type === 'mention'}
		<MentionToken {token} />
	{:else if token.type === 'footnote'}
		<sup class="footnote-ref footnote-ref-text">{unescapeHtml(token.escapedText)}</sup>
	{:else if token.type === 'citation'}
		{#if (sourceIds ?? []).length > 0}
			<SourceToken {id} {token} {sourceIds} onClick={onSourceClick} />
		{:else}
			<TextToken {token} {done} />
		{/if}
	{:else if token.type === 'text'}
		<TextToken {token} {done} />
	{/if}
{/each}
