<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import DOMPurify from 'dompurify';
	import { PiiSessionManager, highlightUnmaskedEntities, unmaskTextWithEntities, type ExtendedPiiEntity } from '$lib/utils/pii';
	import PiiHoverOverlay from '../../../common/PiiHoverOverlay.svelte';

	export let text: string;
	export let id: string = '';

	let containerElement: HTMLElement;
	let piiSessionManager = PiiSessionManager.getInstance();
	
	// Hover overlay state
	let hoverOverlayVisible = false;
	let hoverOverlayEntity: ExtendedPiiEntity | null = null;
	let hoverOverlayPosition = { x: 0, y: 0 };
	let hoverTimeout: ReturnType<typeof setTimeout>;

	$: entities = piiSessionManager.getEntities();
	$: {
		console.log('PiiAwareText debug:', {
			id,
			text: text.substring(0, 50) + '...',
			entitiesCount: entities.length,
			entities: entities.map(e => ({ label: e.label, text: e.raw_text })),
			hasContainer: !!containerElement
		});
	}
	$: processedText = (() => {
		if (!entities.length) {
			console.log('PiiAwareText: No entities, returning original text');
			return text;
		}
		
		// First, check if the text contains masked patterns like [{LABEL_ID}]
		// Create a fresh regex each time to avoid state issues
		const maskedPatternRegex = /\[?\{?([A-Z_]+_\d+)\}?\]?/;
		const hasMaskedPatterns = maskedPatternRegex.test(text);
		
		console.log('PiiAwareText processing:', {
			hasMaskedPatterns,
			textSample: text.substring(0, 100)
		});
		
		if (hasMaskedPatterns) {
			// If it has masked patterns, unmask them first
			const unmaskedText = unmaskTextWithEntities(text, entities);
			// Then apply highlighting to the unmasked text
			const highlighted = highlightUnmaskedEntities(unmaskedText, entities);
			console.log('PiiAwareText: Unmasked and highlighted', { unmaskedText, highlighted });
			return highlighted;
		} else {
			// If no masked patterns, just apply highlighting directly
			const highlighted = highlightUnmaskedEntities(text, entities);
			console.log('PiiAwareText: Direct highlighting', { original: text, highlighted });
			return highlighted;
		}
	})();
	$: hasHighlighting = processedText !== text;

	// Hover overlay handlers
	const handlePiiHover = (entity: ExtendedPiiEntity, position: { x: number, y: number }) => {
		clearTimeout(hoverTimeout);
		hoverOverlayEntity = entity;
		hoverOverlayPosition = position;
		hoverOverlayVisible = true;
	};

	const handlePiiHoverEnd = () => {
		clearTimeout(hoverTimeout);
		hoverTimeout = setTimeout(() => {
			hoverOverlayVisible = false;
			hoverOverlayEntity = null;
		}, 200);
	};

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
			
			const handleMouseEnter = (event: MouseEvent) => {
				console.log('PiiAwareText: Mouse enter event triggered');
				const target = event.target as HTMLElement;
				const entityLabel = target.getAttribute('data-pii-label');
				console.log('PiiAwareText: Entity label found:', entityLabel);
				
				if (entityLabel) {
					const entity = entities.find(e => e.label === entityLabel);
					console.log('PiiAwareText: Found entity:', entity);
					if (entity) {
						const rect = target.getBoundingClientRect();
						const position = {
							x: rect.left + rect.width / 2,
							y: rect.top
						};
						console.log('PiiAwareText: Calling handlePiiHover with position:', position);
						handlePiiHover(entity, position);
					}
				}
			};

			const handleMouseLeave = () => {
				handlePiiHoverEnd();
			};

			const handleClick = (event: MouseEvent) => {
				const target = event.target as HTMLElement;
				const entityLabel = target.getAttribute('data-pii-label');
				
				if (entityLabel) {
					piiSessionManager.toggleEntityMasking(entityLabel, 0);
					handleOverlayToggle();
					event.preventDefault();
				}
			};

			htmlElement.addEventListener('mouseenter', handleMouseEnter);
			htmlElement.addEventListener('mouseleave', handleMouseLeave);
			htmlElement.addEventListener('click', handleClick);
			
			// Store event listeners for cleanup
			(htmlElement as any)._piiEventListeners = {
				mouseenter: handleMouseEnter,
				mouseleave: handleMouseLeave,
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
				htmlElement.removeEventListener('mouseenter', listeners.mouseenter);
				htmlElement.removeEventListener('mouseleave', listeners.mouseleave);
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
		clearTimeout(hoverTimeout);
	});
</script>

<span bind:this={containerElement} {id}>
	{#if hasHighlighting}
		{@html DOMPurify.sanitize(processedText)}
	{:else}
		{text}
	{/if}
</span>

<!-- PII Hover Overlay -->
<PiiHoverOverlay
	bind:visible={hoverOverlayVisible}
	entity={hoverOverlayEntity}
	position={hoverOverlayPosition}
	on:toggle={handleOverlayToggle}
	on:copy={(event) => {
		console.log('Copied:', event.detail.text);
	}}
/>

<style>
	/* Ensure PII highlights are interactive */
	:global(.pii-highlight) {
		cursor: pointer;
		transition: all 0.2s ease;
	}
	
	:global(.pii-highlight:hover) {
		transform: translateY(-1px);
		box-shadow: 0 2px 4px rgba(0,0,0,0.1);
	}
</style> 