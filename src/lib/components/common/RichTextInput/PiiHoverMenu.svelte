<script lang="ts">
	import { createEventDispatcher, onMount, onDestroy, getContext } from 'svelte';
	import { tick } from 'svelte';
	import Tooltip from '../Tooltip.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let wordInfo: { word: string; from: number; to: number; x: number; y: number };
	export let showIgnoreButton: boolean = false;
	export let existingModifiers: any[] = [];
	export let showTextField: boolean = true;
	export let visible: boolean = false;
	export let currentLabel: string | undefined;

	let labelInput: HTMLInputElement;
	let menuElement: HTMLDivElement;
	let label = 'CUSTOM';
	let isDefaultValue = true;
	let skipAutocompletion = false;

	async function focusInputSoon() {
		if (!showTextField) return;
		// Disable auto-focus in KnowledgeBase to prevent scroll jumps
		if (typeof document !== 'undefined' && document.getElementById('collection-container')) {
			return;
		}
		await tick();
		setTimeout(() => {
			try {
				// Collect scrollable ancestors near the trigger point
				const scrollables: Array<{
					el: Element | 'window';
					x: number;
					y: number;
					sx?: number;
					sy?: number;
				}> = [];
				const addScrollable = (el: Element) => {
					const style = window.getComputedStyle(el as HTMLElement);
					const overflowY = style.overflowY;
					const overflowX = style.overflowX;
					const canScrollY =
						(overflowY === 'auto' || overflowY === 'scroll') &&
						(el as HTMLElement).scrollHeight > (el as HTMLElement).clientHeight;
					const canScrollX =
						(overflowX === 'auto' || overflowX === 'scroll') &&
						(el as HTMLElement).scrollWidth > (el as HTMLElement).clientWidth;
					if (canScrollY || canScrollX) {
						scrollables.push({
							el,
							x: (el as HTMLElement).scrollLeft,
							y: (el as HTMLElement).scrollTop
						});
					}
				};
				if (wordInfo && typeof wordInfo.x === 'number' && typeof wordInfo.y === 'number') {
					let node = document.elementFromPoint(wordInfo.x, wordInfo.y) as HTMLElement | null;
					let safety = 0;
					while (node && safety < 25) {
						addScrollable(node);
						node = node.parentElement;
						safety++;
					}
				}
				// Also snapshot window
				const winSX = window.scrollX;
				const winSY = window.scrollY;
				scrollables.push({ el: 'window', x: winSX, y: winSY });

				labelInput?.focus({ preventScroll: true } as any);

				// Restore scrolls synchronously and on next frame
				const restore = () => {
					scrollables.forEach((s) => {
						if (s.el === 'window') {
							window.scrollTo(s.x, s.y);
						} else {
							const el = s.el as HTMLElement;
							el.scrollLeft = s.x;
							el.scrollTop = s.y;
						}
					});
				};
				restore();
				requestAnimationFrame(restore);
			} catch {}
		}, 0);
	}

	// Predefined PII labels for autocompletion
	const PREDEFINED_LABELS = [
		'PERSON',
		'EMAIL',
		'PHONE',
		'ADDRESS',
		'SSN',
		'CREDIT_CARD',
		'DATE_OF_BIRTH',
		'IP_ADDRESS',
		'URL',
		'ORGANIZATION',
		'LOCATION',
		'CUSTOM'
	];

	// Calculate position using the same reliable logic as the old DOM-based approach
	let menuLeft = 0;
	let menuTop = 0;
	let isPositioned = false; // Track if menu has been properly positioned

	// Portal the menu either to KnowledgeBase container or <body>
	function portalToContainer(node: HTMLElement) {
		let target: HTMLElement | null = null;
		if (typeof document !== 'undefined') {
			target = document.getElementById('collection-container');
		}
		const parent = target || document.body;
		if (node && node.parentNode !== parent) {
			parent.appendChild(node);
		}
		return {
			destroy() {
				if (node && node.parentNode) {
					node.parentNode.removeChild(node);
				}
			}
		};
	}

	// Function to calculate position with proper DOM measurements
	const calculatePosition = () => {
		if (!visible || !wordInfo || !menuElement) return;

		// Use mouse coordinates directly - viewport coords from the extension
		const x = wordInfo.x || 0;
		const y = wordInfo.y || 0;

		// Get actual element dimensions - wait for proper rendering
		const rect = menuElement.getBoundingClientRect();
		const hasProperDimensions = rect.width > 0 && rect.height > 0;

		// If element doesn't have proper dimensions yet, use fallback positioning
		const measuredWidth = hasProperDimensions ? rect.width : 250;
		const measuredHeight = hasProperDimensions ? rect.height : 90;

		const kb =
			typeof document !== 'undefined' ? document.getElementById('collection-container') : null;
		if (kb) {
			const kbRect = kb.getBoundingClientRect();
			const desiredLeft = x - measuredWidth / 2 - kbRect.left + kb.scrollLeft;
			const desiredTopBase = y - kbRect.top + kb.scrollTop;
			const spaceBelowOK = y + measuredHeight + 15 <= kbRect.top + kbRect.height - 10;

			menuLeft = Math.max(10, Math.min(desiredLeft, kbRect.width - measuredWidth - 10));
			menuTop = spaceBelowOK ? desiredTopBase + 15 : desiredTopBase - measuredHeight - 10;
			menuTop = Math.max(10, Math.min(menuTop, kbRect.height - measuredHeight - 10));
		} else {
			// Horizontal: center on click, clamp to viewport
			const desiredLeft = x - measuredWidth / 2;
			menuLeft = Math.max(10, Math.min(desiredLeft, window.innerWidth - measuredWidth - 10));
			// Vertical: prefer below the cursor when there is room; else above
			const spaceBelowOK = y + measuredHeight + 15 <= window.innerHeight - 10;
			menuTop = spaceBelowOK ? y + 15 : y - measuredHeight - 10;
			menuTop = Math.max(10, Math.min(menuTop, window.innerHeight - measuredHeight - 10));
		}

		// Mark as positioned if we have proper dimensions
		isPositioned = hasProperDimensions;
	};

	// Reactive positioning with proper timing
	$: if (visible && wordInfo) {
		// Reset positioning state when menu becomes visible
		isPositioned = false;

		// Calculate initial position immediately
		calculatePosition();

		// If we don't have proper dimensions yet, retry after DOM update
		if (!isPositioned) {
			// Use tick() to wait for DOM update, then requestAnimationFrame for layout
			tick().then(() => {
				requestAnimationFrame(() => {
					calculatePosition();
					// If still not positioned, try one more time after a short delay
					if (!isPositioned) {
						setTimeout(() => {
							calculatePosition();
						}, 10);
					}
				});
			});
		}
	}

	$: if (visible && currentLabel) {
		label = currentLabel.toUpperCase();
		isDefaultValue = false;
	}

	// Auto-completion logic
	const findBestMatch = (input: string, options: string[]): string | null => {
		const upperInput = input.toUpperCase();
		return options.find((option) => option.startsWith(upperInput)) || null;
	};

	// Event handlers
	const handleIgnore = () => {
		dispatch('ignore');
	};

	const handleMask = () => {
		const piiType = isDefaultValue ? 'CUSTOM' : label.trim().toUpperCase();
		if (piiType) {
			dispatch('mask', { label: piiType });
		}
	};

	const handleRemoveModifier = (modifierId: string) => {
		dispatch('removeModifier', { modifierId });
	};

	const handleInputFocus = (e: Event) => {
		e.stopPropagation();
		dispatch('inputFocused', { focused: true });

		if (isDefaultValue) {
			label = '';
			isDefaultValue = false;
		}
	};

	const handleInputBlur = () => {
		dispatch('inputFocused', { focused: false });

		if (label.trim() === '') {
			label = 'CUSTOM';
			isDefaultValue = true;
		}
	};

	const handleInput = (e: Event) => {
		e.stopPropagation();

		if (skipAutocompletion) {
			skipAutocompletion = false;
			return;
		}

		if (!isDefaultValue && label) {
			const bestMatch = findBestMatch(label, PREDEFINED_LABELS);

			if (bestMatch && bestMatch !== label.toUpperCase()) {
				const cursorPos = labelInput.selectionStart || 0;
				label = bestMatch;

				// Set selection after DOM update
				setTimeout(() => {
					labelInput.setSelectionRange(cursorPos, bestMatch.length);
				}, 0);
			}
		}
	};

	const handleKeydown = (e: KeyboardEvent) => {
		e.stopPropagation();

		if (e.key === 'Enter') {
			e.preventDefault();
			handleMask();
		} else if (e.key === 'Tab') {
			e.preventDefault();
			if (labelInput) {
				labelInput.setSelectionRange(label.length, label.length);
			}
		} else if (e.key === 'Escape') {
			e.preventDefault();
			dispatch('close');
		} else if (e.key === 'Backspace') {
			skipAutocompletion = true;
		}
	};

	const handleKeyup = (e: KeyboardEvent) => {
		e.stopPropagation();
	};

	const handleMouseEnter = () => {
		dispatch('mouseEnter');
	};

	const handleMouseLeave = (e: MouseEvent) => {
		const relatedTarget = e.relatedTarget as HTMLElement;
		if (relatedTarget && menuElement?.contains(relatedTarget)) {
			return;
		}
		dispatch('mouseLeave');
	};

	const handleHelpClick = (e: MouseEvent) => {
		e.stopPropagation();
		window.open('https://help.nenna.ai/', '_blank', 'noopener,noreferrer');
	};

	onMount(() => {
		// Focus input if it exists
		// Direct focus removed to avoid scroll jumps; use focusInputSoon with preventScroll

		if (currentLabel && typeof currentLabel === 'string') {
			label = currentLabel.toUpperCase();
			isDefaultValue = false;
		}
		focusInputSoon();
	});

	$: if (visible) {
		focusInputSoon();
	}
