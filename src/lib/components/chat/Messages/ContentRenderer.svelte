<script>
	import { onDestroy, onMount, tick, getContext } from 'svelte';
	import { get } from 'svelte/store';
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
    savedSelections,
    latestAssistantMessageId
	} from '$lib/stores';
import { selectionSyncService } from '$lib/services/selectionSync';
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

// TEXT SELECTION: Save selected text from assistant message
const saveCurrentSelection = async () => {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) return;

    const range = selection.getRangeAt(0);
    if (!contentContainerElement?.contains(range.commonAncestorContainer)) return;

    const text = selection.toString();
    if (!text.trim()) return;

    // Highlight selected text with <mark> element
    const mark = document.createElement('mark');
    mark.className = 'selection-highlight';
    mark.textContent = text;
    range.deleteContents();
    range.insertNode(mark);
    selection.removeAllRanges();

    // Only allow selection on the most recent assistant message
    if ($latestAssistantMessageId && $latestAssistantMessageId !== messageId) {
        closeFloatingButtons();
        return;
    }

    // Save to localStorage store
    savedSelections.update((arr) => {
        const newArr = [
            ...arr,
            { chatId: chatId || $chatIdStore, messageId, role: 'assistant', text }
        ];
        return newArr;
    });

    // Also save to backend database via sync service
    const currentChatId = chatId || $chatIdStore;
    if (!currentChatId) return;
    
    try {
        await selectionSyncService.saveSelection({
            chat_id: currentChatId,
            message_id: messageId,
            role: 'assistant',
            selected_text: text,
            context: undefined,
            meta: {
                timestamp: Date.now(),
                source: 'user_selection'
            }
        });
    } catch (error) {
        // Selection is still saved in localStorage, so user doesn't lose data
    }

    closeFloatingButtons();
};

// Re-apply saved selections on mount and when data changes
function wrapFirstMatch(root, target) {
    console.log('wrapFirstMatch called with:', { root, target });
    if (!root || !target || target.length === 0) {
        console.log('wrapFirstMatch: invalid parameters');
        return false;
    }
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    let node;
    let nodeCount = 0;
    while ((node = walker.nextNode())) {
        nodeCount++;
        // Skip inside existing marks
        if (node.parentElement && node.parentElement.closest('mark.selection-highlight')) {
            console.log('Skipping node inside existing mark');
            continue;
        }
        const idx = node.data.indexOf(target);
        if (idx !== -1) {
            console.log('Found target text in node:', { nodeData: node.data, idx, target });
            const mark = document.createElement('mark');
            mark.className = 'selection-highlight';
            mark.textContent = target;

            const before = node.splitText(idx);
            before.splitText(target.length);
            before.parentNode.replaceChild(mark, before);
            console.log('Successfully wrapped text, mark element:', mark);
            console.log('Mark classes:', mark.className);
            console.log('Mark computed styles:', window.getComputedStyle(mark));
            return true;
        }
    }
    console.log('wrapFirstMatch: target not found after checking', nodeCount, 'text nodes');
    return false;
}

// TEXT SELECTION: Re-apply saved selections by highlighting text with <mark> elements
function applySavedSelections() {
    const root = contentContainerElement;
    if (!root) return;
    const chat = chatId || $chatIdStore;
    const items = ($savedSelections || []).filter(
        (s) => s.chatId === chat && s.messageId === messageId && s.role === 'assistant'
    );
    // Avoid double-highlighting: only add marks for texts not yet wrapped
    for (const sel of items) {
        const existingMarks = Array.from(root.querySelectorAll('mark.selection-highlight'));
        const already = existingMarks.some((m) => m.textContent === sel.text);
        if (!already) {
            wrapFirstMatch(root, sel.text);
        } else {
            // Text already wrapped - mark exists and is visible
            const mark = existingMarks.find(m => m.textContent === sel.text);
            if (mark) {
                // Mark exists and is visible
            }
        }
    }
}

onMount(async () => {
    await tick();
    // Add a small delay to ensure DOM is fully rendered
    setTimeout(() => {
        applySavedSelections();
    }, 100);
});

$: if ($savedSelections && messageId && contentContainerElement) {
    // Add a small delay to ensure DOM is fully rendered
    setTimeout(() => {
        applySavedSelections();
    }, 100);
}
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
    
    <!-- Done button below response when selection mode is active -->
    {#if $selectionModeEnabled && done && $latestAssistantMessageId === messageId}
        <div class="mt-4 flex justify-between items-center">
            <div class="text-sm text-gray-600 dark:text-gray-400">
                {$i18n.t('Select problematic text in the chat and save your selection.')}
            </div>
            <button
                class="bg-white border border-gray-100 dark:border-none dark:bg-white/20 hover:bg-gray-100 text-gray-800 dark:text-white transition rounded-full p-1.5 self-center pointer-events-auto"
                type="button"
                on:click={() => {
                    console.log('Done button clicked!');
                    // Import selectionModeEnabled and other stores
                    import('$lib/stores').then(({ selectionModeEnabled, savedSelections }) => {
                        const selections = get(savedSelections);
                        console.log('Current selections:', selections);
                        selectionModeEnabled.set(false);
                        // Switch back to message input
                        window.dispatchEvent(new CustomEvent('selection-done', {
                            detail: { selections }
                        }));
                        console.log('Selection-done event dispatched');
                    });
                }}
            >
                <span class="text-sm font-medium">{$i18n.t('Done')}</span>
            </button>
        </div>
    {:else if $selectionModeEnabled && done}
        <!-- Debug: Show why Done button is not appearing -->
        <div class="mt-4 text-xs text-red-500">
            Debug: Selection mode enabled but Done button not showing. 
            Latest assistant message ID: {$latestAssistantMessageId}, 
            Current message ID: {messageId}, 
            Done: {done}
        </div>
    {/if}
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
