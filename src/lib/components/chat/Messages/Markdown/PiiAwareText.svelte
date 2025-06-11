<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import DOMPurify from 'dompurify';
	import {
		PiiSessionManager,
		unmaskAndHighlightTextForDisplay,
		type ExtendedPiiEntity
	} from '$lib/utils/pii';

	export let text: string;
	export let id: string = '';

	let containerElement: HTMLElement;
	let piiSessionManager = PiiSessionManager.getInstance();

	$: entities = piiSessionManager.getEntities();
	$: {
		console.log('PiiAwareText debug:', {
			id,
			text: text.substring(0, 50) + '...',
			entitiesCount: entities.length,
			entities: entities.map((e) => ({ label: e.label, text: e.raw_text })),
			hasContainer: !!containerElement
		});
	}
	$: processedText = (() => {
		if (!entities.length) {
			console.log('PiiAwareText: No entities, returning original text');
			return text;
		}

		// Check if text has already been processed (contains PII highlight spans)
		if (text.includes('<span class="pii-highlight')) {
			console.log('PiiAwareText: Text already contains PII highlights, skipping processing');
			return text;
		}

		console.log('PiiAwareText processing:', {
			entitiesCount: entities.length,
			textSample: text.substring(0, 100)
		});

		// Use the combined function that handles both unmasking and highlighting
		// This prevents double processing and position-based issues
		return unmaskAndHighlightTextForDisplay(text, entities);
	})();
	$: hasHighlighting = processedText !== text;

	const handleOverlayToggle = () => {
		// Refresh the highlighting when an entity is toggled
		// The reactive statement will automatically update processedText
	};

	// Add event listeners for PII highlights
	const addPiiEventListeners = () => {
		if (!containerElement) {
			console.log('PiiAwareText: No container element for adding event listeners');
			return;
		}

		const piiElements = containerElement.querySelectorAll('.pii-highlight');
		console.log('PiiAwareText: Adding event listeners to', piiElements.length, 'PII elements');

		piiElements.forEach((element) => {
			const htmlElement = element as HTMLElement;

			const handleClick = (event: MouseEvent) => {
				const target = event.target as HTMLElement;
				const entityLabel = target.getAttribute('data-pii-label');

				if (entityLabel) {
					piiSessionManager.toggleEntityMasking(entityLabel, 0);
					handleOverlayToggle();
					event.preventDefault();
				}
			};

			htmlElement.addEventListener('click', handleClick);

			// Store event listeners for cleanup
			(htmlElement as any)._piiEventListeners = {
				click: handleClick
			};
		});
	};

	const removePiiEventListeners = () => {
		if (!containerElement) return;

		const piiElements = containerElement.querySelectorAll('.pii-highlight');

		piiElements.forEach((element) => {
			const htmlElement = element as HTMLElement;
			const listeners = (htmlElement as any)._piiEventListeners;

			if (listeners) {
				htmlElement.removeEventListener('click', listeners.click);
				delete (htmlElement as any)._piiEventListeners;
			}
		});
	};

	// Re-add event listeners when the text changes
	$: if (containerElement && hasHighlighting) {
		// Use a small delay to ensure DOM is updated
		setTimeout(() => {
			removePiiEventListeners();
			addPiiEventListeners();
		}, 0);
	}

	onMount(() => {
		if (hasHighlighting) {
			addPiiEventListeners();
		}
	});

	onDestroy(() => {
		removePiiEventListeners();
	});
</script>

<span bind:this={containerElement} {id}>
	{#if hasHighlighting}
		{@html DOMPurify.sanitize(processedText)}
	{:else}
		{text}
	{/if}
</span>

<style>
	/* Ensure PII highlights are interactive */
	:global(.pii-highlight) {
		cursor: pointer;
		transition: all 0.2s ease;
		border-radius: 3px;
		padding: 1px 2px;
		position: relative;
	}

	:global(.pii-highlight:hover) {
		transform: translateY(-1px);
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
	}

	/* Masked entities - dark green font, green background, green dashed underline */
	:global(.pii-highlight.pii-masked) {
		color: #15803d;
		background-color: rgba(34, 197, 94, 0.2);
		border-bottom: 1px dashed #15803d;
	}

	:global(.pii-highlight.pii-masked:hover) {
		background-color: rgba(34, 197, 94, 0.3);
		border-bottom: 2px dashed #15803d;
	}

	/* Unmasked entities - red background, dashed red underline */
	:global(.pii-highlight.pii-unmasked) {
		background-color: rgba(239, 68, 68, 0.2);
		border-bottom: 1px dashed #dc2626;
	}

	:global(.pii-highlight.pii-unmasked:hover) {
		background-color: rgba(239, 68, 68, 0.3);
		border-bottom: 2px dashed #dc2626;
	}
</style>
