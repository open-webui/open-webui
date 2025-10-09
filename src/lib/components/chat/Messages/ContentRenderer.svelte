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
	import { getCurrentChildMarker } from '$lib/utils/childUtils';

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
	export let allowTextSelection = false;

	export let onSave = (e) => {};
	export let onSourceClick = (e) => {};
	export let onTaskClick = (e) => {};
	export let onAddMessages = (e) => {};

	let contentContainerElement;
	let floatingButtonsElement;
	
	// Delete selection popup state
	let showDeletePopup = false;
	let deletePopupElement;
	let selectedTextToDelete = '';
	let selectedMarkToDelete = null;
	
	// Edit selections popup state
	let showEditSelectionsPopupState = false;
	let editSelectionsPopupElement;

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
    if (floatingButtons || ($selectionModeEnabled && allowTextSelection)) {
        attachListeners();
		}
	});

	onDestroy(() => {
    detachListeners();
});

// React to selection mode changes to attach/detach listeners dynamically
$: {
    if ($selectionModeEnabled && allowTextSelection) {
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
    // Add click handler for selection interaction
    mark.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        handleSelectionClick(mark, text);
    });
    range.deleteContents();
    range.insertNode(mark);
    selection.removeAllRanges();

    // Only allow selection on the most recent assistant message
    if ($latestAssistantMessageId && $latestAssistantMessageId !== messageId) {
        closeFloatingButtons();
        return;
    }

    // Save to both localStorage and backend via sync service
    const currentChatId = chatId || $chatIdStore;
    if (!currentChatId) return;
    
    try {
        await selectionSyncService.saveSelection({
            chat_id: currentChatId,
            message_id: messageId,
            role: 'assistant',
            selected_text: text,
            child_marker: getCurrentChildMarker() || undefined,
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

// Handle selection click based on current state
const handleSelectionClick = (markElement, text) => {
    // Check if this is the most recent assistant message
    const isMostRecent = $latestAssistantMessageId === messageId;
    
    if (!isMostRecent) {
        // Don't show any popup for selections in older messages
        return;
    }
    
    if ($selectionModeEnabled) {
        // In selection mode, show delete popup
        showDeleteSelectionPopup(markElement, text);
    } else {
        // Not in selection mode, show edit selections popup
        showEditSelectionsPopup(markElement, text);
    }
};

// Show delete selection popup
const showDeleteSelectionPopup = (markElement, text) => {
    selectedTextToDelete = text;
    selectedMarkToDelete = markElement;
    showDeletePopup = true;
    
    // Position the popup next to the selection like the Save button
    setTimeout(() => {
        if (deletePopupElement && markElement && contentContainerElement) {
            const markRect = markElement.getBoundingClientRect();
            const parentRect = contentContainerElement.getBoundingClientRect();
            
            // Calculate position relative to the content container
            const top = markRect.bottom - parentRect.top;
            const left = markRect.left - parentRect.left;
            
            // Calculate space available on the right
            const spaceOnRight = parentRect.width - left;
            let halfScreenWidth = $mobile ? window.innerWidth / 2 : window.innerWidth / 3;
            
            if (spaceOnRight < halfScreenWidth) {
                const right = parentRect.right - markRect.right;
                deletePopupElement.style.right = `${right}px`;
                deletePopupElement.style.left = 'auto';
            } else {
                deletePopupElement.style.left = `${left}px`;
                deletePopupElement.style.right = 'auto';
            }
            
            deletePopupElement.style.top = `${top + 5}px`;
            
            // Show the popup after positioning
            deletePopupElement.style.display = 'block';
        }
    }, 0);
};

// Show edit selections popup
const showEditSelectionsPopup = (markElement, text) => {
    selectedTextToDelete = text;
    selectedMarkToDelete = markElement;
    showEditSelectionsPopupState = true;
    
    // Position the popup next to the selection like the Save button
    setTimeout(() => {
        if (editSelectionsPopupElement && markElement && contentContainerElement) {
            const markRect = markElement.getBoundingClientRect();
            const parentRect = contentContainerElement.getBoundingClientRect();
            
            // Calculate position relative to the content container
            const top = markRect.bottom - parentRect.top;
            const left = markRect.left - parentRect.left;
            
            // Calculate space available on the right
            const spaceOnRight = parentRect.width - left;
            let halfScreenWidth = $mobile ? window.innerWidth / 2 : window.innerWidth / 3;
            
            if (spaceOnRight < halfScreenWidth) {
                const right = parentRect.right - markRect.right;
                editSelectionsPopupElement.style.right = `${right}px`;
                editSelectionsPopupElement.style.left = 'auto';
            } else {
                editSelectionsPopupElement.style.left = `${left}px`;
                editSelectionsPopupElement.style.right = 'auto';
            }
            
            editSelectionsPopupElement.style.top = `${top + 5}px`;
            
            // Show the popup after positioning
            editSelectionsPopupElement.style.display = 'block';
        }
    }, 0);
};

// Delete a selection
const deleteSelection = async () => {
    if (!selectedTextToDelete || !selectedMarkToDelete) return;
    
    // Remove from backend and localStorage using selectionSyncService
    const currentChatId = chatId || $chatIdStore;
    if (currentChatId) {
        try {
            await selectionSyncService.deleteSelection({
                chat_id: currentChatId,
                message_id: messageId,
                role: 'assistant',
                selected_text: selectedTextToDelete
            });
        } catch (error) {
            console.error('Failed to delete selection from backend:', error);
        }
    }
    
    // Remove the mark element from DOM
    if (selectedMarkToDelete && selectedMarkToDelete.parentNode) {
        const parent = selectedMarkToDelete.parentNode;
        const textNode = document.createTextNode(selectedTextToDelete);
        parent.replaceChild(textNode, selectedMarkToDelete);
        
        // Merge adjacent text nodes
        parent.normalize();
    }
    
    // Close popup
    showDeletePopup = false;
    selectedTextToDelete = '';
    selectedMarkToDelete = null;
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
            // Add click handler for selection interaction
            mark.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                handleSelectionClick(mark, target);
            });

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
    const currentChildMarker = getCurrentChildMarker();
    const items = ($savedSelections || []).filter(
        (s) => s.chatId === chat && s.messageId === messageId && s.role === 'assistant' && 
               (s.childMarker === currentChildMarker || (!s.childMarker && !currentChildMarker))
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
    
    // Listen for child profile changes to refresh selections
    const handleRefreshSelections = () => {
        // Clear existing selections first
        const root = contentContainerElement;
        if (root) {
            const existingMarks = Array.from(root.querySelectorAll('mark.selection-highlight'));
            existingMarks.forEach(mark => {
                const parent = mark.parentNode;
                if (parent) {
                    parent.replaceChild(document.createTextNode(mark.textContent || ''), mark);
                    parent.normalize();
                }
            });
        }
        // Reapply selections with new child filter
        setTimeout(() => {
            applySavedSelections();
        }, 50);
    };
    
    window.addEventListener('refresh-selections', handleRefreshSelections);
    
    return () => {
        window.removeEventListener('refresh-selections', handleRefreshSelections);
    };
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

{#if $selectionModeEnabled && allowTextSelection}
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

<!-- Delete Selection Popup -->
{#if showDeletePopup}
	<div
		bind:this={deletePopupElement}
		class="absolute rounded-lg mt-1 text-xs z-9999 bg-white dark:bg-gray-850 dark:text-gray-100 text-medium rounded-lg shadow-xl p-1"
		style="display: none;"
	>
		<div class="flex flex-row gap-0.5 shrink-0">
			<button
				class="px-2 py-0.5 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-sm min-w-fit text-red-600 dark:text-red-400"
				on:click={() => {
					deleteSelection();
				}}
			>
				{$i18n.t('Delete')}
			</button>
			<button
				class="px-2 py-0.5 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-sm min-w-fit"
				on:click={() => {
					showDeletePopup = false;
					selectedTextToDelete = '';
					selectedMarkToDelete = null;
				}}
			>
				{$i18n.t('Cancel')}
			</button>
		</div>
	</div>
{/if}

<!-- Edit Selections Popup -->
{#if showEditSelectionsPopupState}
	<div
		bind:this={editSelectionsPopupElement}
		class="absolute rounded-lg mt-1 text-xs z-9999 bg-white dark:bg-gray-850 dark:text-gray-100 text-medium rounded-lg shadow-xl p-1"
		style="display: none;"
	>
		<div class="flex flex-row gap-0.5 shrink-0">
			<button
				class="px-2 py-0.5 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-sm min-w-fit"
				on:click={() => {
					// Trigger selection mode
					selectionModeEnabled.set(true);
					window.dispatchEvent(new CustomEvent('set-input-panel-state', {
						detail: { state: 'selection' }
					}));
					// Close the popup
					showEditSelectionsPopupState = false;
					selectedTextToDelete = '';
					selectedMarkToDelete = null;
				}}
			>
				{$i18n.t('Edit Selections')}
			</button>
			<button
				class="px-2 py-0.5 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-sm min-w-fit"
				on:click={() => {
					showEditSelectionsPopupState = false;
					selectedTextToDelete = '';
					selectedMarkToDelete = null;
				}}
			>
				{$i18n.t('Cancel')}
			</button>
		</div>
	</div>
{/if}
