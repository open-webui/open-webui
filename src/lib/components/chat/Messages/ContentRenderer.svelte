<script>
	import {
		commentSurface,
		contentHash,
		commentSelectionDraft,
		selectedComment
	} from '$lib/components/comments/anchors';
	import {
		config,
		user,
		artifactCode,
		chatId as currentChatId,
		mobile,
		settings,
		showArtifacts,
		showTabs,
		showEmbeds
	} from '$lib/stores';
	import { onDestroy, onMount, tick, getContext } from 'svelte';
	const i18n = getContext('i18n');

	import Markdown from './Markdown.svelte';
	import StructuredOutputRenderer from './StructuredOutputRenderer.svelte';
	import FloatingButtons from '../ContentRenderer/FloatingButtons.svelte';
	import { createMessagesList, replaceOutsideCode } from '$lib/utils';

	/**
	 * Extracts all top-level <details>...</details> blocks from content,
	 * handling nested <details> via depth tracking.
	 * Returns { detailsContent, plainContent }.
	 */
	const extractDetailsBlocks = (text) => {
		const blocks = [];
		let remaining = text;
		let result = '';
		const openTag = '<details';
		const closeTag = '</details>';

		while (true) {
			const start = remaining.indexOf(openTag);
			if (start === -1) {
				result += remaining;
				break;
			}

			result += remaining.slice(0, start);

			// Find matching closing tag with depth tracking
			let depth = 1;
			let idx = start + openTag.length;
			while (depth > 0 && idx < remaining.length) {
				if (remaining.startsWith(openTag, idx)) {
					depth++;
				} else if (remaining.startsWith(closeTag, idx)) {
					depth--;
				}
				if (depth > 0) idx++;
			}

			if (depth === 0) {
				const end = idx + closeTag.length;
				blocks.push(remaining.slice(start, end));
				remaining = remaining.slice(end);
			} else {
				// Unmatched opening tag, treat as plain text
				result += remaining.slice(start);
				remaining = '';
				break;
			}
		}

		return {
			detailsContent: blocks.join('\n'),
			plainContent: result.trim()
		};
	};

	export let id;
	export let chatId = '';
	export let content;
	/** @type {import('./structuredOutput').OutputItem[]} */
	export let output = [];

	export let history;
	export let messageId;

	export let selectedModels = [];

	export let done = true;
	export let model = null;
	export let sources = null;

	export let save = false;
	export let preview = false;
	export let compactPreview = false;
	export let floatingButtons = true;

	export let editCodeBlock = true;
	export let topPadding = false;
	export let allowEmbeds = false;

	export let onSave = (e) => {};
	export let onSourceClick = (e) => {};
	export let onTaskClick = (e) => {};
	export let onToolCallResolved = (e) => {};
	export let onSetInputText = (text) => {};

	/** @type {HTMLDivElement | undefined} */
	let contentContainerElement;
	/** @type {{ closeHandler: () => void } | undefined} */
	let floatingButtonsElement;
	/** @type {Range | null} */
	let floatingButtonsRange = null;
	let selectedText = '';
	let usingFloatingButtons = false;

	let sourceIds = [];
	$: getSourceIds(sources);

	const getSourceIds = (sources) => {
		const result = [];
		const seenIds = new Set();
		for (const source of sources ?? []) {
			for (let index = 0; index < (source.document ?? []).length; index++) {
				if (model?.info?.meta?.capabilities?.citations == false) {
					result.push('N/A');
					continue;
				}
				const metadata = source.metadata?.[index];
				const id = metadata?.source ?? source?.source?.id ?? 'N/A';
				if (seenIds.has(id)) {
					continue;
				}
				seenIds.add(id);
				if (metadata?.name) {
					result.push(metadata.name);
				} else if (id.startsWith('http://') || id.startsWith('https://')) {
					result.push(id);
				} else {
					result.push(source?.source?.name ?? id);
				}
			}
		}
		sourceIds = result;
	};

	/** @param {string} messageContent */
	const formatMessageContent = (messageContent) =>
		model?.info?.meta?.capabilities?.citations == false
			? replaceOutsideCode(messageContent, (segment) =>
					segment.replace(/\s*(\[(?:\d+(?:#[^,\]\s]+)?(?:,\s*\d+(?:#[^,\]\s]+)?)*)\])+/g, '')
				)
			: messageContent;

	let autoOpenedArtifactIds = new Set();
	/** @type {ReturnType<typeof selectedComment>} */
	let commentSelection = null;

	const hasClosingCodeFence = (raw = '') => /(?:^|\n)```[ \t]*$/.test(raw.trimEnd());

	const markdownUpdateHandler = /** @type {any} */ (
		async (
			/** @type {{ lang?: string; raw?: string; text?: string }} */ token,
			codeBlockId = ''
		) => {
			const { lang = '', raw = '', text: code = '' } = token;
			const normalizedLang = lang.toLowerCase();
			const isArtifact =
				['html', 'svg'].includes(normalizedLang) ||
				(normalizedLang === 'xml' && code.toLowerCase().includes('<svg'));
			const artifactId = codeBlockId || `${normalizedLang}:${raw}`;

			if (
				($settings?.detectArtifacts ?? true) &&
				!compactPreview &&
				isArtifact &&
				hasClosingCodeFence(raw) &&
				!autoOpenedArtifactIds.has(artifactId) &&
				!$mobile &&
				$currentChatId
			) {
				autoOpenedArtifactIds.add(artifactId);
				await tick();
				showArtifacts.set(true);
				showTabs.set(true);
			}
		}
	);

	const previewHandler = /** @type {any} */ (
		async (/** @type {string} */ value) => {
			console.log('Preview', value);
			await artifactCode.set(/** @type {any} */ (value));
			await showTabs.set(true);
			await showArtifacts.set(true);
			await showEmbeds.set(false);
		}
	);

	const updateSelection = () => {
		if (usingFloatingButtons) return;
		const selection = window.getSelection();
		const range = selection?.rangeCount ? selection.getRangeAt(0) : null;
		if (
			!selection ||
			!range ||
			!selection.toString().trim() ||
			!contentContainerElement?.contains(range.startContainer) ||
			!contentContainerElement.contains(range.endContainer)
		) {
			closeFloatingButtons();
			return;
		}
		floatingButtonsElement?.closeHandler();
		selectedText = selection.toString();
		floatingButtonsRange = range.cloneRange();
		commentSelection = $config?.features?.enable_comments && $user ? selectedComment() : null;
	};

	/** @param {Event} event */
	const toolbarInteractionHandler = (event) => {
		if (!(event.target instanceof Node)) return;
		const toolbar = document.getElementById(`floating-buttons-${id}`);
		// Keep the snapshot while a touch focuses an action or its question input.
		usingFloatingButtons = !!toolbar?.contains(event.target);
		if (!usingFloatingButtons && !contentContainerElement?.contains(event.target)) {
			closeFloatingButtons();
		}
	};

	const closeFloatingButtons = () => {
		commentSelection = null;
		floatingButtonsRange = null;
		selectedText = '';

		if (floatingButtonsElement) {
			// check if closeHandler is defined

			if (typeof floatingButtonsElement?.closeHandler === 'function') {
				// call the closeHandler function
				floatingButtonsElement?.closeHandler();
			}
		}
	};

	const keydownHandler = (e) => {
		if (e.key === 'Escape') {
			closeFloatingButtons();
		}
	};

	// Reactive listener attachment: re-attaches when floatingButtons
	// transitions from false → true (e.g. when message.done flips).
	let listenersAttached = false;

	function attachListeners() {
		if (!listenersAttached && contentContainerElement) {
			document.addEventListener('selectionchange', updateSelection);
			document.addEventListener('pointerdown', toolbarInteractionHandler, true);
			document.addEventListener('focusin', toolbarInteractionHandler, true);
			document.addEventListener('keydown', keydownHandler);
			listenersAttached = true;
		}
	}

	function detachListeners() {
		if (listenersAttached) {
			document.removeEventListener('selectionchange', updateSelection);
			document.removeEventListener('pointerdown', toolbarInteractionHandler, true);
			document.removeEventListener('focusin', toolbarInteractionHandler, true);
			document.removeEventListener('keydown', keydownHandler);
			listenersAttached = false;
		}
	}

	$: if (floatingButtons && contentContainerElement) {
		attachListeners();
	} else {
		detachListeners();
	}

	onDestroy(() => {
		detachListeners();
	});
</script>

<div bind:this={contentContainerElement}>
	{#if output?.length}
		<StructuredOutputRenderer
			commentToolbarId={floatingButtons ? `floating-buttons-${id}` : undefined}
			{id}
			{chatId}
			{messageId}
			{output}
			{model}
			{save}
			{preview}
			{compactPreview}
			{done}
			{allowEmbeds}
			{editCodeBlock}
			{topPadding}
			{sourceIds}
			renderMarkdown={$settings?.renderMarkdownInAssistantMessages ?? true}
			{formatMessageContent}
			{onSourceClick}
			{onTaskClick}
			{onToolCallResolved}
			{onSave}
			onUpdate={markdownUpdateHandler}
			onPreview={previewHandler}
		/>
	{:else if $settings?.renderMarkdownInAssistantMessages ?? true}
		<div
			class="markdown-prose"
			use:commentSurface={{
				resource_type: 'chat',
				resource_id: chatId,
				target_type: 'chat_message',
				target_id: messageId,
				surface_id: 'content',
				content_hash: contentHash(content ?? ''),
				enabled: done && !compactPreview && !!chatId,
				toolbar_id: floatingButtons ? `floating-buttons-${id}` : undefined
			}}
		>
			<Markdown
				{id}
				{chatId}
				{messageId}
				content={formatMessageContent(content)}
				{model}
				{save}
				{preview}
				{compactPreview}
				{done}
				{allowEmbeds}
				{editCodeBlock}
				{topPadding}
				{sourceIds}
				{onSourceClick}
				{onTaskClick}
				{onToolCallResolved}
				{onSave}
				onUpdate={markdownUpdateHandler}
				onPreview={previewHandler}
			/>
		</div>
	{:else}
		{@const extracted = extractDetailsBlocks(content)}

		{#if extracted.detailsContent}
			<!-- Render structural blocks (tool calls, reasoning, etc.) through Markdown -->
			<div class="markdown-prose">
				<Markdown
					{id}
					{chatId}
					{messageId}
					content={extracted.detailsContent}
					{save}
					{preview}
					{compactPreview}
					{done}
					{allowEmbeds}
					{onToolCallResolved}
				/>
			</div>
		{/if}
		{#if extracted.plainContent}
			<div
				class="whitespace-pre-wrap text-[0.9375rem]"
				use:commentSurface={{
					resource_type: 'chat',
					resource_id: chatId,
					target_type: 'chat_message',
					target_id: messageId,
					surface_id: 'content',
					content_hash: contentHash(content ?? ''),
					enabled: done && !compactPreview && !!chatId,
					toolbar_id: floatingButtons ? `floating-buttons-${id}` : undefined
				}}
			>
				{extracted.plainContent}
			</div>
		{/if}
	{/if}
</div>

{#if floatingButtons}
	<FloatingButtons
		bind:this={floatingButtonsElement}
		range={floatingButtonsRange}
		{selectedText}
		{id}
		actions={$settings?.floatingActionButtons ?? []}
		onComment={commentSelection
			? () => {
					if (!commentSelection) return;
					commentSelectionDraft.set(commentSelection);
					window.getSelection()?.removeAllRanges();
					closeFloatingButtons();
				}
			: null}
		onSetInputText={(text) => {
			onSetInputText(text);
			closeFloatingButtons();
		}}
	/>
{/if}
