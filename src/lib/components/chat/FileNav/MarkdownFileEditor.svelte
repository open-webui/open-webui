<script lang="ts">
	import { v4 as uuidv4 } from 'uuid';
	import { getAllContexts, getContext, mount, unmount, onDestroy, tick } from 'svelte';
	import { Node, type Editor } from '@tiptap/core';
	import type { Transaction } from '@tiptap/pm/state';
	import { Marked } from 'marked';
	import DOMPurify from 'dompurify';
	// @ts-expect-error The existing Turndown dependency does not ship declarations.
	import TurndownService from 'turndown';
	// @ts-expect-error The existing GFM plugin does not ship declarations.
	import { gfm } from '@joplin/turndown-plugin-gfm';
	import { toast } from 'svelte-sonner';
	import RichTextInput from '$lib/components/common/RichTextInput.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { downloadFileBlob, uploadNewFileToTerminal } from '$lib/apis/terminal';
	import MarkdownDocument, { resolveDocumentPath } from './MarkdownDocument.svelte';
	import KatexRenderer from '../Messages/Markdown/KatexRenderer.svelte';
	import markedKatexExtension from '$lib/utils/marked/katex-extension';

	export let value = '';
	export let path = '';
	export let baseUrl = '';
	export let apiKey = '';
	export let chatId: string | null = null;
	export let readOnly = false;
	export let onSave: (() => Promise<void>) | null = null;
	const i18n = getContext<any>('i18n');
	const context = getAllContexts();
	const math = markedKatexExtension();
	const sourceFromElement = (element: HTMLElement) => {
		try {
			return decodeURIComponent(element.getAttribute('data-markdown-source') ?? '');
		} catch {
			return element.textContent ?? '';
		}
	};
	const sourceHtml = (source: string, inline: boolean) => {
		const element = document.createElement(inline ? 'span' : 'div');
		// Encode source so XML-sensitive syntax such as Mermaid arrows survives sanitization.
		element.setAttribute('data-markdown-source', encodeURIComponent(source));
		element.textContent = source;
		return element.outerHTML;
	};
	const markdown = new Marked({
		breaks: false,
		extensions: [
			...math.extensions.map((extension) => ({
				...extension,
				level: extension.level as 'inline' | 'block',
				renderer: (token: { raw: string }) => sourceHtml(token.raw, extension.level === 'inline')
			})),
			{ name: 'markdownBlock', renderer: (token) => sourceHtml(token.raw, false) }
		],
		walkTokens(token) {
			if (
				(token.type === 'blockquote' &&
					/^\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]/.test(token.text)) ||
				(token.type === 'code' && token.lang?.trim() === 'mermaid')
			) {
				token.type = 'markdownBlock';
			}
		},
		renderer: {
			list: (body, ordered, start) =>
				body.includes('data-type="taskItem"')
					? `<ul data-type="taskList">${body}</ul>`
					: ordered
						? `<ol start="${start}">${body}</ol>`
						: `<ul>${body}</ul>`,
			listitem: (text, task, checked) =>
				task
					? `<li data-type="taskItem" data-checked="${checked}">${text.replace(/^<input[^>]*>\s*/, '')}</li>`
					: `<li>${text}</li>`
		}
	});
	const serializer = new TurndownService({ headingStyle: 'atx', codeBlockStyle: 'fenced' });
	serializer.use(gfm);
	serializer.addRule('markdownSource', {
		filter: (node: HTMLElement) => node.hasAttribute('data-markdown-source'),
		replacement: (_content: string, node: HTMLElement) => {
			const source = sourceFromElement(node);
			return node.nodeName === 'DIV' ? `\n\n${source}\n\n` : source;
		}
	});
	serializer.addRule('taskCheckbox', {
		filter: (node: HTMLElement) => node.nodeName === 'INPUT',
		replacement: () => ''
	});
	serializer.addRule('taskItem', {
		filter: (node: HTMLElement) =>
			node.nodeName === 'LI' && node.getAttribute('data-type') === 'taskItem',
		replacement: (content: string, node: HTMLElement) =>
			`- [${node.getAttribute('data-checked') === 'true' ? 'x' : ' '}] ${content.trim().replace(/\n(?=.)/g, '\n    ')}\n`
	});

	// Node views render Markdown without feeding their rendered HTML back into the serializer.
	const extensions = [true, false].map((inline) =>
		Node.create({
			name: inline ? 'markdownInline' : 'markdownBlock',
			group: inline ? 'inline' : 'block',
			inline,
			atom: true,
			addAttributes: () => ({
				source: {
					default: '',
					parseHTML: sourceFromElement,
					renderHTML: ({ source }) => ({ 'data-markdown-source': encodeURIComponent(source) })
				}
			}),
			parseHTML: () => [{ tag: `${inline ? 'span' : 'div'}[data-markdown-source]` }],
			renderHTML: ({ node, HTMLAttributes }) => [
				inline ? 'span' : 'div',
				HTMLAttributes,
				node.attrs.source
			],
			renderText: ({ node }) => node.attrs.source,
			addNodeView:
				() =>
				({ node, editor, getPos }) => {
					const dom = document.createElement(inline ? 'span' : 'div');
					dom.className = inline
						? 'inline-flex max-w-full items-center align-baseline'
						: 'relative my-2';
					const preview = document.createElement(inline ? 'span' : 'div');
					preview.setAttribute('role', 'button');
					preview.setAttribute('aria-label', $i18n.t('Edit'));
					preview.tabIndex = editor.isEditable ? 0 : -1;
					const input = document.createElement('textarea');
					input.className = inline
						? 'm-0 max-w-full resize-none p-0 font-mono text-sm leading-5 outline-none'
						: 'w-full p-0 font-mono text-sm outline-none';
					input.setAttribute('aria-label', $i18n.t('Source'));
					input.value = node.attrs.source;
					input.hidden = true;
					dom.append(preview, input);
					dom.contentEditable = 'false';
					let editing = false;
					let component: ReturnType<typeof mount> | undefined;
					const render = () => {
						if (component) void unmount(component);
						component = undefined;
						const token = inline ? math.extensions[0].tokenizer(node.attrs.source, []) : null;
						if (inline && !token) {
							preview.textContent = node.attrs.source;
						} else {
							preview.textContent = '';
							component = token
								? mount(KatexRenderer, {
										target: preview,
										context,
										props: { content: token.text, displayMode: token.displayMode }
									})
								: mount(MarkdownDocument, {
										target: preview,
										context,
										props: {
											content: node.attrs.source,
											id: `editor-${uuidv4()}`,
											path,
											baseUrl,
											apiKey,
											chatId
										}
									});
						}
					};
					input.oninput = () => {
						const pos = getPos();
						if (!editor.isEditable || typeof pos !== 'number') return;
						editor.view.dispatch(
							editor.state.tr.setNodeMarkup(pos, undefined, { source: input.value })
						);
					};
					const startEditing = () => {
						if (!editor.isEditable) return;
						editing = true;
						preview.hidden = true;
						input.hidden = false;
						input.rows = inline ? 1 : Math.max(3, input.value.split('\n').length);
						if (inline)
							input.style.width = `${Math.min(48, Math.max(12, input.value.length + 2))}ch`;
						input.focus();
					};
					preview.addEventListener(
						'click',
						(event) => {
							if ((event.target as Element).closest('a, button, input')) return;
							event.preventDefault();
							event.stopPropagation();
							startEditing();
						},
						true
					);
					preview.onfocus = startEditing;
					input.onblur = () => {
						editing = false;
						preview.hidden = false;
						input.hidden = true;
						render();
					};
					input.onkeydown = (event) => {
						if (inline && event.key === 'Enter' && !event.shiftKey) {
							event.preventDefault();
							input.blur();
							editor.commands.focus();
						}
					};
					render();
					return {
						dom,
						stopEvent: () => true,
						ignoreMutation: () => true,
						update(next) {
							if (next.type !== node.type) return false;
							if (next.attrs.source !== node.attrs.source) {
								node = next;
								if (input.value !== node.attrs.source) input.value = node.attrs.source;
								if (!editing) render();
							}
							return true;
						},
						destroy: () => {
							input.onblur = null;
							if (component) void unmount(component);
						}
					};
				}
		})
	);

	let editor: Editor | null = null;
	let html: string | null = null;
	let documentJSON: any = null;
	let lastValue: string | null = null;
	let original = '';
	let originalDocument = '';
	let header = '';
	let generation = 0;
	let revision = 0;
	const images = new Map<string, string>();
	let pendingImages: Promise<void>[] = [];
	export const flushUploads = () => Promise.all(pendingImages);
	const attachImages = (event: ClipboardEvent | DragEvent) => {
		const currentEditor = editor;
		if (readOnly || !currentEditor || !baseUrl || !path) return;
		const transfer = 'clipboardData' in event ? event.clipboardData : event.dataTransfer;
		const files = Array.from(transfer?.files ?? []).filter((file) =>
			file.type.startsWith('image/')
		);
		if (!files.length) return;
		event.preventDefault();
		event.stopPropagation();
		let position =
			'clientX' in event
				? (currentEditor.view.posAtCoords({ left: event.clientX, top: event.clientY })?.pos ??
					currentEditor.state.selection.from)
				: currentEditor.state.selection.from;
		const mapPosition = ({ transaction }: { transaction: Transaction }) => {
			position = transaction.mapping.map(position, 1);
		};
		// Keep the insertion point stable if the user types while the upload is running.
		currentEditor.on('transaction', mapPosition);
		const current = generation;
		const documentPath = path.replace(/\\/g, '/');
		const directory = documentPath.slice(0, documentPath.lastIndexOf('/')) || '/';
		const connection = { baseUrl, apiKey, chatId };
		const upload = (async () => {
			try {
				for (const file of files) {
					if (current !== generation || currentEditor.isDestroyed || readOnly) break;
					const result = await uploadNewFileToTerminal(
						connection.baseUrl,
						connection.apiKey,
						directory,
						file,
						connection.chatId ?? undefined
					);
					if (current !== generation || currentEditor.isDestroyed || readOnly) break;
					if (!result) throw new Error($i18n.t('Failed to upload file.'));
					const name = result.path.split('/').pop()!;
					const url = URL.createObjectURL(file);
					images.set(
						url,
						`./${encodeURIComponent(name).replace(/[()]/g, (char) => '%' + char.charCodeAt(0).toString(16))}`
					);
					currentEditor.commands.insertContentAt(position, {
						type: 'image',
						attrs: { src: url, alt: name }
					});
				}
			} catch (error) {
				toast.error(error instanceof Error ? error.message : String(error));
			} finally {
				currentEditor.off('transaction', mapPosition);
			}
		})();
		pendingImages = [...pendingImages, upload];
		void upload.finally(() => {
			pendingImages = pendingImages.filter((pending) => pending !== upload);
		});
	};
	const releaseImages = () => {
		for (const url of images.keys()) URL.revokeObjectURL(url);
		images.clear();
	};
	async function load(source: string) {
		const current = ++generation;
		lastValue = source;
		html = null;
		editor = null;
		releaseImages();
		original = source;
		// Keep document metadata out of the rich-text conversion.
		header = source.match(/^---\r?\n[\s\S]*?\r?\n(?:---|\.\.\.)\r?\n/)?.[0] ?? '';
		const dom = document.createElement('div');
		dom.innerHTML = DOMPurify.sanitize(markdown.parse(source.slice(header.length)) as string);
		await Promise.all(
			Array.from(dom.querySelectorAll('img')).map(async (image) => {
				const reference = image.getAttribute('src') ?? '';
				const file = resolveDocumentPath(path, reference);
				if (!file || !baseUrl) return;
				try {
					const result = await downloadFileBlob(baseUrl, apiKey, file, chatId ?? undefined);
					if (!result || current !== generation) return;
					const url = URL.createObjectURL(result.blob);
					images.set(url, reference);
					image.src = url;
				} catch {
					/* Keep the original reference if an image cannot be loaded. */
				}
			})
		);
		if (current !== generation) return;
		documentJSON = null;
		revision++;
		html = dom.innerHTML;
	}
	$: if (value !== lastValue) void load(value);
	async function attach(next: Editor | null) {
		if (!next || editor === next) return;
		editor = next;
		// Let Tiptap finish normalizing tables before recording the unchanged document.
		await tick();
		if (next.isDestroyed || editor !== next) return;
		next.commands.setTextSelection(1);
		originalDocument = JSON.stringify(next.getJSON());
		next.on('update', () => {
			if (readOnly) return;
			const dom = document.createElement('div');
			dom.innerHTML = next.getHTML();
			for (const table of dom.querySelectorAll('table')) {
				const row = table.rows[0];
				if (row && Array.from(row.cells).every((cell) => cell.tagName === 'TH')) {
					table.createTHead().append(row);
				}
			}
			for (const image of dom.querySelectorAll('img')) {
				const reference = images.get(image.getAttribute('src') ?? '');
				if (reference) image.setAttribute('src', reference);
			}
			value = lastValue =
				JSON.stringify(next.getJSON()) === originalDocument
					? original
					: header + serializer.turndown(dom.innerHTML) + '\n';
		});
	}
	export const getSelection = () => {
		if (!editor || editor.state.selection.empty) return undefined;
		const { from, to } = editor.state.selection;
		return { text: editor.state.doc.textBetween(from, to, '\n'), location: '' };
	};
	onDestroy(() => {
		generation++;
		releaseImages();
	});
