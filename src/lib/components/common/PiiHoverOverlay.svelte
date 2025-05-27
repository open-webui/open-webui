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
	$: statusText = shouldMask ? 'Protected by NENNA.AI' : 'Unprotected';
	$: statusColor = shouldMask ? 'text-[#3f3d8a]' : 'text-red-600 dark:text-red-400';
	$: statusBgColor = shouldMask ? 'bg-[#f8b76b]/20' : 'bg-red-50 dark:bg-red-900/20';
	

	
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
	
	// Prevent overlay from disappearing when hovering over it
	const handleOverlayMouseEnter = () => {
		// Dispatch event to parent to prevent hiding
		dispatch('overlayMouseEnter');
	};
	
	const handleOverlayMouseLeave = () => {
		// Dispatch event to parent to potentially hide after delay
		dispatch('overlayMouseLeave');
	};
	
	// Placeholder functions to maintain compatibility with parent components
	const handleToggle = () => {
		// Dispatch toggle event to parent components that expect it
		dispatch('toggle', { entity });
	};
	
	const handleCopy = (text: string) => {
		// Dispatch copy event to parent components that expect it
		dispatch('copy', { text });
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
		on:click|stopPropagation
		on:mouseenter={handleOverlayMouseEnter}
		on:mouseleave={handleOverlayMouseLeave}
	>
		<div
			class="bg-white dark:bg-gray-900 rounded-lg shadow-lg border border-[#f8b76b] dark:border-[#3f3d8a] min-w-56 max-w-80 custom-overlay"
			transition:fly={{ y: 10, duration: 200 }}
		>
			<!-- Header -->
			<div class="px-3 py-2 border-b border-[#f8b76b]/30 dark:border-[#3f3d8a]/50 bg-gradient-to-r from-[#f8b76b]/10 to-[#f9c689]/20 dark:from-[#3f3d8a]/10 dark:to-[#3f3d8a]/20">
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-2">
						<!-- Custom Logo/Icon -->
						<div class="flex items-center gap-1.5">
							<div class="w-4 h-4 rounded flex items-center justify-center overflow-hidden">
								<img src="/static/static/icon-purple-128.png" alt="Logo" class="w-full h-full object-cover" />
							</div>
							<div class="text-xs font-bold text-[#3f3d8a] tracking-wider">NENNA.AI</div>
						</div>
						<div class="w-2 h-2 rounded-full {shouldMask ? 'bg-[#f8b76b]' : 'bg-red-500'}"></div>
						<h3 class="font-medium text-sm text-[#3f3d8a] dark:text-[#f8b76b]">
							PII
						</h3>
					</div>
					<button
						class="text-[#3f3d8a] hover:text-[#3f3d8a]/80 dark:text-[#f8b76b] dark:hover:text-[#f9c689] transition-colors p-0.5 hover:bg-[#f9c689]/30 dark:hover:bg-[#3f3d8a]/20 rounded"
						on:click={() => visible = false}
					>
						<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
				</div>
			</div>
			
			<!-- Content -->
			<div class="px-3 py-2 space-y-2">
				<!-- Entity Info -->
				<div class="space-y-1.5">
					<div class="flex items-center justify-between">
						<span class="text-xs font-medium text-[#3f3d8a] dark:text-[#f8b76b]">Type:</span>
						<span class="text-xs font-semibold text-[#3f3d8a] dark:text-white uppercase px-1.5 py-0.5 bg-[#f8b76b]/20 dark:bg-[#3f3d8a]/20 rounded">
							{entity.type}
						</span>
					</div>
					
					<div class="flex items-center justify-between">
						<span class="text-xs font-medium text-[#3f3d8a] dark:text-[#f8b76b]">Text:</span>
						<span class="text-xs text-[#3f3d8a] dark:text-white text-right break-all bg-[#f8b76b]/10 dark:bg-[#3f3d8a]/10 px-1.5 py-0.5 rounded italic max-w-32">
							"{entity.raw_text}"
						</span>
					</div>
					
					<div class="flex items-center justify-between">
						<span class="text-xs font-medium text-[#3f3d8a] dark:text-[#f8b76b]">Masked as:</span>
						<span class="text-xs font-mono text-[#3f3d8a] dark:text-white text-right break-all bg-[#f8b76b]/10 dark:bg-[#3f3d8a]/10 px-1.5 py-0.5 rounded font-semibold max-w-32">
							[{`{${entity.label}}`}]
						</span>
					</div>
				</div>
				
				<!-- Status -->
				<div class="p-2 rounded {statusBgColor} border border-current border-opacity-20">
					<div class="flex items-center gap-1.5">
						<svg class="w-3 h-3 {statusColor}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							{#if shouldMask}
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
							{:else}
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
							{/if}
						</svg>
						<span class="text-xs font-medium {statusColor}">
							{shouldMask ? 'Protected' : 'Unprotected'}
						</span>
					</div>
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

	/* Custom Color Theme with Orange/Purple */
	:global(.custom-overlay) {
		backdrop-filter: blur(8px);
		box-shadow: 
			0 20px 25px -5px rgba(248, 183, 107, 0.15),
			0 10px 10px -5px rgba(248, 183, 107, 0.08);
	}

	:global(.dark .custom-overlay) {
		box-shadow: 
			0 20px 25px -5px rgba(63, 61, 138, 0.25),
			0 10px 10px -5px rgba(63, 61, 138, 0.15);
	}

	/* Ensure proper image sizing and fit */
	:global(.custom-overlay img) {
		object-fit: contain;
		max-width: 100%;
		max-height: 100%;
	}
</style> 