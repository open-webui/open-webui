<script lang="ts" context="module">
	import { Marked } from 'marked';
	import markedKatexExtension from '$lib/utils/marked/katex-extension';
	import { footnoteExtension } from '$lib/utils/marked/footnote-extension';

	// Documents must not inherit chat's global extensions or soft-line-break settings.
	const documentMarkdown = new Marked(markedKatexExtension(), {
		breaks: false,
		extensions: [
			{
				...footnoteExtension(),
				renderer: (token) => `<sup class="footnote-ref">${token.escapedText}</sup>`
			}
		]
	});
</script>

<script lang="ts">
	import { getAllContexts, mount, unmount, setContext, onDestroy } from 'svelte';
	import { writable } from 'svelte/store';
	import DOMPurify from 'dompurify';
	import { v4 as uuidv4 } from 'uuid';
	import { downloadFileBlob } from '$lib/apis/terminal';
	import MarkdownTokens from '../Messages/Markdown/MarkdownTokens.svelte';
	import type { Token, Tokens } from 'marked';
	import { toast } from 'svelte-sonner';

	export let content: string;
	export let onSave: ((content: string) => Promise<void>) | null = null;
	export let saving = false;
	export let id: string;
	export let path = '';
	export let baseUrl = '';
	export let apiKey = '';
	export let chatId: string | null = null;
	export let resourceVersion = 0;
	export let onLocalLink: (path: string) => void = () => {};
	/** Local document resources never become arbitrary network requests. */
	function resolveDocumentPath(documentPath: string, reference: string): string | null {
		if (!reference || reference.startsWith('#') || reference.startsWith('//')) return null;
		if (/^[a-z][a-z\d+.-]*:/i.test(reference) && !/^[a-z]:[\\/]/i.test(reference)) return null;
		let path: string;
		try {
			path = decodeURIComponent(reference.split(/[?#]/)[0]).replace(/\\/g, '/');
		} catch {
			return null;
		}
		if (/[\x00-\x1f]/.test(path)) return null;
		const base = documentPath.replace(/\\/g, '/');
		if (!path.startsWith('/') && !/^[a-z]:\//i.test(path))
			path = base.slice(0, base.lastIndexOf('/') + 1) + path;
		const prefix = /^[a-z]:\//i.test(path) ? path.slice(0, 3) : '/';
		const parts: string[] = [];
		for (const part of path.slice(prefix.length).split('/')) {
			if (part === '..') parts.pop();
			else if (part && part !== '.') parts.push(part);
		}
		return prefix + parts.join('/');
	}

	let generation = 0;
	let urls = new Map<string, Promise<string | null>>();
	let objectUrls: string[] = [];
	const release = () => {
		generation++;
		objectUrls.forEach((url) => URL.revokeObjectURL(url));
		objectUrls = [];
		urls.clear();
	};
	onDestroy(release);
	const resolveImage = (reference: string): Promise<string | null> => {
		const file = resolveDocumentPath(path, reference);
		if (!file || !baseUrl) return Promise.resolve(null);
		if (!urls.has(file)) {
			const current = generation;
			urls.set(
				file,
				downloadFileBlob(baseUrl, apiKey, file, chatId ?? undefined).then((result) => {
					if (!result || current !== generation) return null;
					const url = URL.createObjectURL(result.blob);
					objectUrls.push(url);
					return url;
				})
			);
		}
		return urls.get(file)!;
	};
	const resources = {
		resolveImage,
		localPath: (ref: string) => (baseUrl ? resolveDocumentPath(path, ref) : null),
		open: (ref: string) => {
			const file = resolveDocumentPath(path, ref);
			if (file) onLocalLink(file);
		}
	};
	setContext('terminal-document', resources);
	$: {
		(resourceVersion, path, baseUrl, chatId);
		release();
	}

	function markdownTasks(tokens: Token[]) {
		const tasks: Tokens.ListItem[] = [];
		documentMarkdown.walkTokens(tokens, (token) => {
			if (token.type === 'list_item' && token.task) tasks.push(token as Tokens.ListItem);
		});
		return tasks;
	}

	function toggleMarkdownTask(content: string, index: number, checked: boolean) {
		const tasks = markdownTasks(documentMarkdown.lexer(content));
		if (!tasks[index]) throw new Error('Task no longer exists. Reload the file and try again.');
		if (tasks[index].checked === checked) return content;

		// Confirm the marker with the renderer's parser, so duplicates and code examples stay untouched.
		for (const match of content.matchAll(/\[[ xX]\]/g)) {
			const offset = match.index! + 1;
			if ((content[offset].toLowerCase() === 'x') === checked) continue;
			const updated = content.slice(0, offset) + (checked ? 'x' : ' ') + content.slice(offset + 1);
			const next = markdownTasks(documentMarkdown.lexer(updated));
			if (
				next.length === tasks.length &&
				next.every((task, i) => task.checked === (i === index ? checked : tasks[i].checked))
			) {
				return updated;
			}
		}
		throw new Error('Could not locate the task in the file. Reload the file and try again.');
	}

	const taskEnabled = writable(false);
	$: taskEnabled.set(!!onSave);
	setContext('markdown', {
		document: true,
		taskEnabled,
		onTaskClick: async ({
			item,
			checked,
			input
		}: {
			item: Tokens.ListItem;
			checked: boolean;
			input: HTMLInputElement;
		}) => {
			input.checked = !!item.checked;
			if (!onSave || saving) return;
			const previous = content;
			const wasChecked = !!item.checked;
			saving = true;
			try {
				const index = markdownTasks(tokens).indexOf(item);
				const updated = toggleMarkdownTask(content, index, checked);
				// Keep the rendered document in place while saving this single marker.
				parsedContent = content = updated;
				item.checked = input.checked = checked;
				await onSave(updated);
			} catch (error) {
				parsedContent = content = previous;
				item.checked = input.checked = wasChecked;
				toast.error(String(error));
			} finally {
				saving = false;
			}
		},
		allowRemoteContent: true,
		lexer: (source: string) => documentMarkdown.lexer(source),
		parseInline: (tokens: Token[]) =>
			documentMarkdown.Parser.parseInline(tokens, documentMarkdown.defaults),
		renderHtml
	});
	const context = getAllContexts();
	function renderHtml(node: HTMLElement, props: { id: string; tokens: Token[]; top: boolean }) {
		let components: ReturnType<typeof mount>[] = [];
		const destroy = () => {
			components.forEach((component) => unmount(component));
			components = [];
		};
		const update = ({ id, tokens, top }: typeof props) => {
			destroy();
			const prefix = `markdown-${uuidv4()}`;
			// Parse HTML together; keep Markdown components in slots the document cannot forge.
			node.replaceChildren(
				DOMPurify.sanitize(
					tokens
						.map((token, index) =>
							token.type === 'html'
								? token.text
								: `<div id="${prefix}-${index}" style="display: contents"></div>`
						)
						.join(''),
					{ RETURN_DOM_FRAGMENT: true }
				)
			);
			tokens.forEach((token, index) => {
				const target = node.querySelector(`#${prefix}-${index}`);
				if (target) {
					components.push(
						mount(MarkdownTokens, {
							target,
							context,
							props: { id: `${id}-${index}`, tokens: [token], top, editCodeBlock: false }
						})
					);
				}
			});
		};
		update(props);
		return { update, destroy };
	}
	let parsedContent: string | undefined;
	let tokens: Token[] = [];
	$: if (content !== parsedContent) {
		tokens = documentMarkdown.lexer(content);
		parsedContent = content;
	}
	const resolveHtmlImages = (node: HTMLElement) => {
		let alive = true;
		const update = () => {
			for (const img of node.querySelectorAll<HTMLImageElement>(
				'img:not([data-terminal-resolved])'
			)) {
				const src = img.getAttribute('src') ?? '';
				if (!resources.localPath(src)) continue;
				img.dataset.terminalResolved = 'true';
				img.removeAttribute('src');
				void resolveImage(src).then((url) => {
					if (alive && url) img.src = url;
				});
			}
		};
		const observer = new MutationObserver(update);
		observer.observe(node, { childList: true, subtree: true });
		update();
		return {
			destroy: () => {
				alive = false;
				observer.disconnect();
			}
		};
	};
	const openLink = (event: MouseEvent) => {
		const anchor = (event.target as Element)?.closest('a');
		const href = anchor?.getAttribute('href');
		if (href && resources.localPath(href)) {
			event.preventDefault();
			event.stopPropagation();
			resources.open(href);
		}
	};
</script>

{#key resourceVersion}
	<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
	<div
		use:resolveHtmlImages
		on:click|capture={openLink}
		class="document-markdown prose prose-sm dark:prose-invert min-w-0 max-w-none p-3"
	>
		<MarkdownTokens {id} {tokens} editCodeBlock={false} />
	</div>
{/key}

<style>
	.document-markdown {
		font-size: 0.75rem;
		line-height: 1.5;
		overflow-wrap: anywhere;
	}
	.document-markdown :global(h1),
	.document-markdown :global(h2),
	.document-markdown :global(h3),
	.document-markdown :global(h4),
	.document-markdown :global(h5),
	.document-markdown :global(h6) {
		margin: 1rem 0 0.375rem;
		font-weight: 600;
		line-height: 1.3;
	}
	.document-markdown :global(h1) {
		font-size: 1.125rem;
	}
	.document-markdown :global(h2) {
		font-size: 1rem;
	}
	.document-markdown :global(h3) {
		font-size: 0.875rem;
	}
	.document-markdown :global(h4),
	.document-markdown :global(h5),
	.document-markdown :global(h6) {
		font-size: 0.75rem;
	}
	.document-markdown :global(p),
	.document-markdown :global(ul),
	.document-markdown :global(ol) {
		margin: 0.5rem 0;
	}
	.document-markdown :global(li) {
		margin-block: 0.125rem;
	}
	.document-markdown :global(blockquote) {
		font-size: 0.75rem;
	}
	.document-markdown :global(strong) {
		font-weight: 600;
	}
	.document-markdown :global(hr) {
		margin: 0.75rem 0;
	}
	.document-markdown :global(img) {
		margin: 0.5rem 0;
	}
	.document-markdown :global(table) {
		font-size: 0.75rem;
		margin: 0.5rem 0;
	}
	.document-markdown :global(th),
	.document-markdown :global(td) {
		padding: 0.375rem 0.5rem !important;
	}
	.document-markdown :global(pre) {
		margin: 0.5rem 0;
		font-family: var(--font-mono);
	}
	.document-markdown :global(pre.hljs) {
		padding: 0.5rem 0.75rem;
	}
	.document-markdown :global(pre code) {
		font-size: 0.75rem;
	}
	.document-markdown :global(.codespan) {
		font-size: 0.95em;
	}
	.document-markdown :global(input[type='checkbox']:disabled) {
		cursor: default;
	}
	.document-markdown :global(.document-code-block) {
		border-radius: 0.5rem;
	}
	.document-markdown :global(.document-code-block > .sticky) {
		padding: 0.25rem 0.5rem;
	}
	.document-markdown :global(.document-code-block > .sticky button) {
		height: 1.5rem;
		padding-inline: 0.375rem;
		font-size: 0.6875rem;
	}
	.document-markdown > :global(:first-child) {
		margin-top: 0;
	}
	.document-markdown > :global(:last-child) {
		margin-bottom: 0;
	}
</style>
