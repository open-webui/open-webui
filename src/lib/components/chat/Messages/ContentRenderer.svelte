<script>
	import { onDestroy, onMount, tick, getContext } from 'svelte';
	const i18n = getContext('i18n');

	import Markdown from './Markdown.svelte';
	import {
		artifactCode,
		mobile,
		settings,
		showArtifacts,
		showControls,
		showEmbeds,
		showOverview
	} from '$lib/stores';
	import FloatingButtons from '../ContentRenderer/FloatingButtons.svelte';
	import { blocksToDisplayMarkdown, createMessagesList } from '$lib/utils';

	export let id;
	export let content;
	// Optional structured content_blocks. When present we render block-by-block
	// with cached per-block projections — older blocks (completed reasoning,
	// completed tool_calls, prior text blocks) reuse the same `<Markdown>`
	// instance with an unchanged content string, so Svelte's prop-equality
	// check short-circuits the marked.parse + {@html} wipe for them. Only the
	// last block (the one actively streaming) re-parses per chunk. Net cost
	// per stream chunk: O(last_block_size) instead of O(total_message_size).
	//
	// When unset (or empty), we fall back to a single `<Markdown content>`
	// render — the legacy path, used for messages that pre-date the
	// content_blocks migration and for non-message renderings.
	export let content_blocks = null;

	export let history;
	export let messageId;
	export let chatId = '';
	export let dataVizOverrides = {};

	export let selectedModels = [];

	export let done = true;
	export let model = null;
	export let sources = null;

	export let save = false;
	export let preview = false;
	export let floatingButtons = true;

	export let editCodeBlock = true;
	export let topPadding = false;

	export let onSave = (e) => {};
	export let onSourceClick = (e) => {};
	export let onTaskClick = (e) => {};
	export let onAddMessages = (e) => {};

	let contentContainerElement;
	let floatingButtonsElement;

	// Cached per-block markdown projections. The invariant we exploit: the
	// backend never mutates older blocks — once a new block is appended,
	// the previous-last block is frozen. So we only ever recompute the
	// projection for the *current* last block. Earlier projections are
	// referentially identical strings across reactive updates, which means
	// the nested `<Markdown>` component sees prop equality and skips its
	// internal marked.parse + {@html} wipe entirely.
	/** @type {string[]} */
	let blockProjections = [];
	$: {
		/** @type {any[]} */
		const blocks = Array.isArray(content_blocks) ? content_blocks : [];
		if (blocks.length === 0) {
			if (blockProjections.length !== 0) blockProjections = [];
		} else {
			/** @type {string[]} */
			const next = blockProjections.slice(0, blocks.length - 1);
			// Backfill projections for any newly-finalized blocks (we may have
			// jumped multiple blocks in one update — e.g. tool_calls round
			// completed and a fresh text block was appended in the same tick).
			for (let i = next.length; i < blocks.length - 1; i++) {
				next.push(blocksToDisplayMarkdown([blocks[i]]));
			}
			// The last block is always (re)projected; it's the only one that
			// can be growing during streaming.
			next[blocks.length - 1] = blocksToDisplayMarkdown([blocks[blocks.length - 1]]);
			blockProjections = next;
		}
	}

	// Single render path: per-block projections when `content_blocks` is
	// provided, otherwise a one-element array carrying the legacy `content`
	// string. Keeps the `<Markdown>` invocation in exactly one place.
	//
	// `structuredMode` stays true for the duration of a structured render so
	// each block's id is `${id}-b${i}` from the start — preventing a re-mount
	// of block-0 when a second block gets appended (which would otherwise
	// flip the id from `${id}` to `${id}-b0`, triggering Markdown's `{#key
	// id}` to tear down and rebuild the rendered DOM).
	$: structuredMode = blockProjections.length > 0;
	$: renderedSegments = structuredMode ? blockProjections : [content ?? ''];

	const updateButtonPosition = (event) => {
		const buttonsContainerElement = document.getElementById(`floating-buttons-${id}`);
		if (
			!contentContainerElement?.contains(event.target) &&
			!buttonsContainerElement?.contains(event.target)
		) {
			closeFloatingButtons();
			return;
		}

		setTimeout(async () => {
			await tick();

			if (!contentContainerElement?.contains(event.target)) return;

			let selection = window.getSelection();

			if (selection.toString().trim().length > 0) {
				const range = selection.getRangeAt(0);
				const rect = range.getBoundingClientRect();

				const parentRect = contentContainerElement.getBoundingClientRect();

				// Adjust based on parent rect
				const top = rect.bottom - parentRect.top;
				const left = rect.left - parentRect.left;

				if (buttonsContainerElement) {
					buttonsContainerElement.style.display = 'block';

					// Calculate space available on the right
					const spaceOnRight = parentRect.width - left;
					let halfScreenWidth = $mobile ? window.innerWidth / 2 : window.innerWidth / 3;

					if (spaceOnRight < halfScreenWidth) {
						const right = parentRect.right - rect.right;
						buttonsContainerElement.style.right = `${right}px`;
						buttonsContainerElement.style.left = 'auto'; // Reset left
					} else {
						// Enough space, position using 'left'
						buttonsContainerElement.style.left = `${left}px`;
						buttonsContainerElement.style.right = 'auto'; // Reset right
					}
					buttonsContainerElement.style.top = `${top + 5}px`; // +5 to add some spacing
				}
			} else {
				closeFloatingButtons();
			}
		}, 0);
	};

	const closeFloatingButtons = () => {
		const buttonsContainerElement = document.getElementById(`floating-buttons-${id}`);
		if (buttonsContainerElement) {
			buttonsContainerElement.style.display = 'none';
		}

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

	onMount(() => {
		if (floatingButtons) {
			contentContainerElement?.addEventListener('mouseup', updateButtonPosition);
			document.addEventListener('mouseup', updateButtonPosition);
			document.addEventListener('keydown', keydownHandler);
		}
	});

	onDestroy(() => {
		if (floatingButtons) {
			contentContainerElement?.removeEventListener('mouseup', updateButtonPosition);
			document.removeEventListener('mouseup', updateButtonPosition);
			document.removeEventListener('keydown', keydownHandler);
		}
	});
</script>

<div bind:this={contentContainerElement}>
	{#each renderedSegments as segment, i (i)}
		<Markdown
			id={structuredMode ? `${id}-b${i}` : id}
			content={segment}
			{model}
			{save}
			{preview}
			{done}
			{editCodeBlock}
			topPadding={i === 0 ? topPadding : false}
			{chatId}
			{messageId}
			{dataVizOverrides}
			sourceIds={(sources ?? []).reduce((acc, source) => {
				let ids = [];
				source.document.forEach((document, index) => {
					if (model?.info?.meta?.capabilities?.citations == false) {
						ids.push('N/A');
						return ids;
					}

					const metadata = source.metadata?.[index];
					const id = metadata?.source ?? 'N/A';

					if (metadata?.name) {
						ids.push(metadata.name);
						return ids;
					}

					if (id.startsWith('http://') || id.startsWith('https://')) {
						ids.push(id);
					} else {
						ids.push(source?.source?.name ?? id);
					}

					return ids;
				});

				acc = [...acc, ...ids];

				// remove duplicates
				return acc.filter((item, index) => acc.indexOf(item) === index);
			}, [])}
			{onSourceClick}
			{onTaskClick}
			{onSave}
			onUpdate={(token) => {
				const { lang, text: code } = token;

				if (
					($settings?.detectArtifacts ?? true) &&
					(['html', 'svg'].includes(lang) || (lang === 'xml' && code.includes('svg'))) &&
					!$mobile &&
					chatId
				) {
					showArtifacts.set(true);
					showControls.set(true);
				}
			}}
			onPreview={async (value) => {
				console.log('Preview', value);
				await artifactCode.set(value);
				await showControls.set(true);
				await showArtifacts.set(true);
				await showOverview.set(false);
				await showEmbeds.set(false);
			}}
		/>
	{/each}
</div>

{#if floatingButtons && model}
	<FloatingButtons
		bind:this={floatingButtonsElement}
		{id}
		{messageId}
		{chatId}
		actions={$settings?.floatingActionButtons ?? []}
		model={(selectedModels ?? []).includes(model?.id)
			? model?.id
			: (selectedModels ?? []).length > 0
				? selectedModels.at(0)
				: model?.id}
		messages={createMessagesList(history, messageId)}
		onAdd={({ modelId, parentId, messages }) => {
			console.log(modelId, parentId, messages);
			onAddMessages({ modelId, parentId, messages });
			closeFloatingButtons();
		}}
	/>
{/if}
