<script>
	import { onDestroy, onMount, tick, getContext } from 'svelte';
	const i18n = getContext('i18n');

	import Markdown from './Markdown.svelte';
import {
    artifactCode,
    chatId as chatIdStore,
    mobile,
    settings,
    showArtifacts,
    showControls,
    showEmbeds,
    showOverview,
    selectionModeEnabled,
    savedSelections
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

	export let onSave = (e) => {};
	export let onSourceClick = (e) => {};
	export let onTaskClick = (e) => {};
	export let onAddMessages = (e) => {};

	let contentContainerElement;
	let floatingButtonsElement;

// Chat identifier to record selection against
export let chatId = '';

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

let listenersAttached = false;

const attachListeners = () => {
    if (listenersAttached) return;
    contentContainerElement?.addEventListener('mouseup', updateButtonPosition);
    document.addEventListener('mouseup', updateButtonPosition);
    document.addEventListener('keydown', keydownHandler);
    listenersAttached = true;
};

const detachListeners = () => {
    if (!listenersAttached) return;
    contentContainerElement?.removeEventListener('mouseup', updateButtonPosition);
    document.removeEventListener('mouseup', updateButtonPosition);
    document.removeEventListener('keydown', keydownHandler);
    listenersAttached = false;
};

onMount(() => {
    if (floatingButtons || $selectionModeEnabled) {
        attachListeners();
    }
});

onDestroy(() => {
    detachListeners();
});

// React to selection mode changes to attach/detach listeners dynamically
$: {
    if ($selectionModeEnabled) {
        attachListeners();
    } else if (!floatingButtons) {
        // Only detach when floatingButtons is also off
        detachListeners();
    }
}

const saveCurrentSelection = () => {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) return;

    const range = selection.getRangeAt(0);
    if (!contentContainerElement?.contains(range.commonAncestorContainer)) return;

    const text = selection.toString();
    if (!text.trim()) return;

    // Highlight selected text
    const mark = document.createElement('mark');
    mark.className = 'selection-highlight';
    mark.textContent = text;

    range.deleteContents();
    range.insertNode(mark);

    selection.removeAllRanges();

    // Record selection
    savedSelections.update((arr) => [
        ...arr,
        { chatId: chatId || $chatIdStore, messageId, role: 'assistant', text }
    ]);

    closeFloatingButtons();
};
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
		onUpdate={(token) => {
			const { lang, text: code } = token;

			if (
                ($settings?.detectArtifacts ?? true) &&
				(['html', 'svg'].includes(lang) || (lang === 'xml' && code.includes('svg'))) &&
                !$mobile &&
                $chatIdStore
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
</div>

{#if $selectionModeEnabled}
    <div
        id={`floating-buttons-${id}`}
        class="absolute rounded-lg mt-1 text-xs z-9999"
        style="display: none"
    >
        <div class="flex flex-row gap-0.5 shrink-0 p-1 bg-white dark:bg-gray-850 dark:text-gray-100 text-medium rounded-lg shadow-xl">
            <button
                class="px-2 py-0.5 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-sm min-w-fit"
                on:click={saveCurrentSelection}
            >
                {$i18n.t('Save')}
            </button>
        </div>
    </div>
{:else if floatingButtons && model}
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
    />
{/if}
