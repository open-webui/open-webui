<script lang="ts">
	import { createEventDispatcher, onMount, onDestroy } from 'svelte';
	import { fly } from 'svelte/transition';
	
	// Import existing icon components
	import Search from '../icons/Search.svelte';
	import ChevronUp from '../icons/ChevronUp.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';
	import XMark from '../icons/XMark.svelte';

	const dispatch = createEventDispatcher();

	export let show = false;
	export let history = { messages: {}, currentId: null };
	
	let searchInput: HTMLInputElement;
	let searchContainer: HTMLDivElement;
	let searchQuery = '';
	let matchingMessageIds: string[] = [];
	let currentIndex = 0;
	let isNavigating = false;

	$: totalResults = matchingMessageIds.length;
	$: currentResult = totalResults > 0 ? currentIndex + 1 : 0;
	$: if (show && searchInput) searchInput.focus();

	const HIGHLIGHT_CLASS = 'search-highlight bg-yellow-200 dark:bg-yellow-600 px-0.5 rounded underline';
	const HIGHLIGHT_BLUE_CLASS = 'search-highlight bg-blue-200 dark:bg-blue-600 px-0.5 rounded underline';

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
		clearHighlights();
		searchQuery = '';
		matchingMessageIds = [];
		currentIndex = 0;
		isNavigating = false;
		dispatch('close');
	};

	const performSearch = (query: string) => {
		clearHighlights();
		
		if (!query.trim() || !history?.messages) {
			matchingMessageIds = [];
			currentIndex = 0;
			return;
		}

		const searchTerm = query.toLowerCase().trim();
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
		
		if (matchingMessageIds.length > 0) {
			highlightMatches(searchTerm);
			scrollToCurrentResult();
		}
	};

	const highlightMatches = (searchTerm: string) => {
		matchingMessageIds.forEach(messageId => {
			const messageElement = document.getElementById(`message-${messageId}`);
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

		textNodes.forEach(textNode => {
			const text = textNode.textContent || '';
			const lowerText = text.toLowerCase();
			const lowerSearchTerm = searchTerm.toLowerCase();
			
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
		const nextIndex = (currentIndex + 1) % totalResults;
		navigateToIndex(nextIndex);
	};

	const navigateToPrevious = () => {
		if (totalResults === 0) return;
		const prevIndex = currentIndex === 0 ? totalResults - 1 : currentIndex - 1;
		navigateToIndex(prevIndex);
	};

	const navigateToIndex = (newIndex: number) => {
		currentIndex = newIndex;
		scrollToCurrentResult();
		
		isNavigating = true;
		setTimeout(() => {
			isNavigating = false;
		}, 300);
	};

	const scrollToCurrentResult = () => {
		const messageId = matchingMessageIds[currentIndex];
		const messageElement = document.getElementById(`message-${messageId}`);
		if (!messageElement) return;

		messageElement.scrollIntoView({ 
			behavior: 'smooth', 
			block: 'center',
			inline: 'nearest'
		});
		
		setHighlightColor('blue');
		
		messageElement.style.transition = 'background-color 0.3s ease';
		messageElement.style.backgroundColor = 'rgba(59, 130, 246, 0.1)';
		
		setTimeout(() => {
			messageElement.style.backgroundColor = '';
		}, 1000);
	};

	const setHighlightColor = (color: 'yellow' | 'blue') => {
		const allHighlights = document.querySelectorAll('.search-highlight');
		const colorClass = color === 'blue' ? HIGHLIGHT_BLUE_CLASS : HIGHLIGHT_CLASS;
		
		allHighlights.forEach(highlight => {
			highlight.className = colorClass;
		});
	};

	const handleInput = () => {
		performSearch(searchQuery);
	};

	const handleClickOutside = (e: MouseEvent) => {
		if (show && searchContainer && !searchContainer.contains(e.target as Node)) {
			closeSearch();
		}
	};

	onMount(() => document.addEventListener('click', handleClickOutside));
	onDestroy(() => {
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

			<!-- Results Counter with enhanced styling -->
			{#if totalResults > 0}
				<div class="text-xs font-medium text-blue-600 dark:text-blue-400 whitespace-nowrap flex-shrink-0">
					{currentResult} of {totalResults} {totalResults === 1 ? 'message' : 'messages'}
				</div>
			{:else if searchQuery.trim()}
				<div class="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap flex-shrink-0">
					No results
				</div>
			{/if}

			<!-- Navigation Buttons with enhanced states -->
			<div class="flex items-center gap-0.5 flex-shrink-0">
				<button
					class="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
					class:bg-blue-50={isNavigating}
					disabled={totalResults === 0}
					title="Previous (Shift+Enter or Cmd+↑)"
					aria-label="Previous result"
					on:click={navigateToPrevious}
				>
					<ChevronUp className="w-3 h-3" />
				</button>
				
				<button
					class="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
					class:bg-blue-50={isNavigating}
					disabled={totalResults === 0}
					title="Next (Enter or Cmd+↓)"
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

		<!-- Enhanced Search Tips -->
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
				Found in 1 message with highlights
			</div>
		{/if}
	</div>
{/if}

<style>
	kbd {
		font-family: ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace;
	}
</style> 