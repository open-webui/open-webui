<script lang="ts">
	import { createEventDispatcher, onMount, onDestroy } from 'svelte';
	import { fade, fly } from 'svelte/transition';
	import type { ExtendedPiiEntity } from '$lib/utils/pii';
	import { PiiSessionManager } from '$lib/utils/pii';
	
	const dispatch = createEventDispatcher();
	
	export let entity: ExtendedPiiEntity | null = null;
	export let position = { x: 0, y: 0 };
	export let visible = false;
	
	let overlayElement: HTMLDivElement;
	let piiSessionManager = PiiSessionManager.getInstance();
	
	$: shouldMask = entity?.shouldMask ?? true;
	$: statusText = shouldMask ? 'Will be masked' : 'Will NOT be masked';
	$: statusColor = shouldMask ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400';
	$: statusBgColor = shouldMask ? 'bg-green-50 dark:bg-green-900/20' : 'bg-red-50 dark:bg-red-900/20';
	
	const toggleMasking = () => {
		if (entity) {
			piiSessionManager.toggleEntityMasking(entity.label, 0);
			// Update the entity reference
			entity = { ...entity, shouldMask: !entity.shouldMask };
			dispatch('toggle', { entity });
		}
	};
	
	const copyOriginalText = () => {
		if (entity) {
			navigator.clipboard.writeText(entity.text);
			dispatch('copy', { text: entity.text });
		}
	};
	
	const copyMaskedText = () => {
		if (entity) {
			const maskedText = `[{${entity.label}}]`;
			navigator.clipboard.writeText(maskedText);
			dispatch('copy', { text: maskedText });
		}
	};
	
	// Position the overlay to avoid going off-screen
	$: overlayStyle = (() => {
		if (!visible || !overlayElement) return '';
		
		const rect = overlayElement.getBoundingClientRect();
		const viewportWidth = window.innerWidth;
		const viewportHeight = window.innerHeight;
		
		let x = position.x;
		let y = position.y - rect.height - 10; // Position above the element by default
		
		// Adjust horizontal position if it would go off-screen
		if (x + rect.width > viewportWidth) {
			x = viewportWidth - rect.width - 10;
		}
		if (x < 10) {
			x = 10;
		}
		
		// If positioning above would go off-screen, position below
		if (y < 10) {
			y = position.y + 30; // Position below the element
		}
		
		return `left: ${x}px; top: ${y}px;`;
	})();
	
	// Close overlay when clicking outside
	const handleClickOutside = (event: MouseEvent) => {
		if (overlayElement && !overlayElement.contains(event.target as Node)) {
			visible = false;
		}
	};
	
	onMount(() => {
		document.addEventListener('click', handleClickOutside);
	});
	
	onDestroy(() => {
		document.removeEventListener('click', handleClickOutside);
	});
</script>

{#if visible && entity}
	<div
		bind:this={overlayElement}
		class="fixed z-50 pointer-events-auto"
		style={overlayStyle}
		transition:fade={{ duration: 150 }}
		on:click|stopPropagation
	>
		<div
			class="bg-white dark:bg-gray-850 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 min-w-72 max-w-96"
			transition:fly={{ y: 10, duration: 200 }}
		>
			<!-- Header -->
			<div class="px-4 py-3 border-b border-gray-100 dark:border-gray-700">
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-2">
						<div class="w-3 h-3 rounded-full {shouldMask ? 'bg-green-500' : 'bg-red-500'}"></div>
						<h3 class="font-semibold text-gray-900 dark:text-gray-100">
							PII Detected
						</h3>
					</div>
					<button
						class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
						on:click={() => visible = false}
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
				</div>
			</div>
			
			<!-- Content -->
			<div class="px-4 py-3 space-y-3">
				<!-- Entity Info -->
				<div class="space-y-2">
					<div class="flex items-center justify-between">
						<span class="text-sm font-medium text-gray-600 dark:text-gray-400">Type:</span>
						<span class="text-sm font-semibold text-gray-900 dark:text-gray-100 uppercase">
							{entity.type}
						</span>
					</div>
					
					<div class="flex items-center justify-between">
						<span class="text-sm font-medium text-gray-600 dark:text-gray-400">Label:</span>
						<span class="text-sm font-mono bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded text-gray-900 dark:text-gray-100">
							{entity.label}
						</span>
					</div>
					
					<div class="flex items-start justify-between gap-2">
						<span class="text-sm font-medium text-gray-600 dark:text-gray-400 flex-shrink-0">Text:</span>
						<span class="text-sm text-gray-900 dark:text-gray-100 text-right break-all">
							"{entity.text}"
						</span>
					</div>
				</div>
				
				<!-- Status -->
				<div class="p-3 rounded-lg {statusBgColor}">
					<div class="flex items-center gap-2">
						<svg class="w-4 h-4 {statusColor}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							{#if shouldMask}
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
							{:else}
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
							{/if}
						</svg>
						<span class="text-sm font-medium {statusColor}">
							{statusText}
						</span>
					</div>
					<p class="text-xs text-gray-600 dark:text-gray-400 mt-1">
						{#if shouldMask}
							This entity will be replaced with [{entity.label}] when sent to AI models.
						{:else}
							This entity will be sent as-is to AI models without masking.
						{/if}
					</p>
				</div>
			</div>
			
			<!-- Actions -->
			<div class="px-4 py-3 border-t border-gray-100 dark:border-gray-700">
				<div class="flex gap-2">
					<button
						class="flex-1 px-3 py-2 text-sm font-medium rounded-lg transition-colors {shouldMask 
							? 'bg-red-100 hover:bg-red-200 text-red-700 dark:bg-red-900/20 dark:hover:bg-red-900/30 dark:text-red-400'
							: 'bg-green-100 hover:bg-green-200 text-green-700 dark:bg-green-900/20 dark:hover:bg-green-900/30 dark:text-green-400'
						}"
						on:click={toggleMasking}
					>
						{shouldMask ? 'Don\'t Mask' : 'Mask This'}
					</button>
					
					<button
						class="px-3 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
						on:click={copyOriginalText}
						title="Copy original text"
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
						</svg>
					</button>
					
					<button
						class="px-3 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
						on:click={copyMaskedText}
						title="Copy masked format"
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
						</svg>
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}

<style>
	/* Ensure the overlay appears above other elements */
	:global(.pii-hover-overlay) {
		z-index: 9999;
	}
</style> 