<script>
	import { onDestroy, onMount, tick } from 'svelte';

	import Markdown from './Markdown.svelte';
	import {
		artifactCode,
		chatId,
		mobile,
		settings,
		showArtifacts,
		showControls,
		showEmbeds,
		showOverview
	} from '$lib/stores';
	import FloatingButtons from '../ContentRenderer/FloatingButtons.svelte';
	import { createMessagesList } from '$lib/utils';

	export let id;
	export let content;

	export let history;
	export let messageId;

	export let selectedModels = [];

	export let done = true;
	export let model = null;
	export let sources = null;

	export let save = false;
	export let preview = false;
	export let floatingButtons = true;

	export let editCodeBlock = true;
	export let topPadding = false;

	export let onSave = () => {};
	export let onSourceClick = () => {};
	export let onTaskClick = () => {};
	export let onAddMessages = () => {};
	export let onPinSelection = () => {};
	export let enableTextPinning = false;

	let contentContainerElement;
	let floatingButtonsElement;

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
				if (!contentContainerElement.contains(range.commonAncestorContainer)) {
					closeFloatingButtons();
					return;
				}

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

	const pinSelectedText = () => {
		const selection = window.getSelection();
		if (!selection || selection.rangeCount === 0) return;

		const text = selection.toString().trim();
		if (!text) return;

		const range = selection.getRangeAt(0);
		if (!contentContainerElement?.contains(range.commonAncestorContainer)) return;

		const snippetId =
			(typeof crypto !== 'undefined' && crypto.randomUUID?.()) ||
			`${messageId}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

		let hasAnchor = false;
		try {
			const marker = document.createElement('span');
			marker.dataset.pinSnippetId = snippetId;
			marker.className = 'rounded px-0.5 bg-blue-500/25';

			const selectedContents = range.extractContents();
			marker.appendChild(selectedContents);
			range.insertNode(marker);
			hasAnchor = true;
		} catch (error) {
			console.warn('Could not create pinned text anchor', error);
		}

		selection.removeAllRanges();
		closeFloatingButtons();

		onPinSelection({
			id: snippetId,
			messageId,
			text,
			hasAnchor
		});
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
	<Markdown
		{id}
		{content}
		{model}
		{save}
		{preview}
		{done}
		{editCodeBlock}
		{topPadding}
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
		onUpdate={async (token) => {
			const { lang, text: code } = token;

			if (
				($settings?.detectArtifacts ?? true) &&
				(['html', 'svg'].includes(lang) || (lang === 'xml' && code.includes('svg'))) &&
				!$mobile &&
				$chatId
			) {
				await tick();
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
</div>

{#if floatingButtons}
	<FloatingButtons
		bind:this={floatingButtonsElement}
		{id}
		{messageId}
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
		enablePinAction={enableTextPinning}
		onPin={() => {
			pinSelectedText();
		}}
	/>
{/if}
