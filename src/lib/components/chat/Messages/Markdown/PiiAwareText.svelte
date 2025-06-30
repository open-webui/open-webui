<script lang="ts">
	import DOMPurify from 'dompurify';
	import {
		PiiSessionManager,
		unmaskAndHighlightTextForDisplay,
	} from '$lib/utils/pii';

	export let text: string;
	export let id: string = '';
	export let conversationId: string = '';

	let containerElement: HTMLElement;
	let piiSessionManager = PiiSessionManager.getInstance();

	// This ensures cross-message consistency
	$: if (conversationId && conversationId !== '') {
		piiSessionManager.loadConversationState(conversationId);
	}

	$: entities = piiSessionManager.getEntitiesForDisplay(conversationId);
	
	$: processedText = (() => {
		if (!entities.length) {
			return text;
		}

		// Check if text has already been processed (contains PII highlight spans)
		if (text.includes('<span class="pii-highlight')) {
			return text;
		}

		// Use the combined function that handles both unmasking and highlighting
		// This prevents double processing and position-based issues
		return unmaskAndHighlightTextForDisplay(text, entities);
	})();
	$: hasHighlighting = processedText !== text;
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
		border-bottom: 2px dashed #15803d;
	}

	:global(.pii-highlight.pii-masked:hover) {
		background-color: rgba(34, 197, 94, 0.3);
		border-bottom: 3px dashed #15803d;
	}

	/* Unmasked entities - red background, solid red underline */
	:global(.pii-highlight.pii-unmasked) {
		background-color: rgba(239, 68, 68, 0.2);
		border-bottom: 1px solid #dc2626;
	}

	:global(.pii-highlight.pii-unmasked:hover) {
		background-color: rgba(239, 68, 68, 0.3);
		border-bottom: 2px solid #dc2626;
	}

	/* Modifier-affected text - yellow font (base styling) */
	:global(.pii-modifier-highlight) {
		color: #ca8a04;
		cursor: pointer;
		transition: all 0.2s ease;
	}

	:global(.pii-modifier-highlight:hover) {
		color: #a16207;
	}

	/* Mask modifier - yellow font, green background, green dashed underline */
	:global(.pii-modifier-highlight.pii-modifier-mask) {
		color: #ca8a04;
		background-color: rgba(34, 197, 94, 0.2);
		border-bottom: 1px dashed #15803d;
		border-radius: 3px;
		padding: 1px 2px;
	}

	:global(.pii-modifier-highlight.pii-modifier-mask:hover) {
		color: #a16207;
		background-color: rgba(34, 197, 94, 0.3);
		border-bottom: 2px dashed #15803d;
	}
</style>
