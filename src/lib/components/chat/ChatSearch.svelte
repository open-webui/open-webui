<script lang="ts">
	import { createEventDispatcher, onMount, onDestroy, tick } from 'svelte';
	import { fly } from 'svelte/transition';
	
	// Import existing icon components
	import Search from '../icons/Search.svelte';
	import ChevronUp from '../icons/ChevronUp.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';
	import XMark from '../icons/XMark.svelte';

	const dispatch = createEventDispatcher();

	export let show = false;
	export let history: { messages: Record<string, any>, currentId: string | null } = { messages: {}, currentId: null };
	
	let searchInput: HTMLInputElement;
	let searchContainer: HTMLDivElement;
	let searchQuery = '';
	let matchingMessageIds: string[] = [];
	let currentIndex = 0;
	let isNavigating = false;

	// Simplified performance optimizations
	let searchDebounceTimer: ReturnType<typeof setTimeout>;
	let lastSearchTerm = '';
	let messageElementCache = new Map<string, HTMLElement>();

	$: totalResults = matchingMessageIds.length;
	$: currentResult = totalResults > 0 ? currentIndex + 1 : 0;
	$: if (show && searchInput) searchInput.focus();

	const HIGHLIGHT_CLASS = 'search-highlight bg-yellow-300 dark:bg-yellow-500 px-1 py-0.5 rounded-md font-semibold border border-yellow-400 dark:border-yellow-600 shadow-sm';

	const handleKeydown = (e: KeyboardEvent) => {
		if (e.key === 'Escape') {
			closeSearch();
		} else if (e.key === 'Enter' && totalResults > 0) {
			e.preventDefault();
			if (e.shiftKey) {
				navigateToPrevious();
			} else {
				navigateToNext();
			}
		}
	};

	const closeSearch = () => {
		clearTimeout(searchDebounceTimer);
		clearHighlights();
		searchQuery = '';
		matchingMessageIds = [];
		currentIndex = 0;
		isNavigating = false;
		lastSearchTerm = '';
		messageElementCache.clear();
		dispatch('close');
	};

	// Get cached DOM element or fetch and cache it
	const getMessageElement = (messageId: string): HTMLElement | null => {
		let element = messageElementCache.get(messageId) || null;
		if (!element) {
			element = document.getElementById(`message-${messageId}`);
			if (element) {
				messageElementCache.set(messageId, element);
			}
		}
		return element;
	};

	const debouncedSearch = (query: string) => {
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(() => {
			performSearch(query);
		}, 150);
	};

	const performSearch = (query: string) => {
		const trimmedQuery = query.trim();
		
		if (!trimmedQuery || !history?.messages) {
			matchingMessageIds = [];
			currentIndex = 0;
			clearHighlights();
			lastSearchTerm = '';
			return;
		}

		const searchTerm = trimmedQuery.toLowerCase();
		
		// Skip if same search
		if (searchTerm === lastSearchTerm) return;
		
		lastSearchTerm = searchTerm;
		clearHighlights();
		
		// Find matching messages
		const messageResults: Array<{id: string, timestamp: number}> = [];
		Object.values(history.messages).forEach((message: any) => {
			if (message?.content && typeof message.content === 'string') {
				if (message.content.toLowerCase().includes(searchTerm)) {
					messageResults.push({
						id: message.id,
						timestamp: message.timestamp || 0
					});
				}
			}
		});

		messageResults.sort((a, b) => a.timestamp - b.timestamp);
		matchingMessageIds = messageResults.map(result => result.id);
		currentIndex = 0;
		
		// Auto-navigate to first result
		if (matchingMessageIds.length > 0) {
			setTimeout(() => navigateToCurrentResult(), 50);
		}
	};

	const calculateMessageDepth = (targetMessageId: string): number => {
		if (!history.currentId || !history.messages?.[targetMessageId]) return 100;
		
		let depth = 0;
		let messageId: string | null = history.currentId;
		
		// Walk backwards to find target
		while (messageId && depth < 500) {
			if (messageId === targetMessageId) return depth;
			const message: any = history.messages[messageId];
			if (!message?.parentId) break;
			messageId = message.parentId;
			depth++;
		}
		
		// Estimate from target to root
		depth = 0;
		messageId = targetMessageId;
		while (messageId && depth < 500) {
			const message: any = history.messages[messageId];
			if (!message?.parentId) break;
			messageId = message.parentId;
			depth++;
		}
		
		return depth + 20;
	};

	const navigateToCurrentResult = async () => {
		if (totalResults === 0) return;
		
		const targetMessageId = matchingMessageIds[currentIndex];
		const messageDepth = calculateMessageDepth(targetMessageId);
		const requiredCount = Math.max(messageDepth, 60);
		
		dispatch('ensureMessagesLoaded', { 
			messageId: targetMessageId, 
			requiredCount 
		});
		
		await tick();
		await new Promise(resolve => setTimeout(resolve, 300));
		await scrollToCurrentResult();
	};

	const highlightMatches = (searchTerm: string) => {
		matchingMessageIds.forEach(messageId => {
			const messageElement = getMessageElement(messageId);
			if (messageElement) {
				highlightInElement(messageElement, searchTerm);
			}
		});
	};

	const highlightInElement = (element: Element, searchTerm: string) => {
		const walker = document.createTreeWalker(
			element,
			NodeFilter.SHOW_TEXT,
			{
				acceptNode: (node) => {
					const parent = node.parentElement;
					if (!parent || parent.classList.contains('search-highlight') || 
						parent.tagName === 'SCRIPT' || parent.tagName === 'STYLE') {
						return NodeFilter.FILTER_REJECT;
					}
					return NodeFilter.FILTER_ACCEPT;
				}
			}
		);

		const textNodes: Text[] = [];
		let node;
		while (node = walker.nextNode()) {
			textNodes.push(node as Text);
		}

		const lowerSearchTerm = searchTerm.toLowerCase();
		textNodes.forEach(textNode => {
			const text = textNode.textContent || '';
			const lowerText = text.toLowerCase();
			
			if (lowerText.includes(lowerSearchTerm)) {
				const parent = textNode.parentNode;
				if (!parent) return;

				const fragment = document.createDocumentFragment();
				let lastIndex = 0;
				let match;
				
				while ((match = lowerText.indexOf(lowerSearchTerm, lastIndex)) !== -1) {
					if (match > lastIndex) {
						fragment.appendChild(document.createTextNode(text.slice(lastIndex, match)));
					}
					
					const highlight = document.createElement('span');
					highlight.className = HIGHLIGHT_CLASS;
					highlight.textContent = text.slice(match, match + searchTerm.length);
					fragment.appendChild(highlight);
					
					lastIndex = match + searchTerm.length;
				}
				
				if (lastIndex < text.length) {
					fragment.appendChild(document.createTextNode(text.slice(lastIndex)));
				}
				
				parent.replaceChild(fragment, textNode);
			}
		});
	};

	const clearHighlights = () => {
		const highlights = document.querySelectorAll('.search-highlight');
		highlights.forEach(highlight => {
			const parent = highlight.parentNode;
			if (parent) {
				parent.replaceChild(document.createTextNode(highlight.textContent || ''), highlight);
				parent.normalize();
			}
		});
	};

	const navigateToNext = () => {
		if (totalResults === 0) return;
		currentIndex = (currentIndex + 1) % totalResults;
		navigateToCurrentResult();
	};

	const navigateToPrevious = () => {
		if (totalResults === 0) return;
		currentIndex = currentIndex === 0 ? totalResults - 1 : currentIndex - 1;
		navigateToCurrentResult();
	};

	const scrollToCurrentResult = async () => {
		const messageId = matchingMessageIds[currentIndex];
		let messageElement = getMessageElement(messageId);
		
		// Wait for element if not available
		if (!messageElement) {
			await new Promise(resolve => setTimeout(resolve, 200));
			messageElement = getMessageElement(messageId);
			if (!messageElement) return;
		}

		// Highlight matches
		clearHighlights();
		if (lastSearchTerm) {
			highlightMatches(lastSearchTerm);
		}
		
		// Scroll and flash
		messageElement.scrollIntoView({ 
			behavior: 'smooth', 
			block: 'center',
			inline: 'nearest'
		});
		
		isNavigating = true;
		messageElement.style.transition = 'background-color 0.3s ease';
		messageElement.style.backgroundColor = 'rgba(0, 0, 0, 0.1)';
		
		setTimeout(() => {
			if (messageElement) {
				messageElement.style.backgroundColor = '';
			}
			isNavigating = false;
		}, 1000);
	};

	const handleInput = () => {
		debouncedSearch(searchQuery);
	};

	const handleClickOutside = (e: MouseEvent) => {
		if (show && searchContainer && !searchContainer.contains(e.target as Node)) {
			closeSearch();
		}
	};

	onMount(() => document.addEventListener('click', handleClickOutside));
	onDestroy(() => {
		clearTimeout(searchDebounceTimer);
		clearHighlights();
		document.removeEventListener('click', handleClickOutside);
	});