</script>

{#if visible}
	<div
		bind:this={menuElement}
		use:portalToContainer
		class="min-w-[220px] max-w-[300px] bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3 z-[2147483600] pointer-events-auto"
		style="left: {menuLeft}px; top: {menuTop}px; position: {document.getElementById(
			'collection-container'
		)
			? 'absolute'
			: 'fixed'}; opacity: {isPositioned ? '1' : '0'}; transition: opacity 0.1s ease-in-out;"
		role="dialog"
		aria-label="PII Modifier Menu"
		on:mouseenter|capture={handleMouseEnter}
		on:mouseleave|capture={handleMouseLeave}
		on:mousedown|stopPropagation
		on:mouseup|stopPropagation
		on:click|stopPropagation
		on:pointerdown|stopPropagation
		on:wheel|capture|stopPropagation
		on:touchstart|stopPropagation
	>
		<!-- Help Icon -->
		<button
			class="absolute top-2 right-2 w-4 h-4 bg-amber-400 hover:bg-amber-500 text-gray-800 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-200 hover:scale-110"
			on:click|stopPropagation={(e) => {
				e.preventDefault();
				const a = document.createElement('a');
				a.href = 'https://help.nenna.ai/';
				a.target = '_blank';
				a.rel = 'noopener noreferrer';
				document.body.appendChild(a);
				a.click();
				document.body.removeChild(a);
			}}
			title="Help & Documentation"
		>
			?
		</button>

		<!-- Existing Modifiers Section -->
		{#if existingModifiers.length > 0}
			<div
				class="mb-3 p-2 bg-gray-100 dark:bg-gray-700 rounded border border-gray-200 dark:border-gray-600"
			>
				<div class="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
					Current Modifiers
				</div>

				{#each existingModifiers as modifier}
					<div
						class="flex justify-between items-center p-1.5 mb-1 bg-white dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-600"
					>
						<span class="text-xs text-gray-600 dark:text-gray-400 flex-1 flex items-center gap-1.5">
							{#if modifier.action === 'ignore'}
								<!-- subtle ban icon -->
								<svg
									width="14"
									height="14"
									viewBox="0 0 20 20"
									fill="none"
									xmlns="http://www.w3.org/2000/svg"
									class="text-gray-600 dark:text-gray-300"
								>
									<path
										d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16Z"
										stroke="currentColor"
										stroke-width="1.5"
									/>
									<path d="M5 15 15 5" stroke="currentColor" stroke-width="1.5" />
								</svg>
								Ignore
							{:else}
								<!-- subtle tag icon -->
								<svg
									width="14"
									height="14"
									viewBox="0 0 20 20"
									fill="none"
									xmlns="http://www.w3.org/2000/svg"
									class="text-gray-600 dark:text-gray-300"
								>
									<path
										d="M7.5 3h4.086a2 2 0 0 1 1.414.586l3.414 3.414a2 2 0 0 1 0 2.828l-6.5 6.5a2 2 0 0 1-2.828 0L3.086 13.5a2 2 0 0 1-.586-1.414V8.999"
										stroke="currentColor"
										stroke-width="1.5"
									/>
									<circle cx="13.5" cy="6.5" r="1" fill="currentColor" />
								</svg>
								{modifier.type}
							{/if}
						</span>

						<Tooltip placement="top" content="Remove modifier" className="z-[10010]">
							<button
								class="w-4 h-4 rounded text-xs flex items-center justify-center transition-colors ml-2 text-gray-600 hover:text-red-600 dark:text-gray-300 dark:hover:text-red-400"
								on:click={() => handleRemoveModifier(modifier.id)}
								aria-label="Remove modifier"
							>
								<svg
									width="12"
									height="12"
									viewBox="0 0 20 20"
									fill="none"
									xmlns="http://www.w3.org/2000/svg"
								>
									<path
										d="M6 6l8 8M14 6l-8 8"
										stroke="currentColor"
										stroke-width="1.75"
										stroke-linecap="round"
									/>
								</svg>
							</button>
						</Tooltip>
					</div>
				{/each}
			</div>
		{/if}

		<!-- Action Buttons Container (FormattingButtons style) -->
		<div
			class="flex items-center gap-1 p-0.5 rounded-lg shadow-sm bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600"
		>
			{#if showIgnoreButton}
				<Tooltip placement="top" content="Ignore PII" className="z-[10010]">
					<button
						class="hover:bg-gray-100 dark:hover:bg-gray-600 rounded-lg p-1.5 transition-all text-gray-600 dark:text-gray-300"
						on:pointerup|capture|stopPropagation={handleIgnore}
						on:click|stopPropagation
						type="button"
						aria-label="Ignore PII"
					>
						<svg
							width="16"
							height="16"
							viewBox="0 0 20 20"
							fill="none"
							xmlns="http://www.w3.org/2000/svg"
						>
							<path
								d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16Z"
								stroke="currentColor"
								stroke-width="1.5"
							/>
							<path d="M5 15 15 5" stroke="currentColor" stroke-width="1.5" />
						</svg>
					</button>
				</Tooltip>
			{/if}

			{#if showTextField}
				<input
					bind:this={labelInput}
					bind:value={label}
					type="text"
					class="px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 focus:border-amber-400 focus:ring-1 focus:ring-amber-400 focus:outline-none w-36"
					class:text-gray-400={isDefaultValue}
					placeholder="Label (e.g., PERSON)"
					autofocus
					on:focus={handleInputFocus}
					on:blur={handleInputBlur}
					on:input={handleInput}
					on:keydown={handleKeydown}
					on:keyup={handleKeyup}
				/>

				<Tooltip placement="top" content="Apply label" className="z-[10010]">
					<button
						class="hover:bg-gray-100 dark:hover:bg-gray-600 rounded-lg p-1.5 transition-all text-gray-600 dark:text-gray-300"
						on:pointerup|capture|stopPropagation={handleMask}
						on:click|stopPropagation
						type="button"
						aria-label="Apply label"
					>
						<svg
							width="16"
							height="16"
							viewBox="0 0 20 20"
							fill="none"
							xmlns="http://www.w3.org/2000/svg"
						>
							<path
								d="M5 10l3 3 7-7"
								stroke="currentColor"
								stroke-width="1.75"
								stroke-linecap="round"
								stroke-linejoin="round"
							/>
						</svg>
					</button>
				</Tooltip>
			{/if}
		</div>

		<!-- Removed vertical label section and big Apply Mask button -->
	</div>
{/if}

<style>
	/* Ensure proper z-index stacking */
	:global(.pii-hover-menu) {
		z-index: 10001 !important;
	}
</style>