</script>

<div
	class="file-markdown-editor min-h-full"
	role="presentation"
	on:paste|capture={attachImages}
	on:drop|capture={attachImages}
	on:dragover|capture={(event) => {
		if (
			!readOnly &&
			Array.from(event.dataTransfer?.items ?? []).some((item) => item.type.startsWith('image/'))
		) {
			event.preventDefault();
			event.stopPropagation();
		}
	}}
	on:keydown={(event) => {
		if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') {
			event.preventDefault();
			event.stopPropagation();
			if (!readOnly)
				void flushUploads()
					.then(() => onSave?.())
					.catch((error) => toast.error(String(error)));
		}
	}}
>
	{#if pendingImages.length}<div
			role="status"
			class="flex items-center gap-1.5 px-3 py-1 text-xs text-gray-500"
		>
			<Spinner className="size-3" />{$i18n.t('Uploading image...')}
		</div>{/if}
	{#if html !== null}
		{#key revision}
			<RichTextInput
				{extensions}
				messageInput={false}
				json={true}
				bind:value={documentJSON}
				{html}
				link={true}
				image={true}
				allowExternalImages={true}
				editable={!readOnly}
				className="document-markdown prose prose-sm dark:prose-invert min-w-0 max-w-none p-3 min-h-[12rem]"
				placeholder={$i18n.t('Markdown editor')}
				on:editor={(event) => attach(event.detail)}
			/>
		{/key}
	{:else}
		<Spinner className="size-4" />
	{/if}
</div>

<style>
	.file-markdown-editor :global(.tiptap .hljs-keyword) {
		color: #c678dd;
	}
	.file-markdown-editor :global(.tiptap .hljs-string) {
		color: #98c379;
	}
	.file-markdown-editor :global(.tiptap .hljs-number) {
		color: #d19a66;
	}
	.file-markdown-editor :global(.tiptap .hljs-comment) {
		color: #5c6370;
		font-style: italic;
	}
	.file-markdown-editor :global(.tiptap .hljs-function) {
		color: #61afef;
	}
	.file-markdown-editor :global(.tiptap .hljs-title) {
		color: #61afef;
	}
	.file-markdown-editor :global(.tiptap .hljs-built_in) {
		color: #e5c07b;
	}
	.file-markdown-editor :global(.tiptap .hljs-attr) {
		color: #d19a66;
	}
	.file-markdown-editor :global(.tiptap .hljs-tag) {
		color: #e06c75;
	}
	.file-markdown-editor :global(.tiptap .hljs-name) {
		color: #e06c75;
	}
	.file-markdown-editor :global(.tiptap .hljs-selector-class) {
		color: #d19a66;
	}
	.file-markdown-editor :global(.tiptap .hljs-variable) {
		color: #e06c75;
	}
	.file-markdown-editor :global(.tiptap .hljs-type) {
		color: #e5c07b;
	}
</style>
