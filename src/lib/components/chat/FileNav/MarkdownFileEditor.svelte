<script lang="ts">
	import { getContext, onDestroy } from 'svelte';
	import type { Editor } from '@tiptap/core';
	import { Marked } from 'marked';
	import DOMPurify from 'dompurify';
	import TurndownService from 'turndown';
	import { gfm } from '@joplin/turndown-plugin-gfm';
	import { toast } from 'svelte-sonner';
	import RichTextInput from '$lib/components/common/RichTextInput.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { downloadFileBlob } from '$lib/apis/terminal';
	import { resolveDocumentPath } from './MarkdownDocument.svelte';

	export let value = '';
	export let path = '';
	export let baseUrl = '';
	export let apiKey = '';
	export let chatId: string | null = null;
	export let readOnly = false;
	export let onSave: (() => Promise<void>) | null = null;
	const i18n = getContext<any>('i18n');
	const markdown = new Marked({
		breaks: false,
		renderer: {
			list: (body, ordered, start) =>
				body.includes('data-type="taskItem"')
					? `<ul data-type="taskList">${body}</ul>`
					: ordered ? `<ol start="${start}">${body}</ol>` : `<ul>${body}</ul>`,
			listitem: (text, task, checked) => task
				? `<li data-type="taskItem" data-checked="${checked}">${text.replace(/^<input[^>]*>\s*/, '')}</li>`
				: `<li>${text}</li>`
		}
	});
	const serializer = new TurndownService({ headingStyle: 'atx', codeBlockStyle: 'fenced' });
	serializer.use(gfm);
	serializer.addRule('taskCheckbox', { filter: (node) => node.nodeName === 'INPUT', replacement: () => '' });
	serializer.addRule('taskItem', {
		filter: (node) => node.nodeName === 'LI' && node.getAttribute('data-type') === 'taskItem',
		replacement: (content, node) => `- [${node.getAttribute('data-checked') === 'true' ? 'x' : ' '}] ${content.trim().replace(/\n(?=.)/g, '\n    ')}\n`
	});

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
		await Promise.all(Array.from(dom.querySelectorAll('img')).map(async (image) => {
			const reference = image.getAttribute('src') ?? '';
			const file = resolveDocumentPath(path, reference);
			if (!file || !baseUrl) return;
			try {
				const result = await downloadFileBlob(baseUrl, apiKey, file, chatId ?? undefined);
				if (!result || current !== generation) return;
				const url = URL.createObjectURL(result.blob);
				images.set(url, reference);
				image.src = url;
			} catch { /* Keep the original reference if an image cannot be loaded. */ }
		}));
		if (current !== generation) return;
		documentJSON = null;
		revision++;
		html = dom.innerHTML;
	}
	$: if (value !== lastValue) void load(value);
	function attach(next: Editor | null) {
		if (!next || editor === next) return;
		editor = next;
		originalDocument = JSON.stringify(next.getJSON());
		next.view.dom.setAttribute('aria-label', i18n ? $i18n.t('Markdown editor') : 'Markdown editor');
		next.on('update', () => {
			if (readOnly) return;
			const dom = document.createElement('div');
			dom.innerHTML = next.getHTML();
			for (const image of dom.querySelectorAll('img')) {
				const reference = images.get(image.getAttribute('src') ?? '');
				if (reference) image.setAttribute('src', reference);
			}
			value = lastValue = JSON.stringify(next.getJSON()) === originalDocument
				? original
				: header + serializer.turndown(dom.innerHTML) + '\n';
		});
	}
	export const getSelection = () => {
		if (!editor || editor.state.selection.empty) return undefined;
		const { from, to } = editor.state.selection;
		return { text: editor.state.doc.textBetween(from, to, '\n'), location: '' };
	};
	onDestroy(() => { generation++; releaseImages(); });
</script>

<div
	class="min-h-full px-4 py-3"
	role="presentation"
	on:keydown={(event) => {
		if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') {
			event.preventDefault();
			event.stopPropagation();
			if (!readOnly) void onSave?.().catch((error) => toast.error(String(error)));
		}
	}}
>
	{#if html !== null}
		{#key revision}
			<RichTextInput
				json={true}
				bind:value={documentJSON}
				{html}
				link={true}
				image={true}
				editable={!readOnly}
				className="input-prose-sm min-h-[12rem]"
				placeholder={$i18n.t('Write something...')}
				on:editor={(event) => attach(event.detail)}
			/>
		{/key}
	{:else}
		<Spinner className="size-4" />
	{/if}
</div>