</script>

{#if show}
	<div 
		bind:this={searchContainer}
		class="fixed top-4 right-4 z-50 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-3 w-80"
		class:animate-pulse={isNavigating}
		transition:fly={{ y: -20, duration: 200 }}
		on:keydown={handleKeydown}
		role="dialog"
		aria-label="Chat search"
	>
		<div class="flex items-center gap-1">
			<Search className="w-4 h-4 text-gray-500 dark:text-gray-400 flex-shrink-0" />

			<input
				bind:this={searchInput}
				bind:value={searchQuery}
				on:input={handleInput}
				type="text"
				placeholder="Search in chat..."
				class="flex-1 min-w-0 bg-transparent border-none outline-none text-sm text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400"
			/>

			{#if totalResults > 0}
				<div class="text-xs font-medium text-black dark:text-white whitespace-nowrap flex-shrink-0">
					{currentResult} of {totalResults} {totalResults === 1 ? 'message' : 'messages'}
				</div>
			{:else if searchQuery.trim()}
				<div class="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap flex-shrink-0">
					No results
				</div>
			{/if}

			<div class="flex items-center gap-0.5 flex-shrink-0">
				<button
					class="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
					class:bg-gray-200={isNavigating}
					disabled={totalResults === 0}
					title="Previous (Shift+Enter)"
					aria-label="Previous result"
					on:click={navigateToPrevious}
				>
					<ChevronUp className="w-3 h-3" />
				</button>
				
				<button
					class="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
					class:bg-gray-200={isNavigating}
					disabled={totalResults === 0}
					title="Next (Enter)"
					aria-label="Next result"
					on:click={navigateToNext}
				>
					<ChevronDown className="w-3 h-3" />
				</button>
			</div>

			<button
				on:click={closeSearch}
				class="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors flex-shrink-0"
				title="Close (Esc)"
				aria-label="Close search"
			>
				<XMark className="w-3 h-3" />
			</button>
		</div>

		{#if searchQuery === ''}
			<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
				<kbd class="px-1 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs">Enter</kbd> next • 
				<kbd class="px-1 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs">Shift+Enter</kbd> previous
			</div>
		{:else if totalResults > 1}
			<div class="mt-2 text-xs text-gray-400 dark:text-gray-500">
				Navigate with <kbd class="px-1 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs">Enter</kbd> / 
				<kbd class="px-1 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs">Shift+Enter</kbd>
			</div>
		{:else if totalResults === 1}
			<div class="mt-2 text-xs text-green-600 dark:text-green-400">
				Found in 1 message
			</div>
		{/if}
	</div>
{/if}

<style>
	kbd {
		font-family: ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace;
	}
</style> 