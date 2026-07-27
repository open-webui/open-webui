<script lang="ts">
	import { flyAndScale } from '$lib/utils/transitions';
	import { tick } from 'svelte';

	/** Whether the dropdown is open */
	export let show = false;

	/** Side to open on: 'bottom' | 'top' */
	export let side = 'bottom';

	/** Alignment: 'start' | 'end' */
	export let align = 'start';

	/** Close when clicking outside */
	export let closeOnOutsideClick = true;

	/** Called when open/close state changes */
	export let onOpenChange: (state: boolean) => void = () => {};

	/** CSS classes for the dropdown content container */
	export let contentClass = '';

	/** Max height for the dropdown content */
	export let maxHeight = 'min(32rem, calc(100dvh - 2rem))';

	/** Side offset in px */
	export let sideOffset = 4;

	/** Position against the visual viewport, e.g. when the mobile keyboard is open */
	export let visualViewportAware = false;

	let triggerEl: HTMLElement | null = null;
	let contentEl: HTMLElement | null = null;
	let previouslyFocused: HTMLElement | null = null;
	let shouldFocusContent = false;
	let positionFrame: number | undefined;
	let settleTimers: number[] = [];
	let resolvedMaxHeight = maxHeight;
	let lastContentHeight = 0;

	/** Svelte action: moves the node to document.body and keeps it positioned as it resizes */
	function portal(node: HTMLElement) {
		document.body.appendChild(node);

		// Content can grow after the dropdown is positioned - a submenu is opened, or an
		// async list finishes loading - which would otherwise leave it overflowing the
		// viewport. Compare scrollHeight (the natural content height) so that clamping
		// max-height here cannot feed back into another reposition.
		const resizeObserver = new ResizeObserver(() => {
			if (node.scrollHeight === lastContentHeight) return;
			lastContentHeight = node.scrollHeight;
			schedulePositionUpdate();
		});
		resizeObserver.observe(node);

		return {
			destroy() {
				resizeObserver.disconnect();
				lastContentHeight = 0;
				if (node.parentNode) {
					node.parentNode.removeChild(node);
				}
			}
		};
	}

	/** Svelte action: captures the first child element as the trigger reference */
	function trigger(node: HTMLElement) {
		triggerEl = (node.firstElementChild as HTMLElement | null) || node;
		function handleClick(e: MouseEvent) {
			e.preventDefault();
			toggleOpen();
		}
		function handleKeydown(e: KeyboardEvent) {
			if (e.key === 'Enter' || e.key === ' ') {
				e.preventDefault();
				toggleOpen();
			}
		}
		node.addEventListener('click', handleClick);
		node.addEventListener('keydown', handleKeydown);
		return {
			destroy() {
				node.removeEventListener('click', handleClick);
				node.removeEventListener('keydown', handleKeydown);
			}
		};
	}

	/**
	 * Height the content wants, independent of any max-height already applied here.
	 * Measuring offsetHeight alone would feed the previous clamp back into the next
	 * calculation, so the dropdown could flip between clamped and unclamped on every
	 * repositioning pass.
	 */
	function naturalContentHeight() {
		if (!contentEl) return 0;
		return Math.max(contentEl.scrollHeight || 0, contentEl.offsetHeight || 0);
	}

	function visualViewportRect() {
		const viewport = window.visualViewport;
		return {
			left: viewport?.offsetLeft ?? 0,
			top: viewport?.offsetTop ?? 0,
			width: viewport?.width ?? window.innerWidth,
			height: viewport?.height ?? window.innerHeight
		};
	}

	function positionContentDefault() {
		if (!triggerEl || !contentEl) return;
		const rect = triggerEl.getBoundingClientRect();
		resolvedMaxHeight = maxHeight;

		contentEl.style.position = 'fixed';
		contentEl.style.zIndex = '9999';

		const contentHeight = naturalContentHeight();
		const spaceBelow = window.innerHeight - rect.bottom - sideOffset;
		const spaceAbove = rect.top - sideOffset;

		// Auto-flip: prefer the requested side, but flip if not enough space
		let openAbove = side === 'top';
		if (side === 'bottom' && spaceBelow < contentHeight && spaceAbove > spaceBelow) {
			openAbove = true;
		} else if (side === 'top' && spaceAbove < contentHeight && spaceBelow > spaceAbove) {
			openAbove = false;
		}

		if (openAbove) {
			contentEl.style.bottom = `${window.innerHeight - rect.top + sideOffset}px`;
			contentEl.style.top = 'auto';
		} else {
			contentEl.style.top = `${rect.bottom + sideOffset}px`;
			contentEl.style.bottom = 'auto';
		}

		if (align === 'end') {
			let right = window.innerWidth - rect.right;
			// Shift if overflowing left edge
			const contentWidth = contentEl.offsetWidth || 0;
			if (right + contentWidth > window.innerWidth) {
				right = window.innerWidth - contentWidth - 16;
			}
			contentEl.style.right = `${Math.max(16, right)}px`;
			contentEl.style.left = 'auto';
		} else {
			let left = rect.left;
			// Shift if overflowing right edge
			const contentWidth = contentEl.offsetWidth || 0;
			if (left + contentWidth + 16 > window.innerWidth) {
				left = window.innerWidth - contentWidth - 16;
			}
			contentEl.style.left = `${Math.max(16, left)}px`;
			contentEl.style.right = 'auto';
		}
	}

	function positionContentVisualViewport() {
		if (!triggerEl || !contentEl) return;
		const rect = triggerEl.getBoundingClientRect();
		const viewport = visualViewportRect();
		const viewportRight = viewport.left + viewport.width;
		const viewportBottom = viewport.top + viewport.height;
		const pad = 8;

		contentEl.style.position = 'fixed';
		contentEl.style.zIndex = '9999';

		const contentHeight = naturalContentHeight();
		const spaceBelow = viewportBottom - rect.bottom - sideOffset - pad;
		const spaceAbove = rect.top - viewport.top - sideOffset - pad;

		// Auto-flip: prefer the requested side, but flip if not enough space
		let openAbove = side === 'top';
		if (side === 'bottom' && spaceBelow < contentHeight && spaceAbove > spaceBelow) {
			openAbove = true;
		} else if (side === 'top' && spaceAbove < contentHeight && spaceBelow > spaceAbove) {
			openAbove = false;
		}

		const availableHeight = Math.max(0, openAbove ? spaceAbove : spaceBelow);
		const constrainedHeight = contentHeight
			? Math.min(contentHeight, availableHeight)
			: contentHeight;
		const preferredTop = openAbove
			? rect.top - constrainedHeight - sideOffset
			: rect.bottom + sideOffset;
		const contentWidth = contentEl.offsetWidth || 0;
		const preferredLeft = align === 'end' && contentWidth ? rect.right - contentWidth : rect.left;
		const maxLeft = contentWidth ? viewportRight - contentWidth - pad : preferredLeft;

		contentEl.style.top = `${Math.max(
			viewport.top + pad,
			Math.min(preferredTop, viewportBottom - pad - constrainedHeight)
		)}px`;
		contentEl.style.bottom = 'auto';
		contentEl.style.left = `${Math.max(viewport.left + pad, Math.min(preferredLeft, maxLeft))}px`;
		contentEl.style.right = 'auto';
		resolvedMaxHeight =
			contentHeight > availableHeight ? `min(${maxHeight}, ${availableHeight}px)` : maxHeight;
		contentEl.style.maxHeight = resolvedMaxHeight;
	}

	function positionContent() {
		if (visualViewportAware) {
			positionContentVisualViewport();
		} else {
			positionContentDefault();
		}
	}

	function schedulePositionUpdate() {
		if (positionFrame != null) cancelAnimationFrame(positionFrame);
		positionFrame = requestAnimationFrame(() => {
			positionFrame = undefined;
			positionContent();
		});
	}

	function scheduleSettledPositionUpdates() {
		for (const timer of settleTimers) window.clearTimeout(timer);
		settleTimers = [];
		schedulePositionUpdate();
		for (const delay of [50, 150, 300]) {
			settleTimers.push(window.setTimeout(schedulePositionUpdate, delay));
		}
	}

	async function afterOpen() {
		await tick();
		positionContent();

		// Re-check after transition renders real dimensions
		if (visualViewportAware) {
			scheduleSettledPositionUpdates();
		} else {
			setTimeout(positionContent, 50);
		}

		if (shouldFocusContent) {
			shouldFocusContent = false;
			contentEl?.focus();
		}
	}

	function openDropdown(focusContent = false) {
		if (show) return;
		if (focusContent) {
			previouslyFocused =
				document.activeElement instanceof HTMLElement ? document.activeElement : null;
			shouldFocusContent = true;
		}
		show = true;
		onOpenChange(true);
	}

	function closeDropdown(restoreFocus = !!contentEl?.contains(document.activeElement)) {
		if (!show) return;
		show = false;
		onOpenChange(false);
		shouldFocusContent = false;

		if (restoreFocus && previouslyFocused?.isConnected) {
			previouslyFocused.focus();
		}
		previouslyFocused = null;
	}

	function toggleOpen() {
		if (show) {
			closeDropdown();
		} else {
			openDropdown(true);
		}
	}

	// React to external show changes (e.g. bind:show toggled by parent component)
	$: if (show) {
		afterOpen();
	}

	function handleWindowPointerDown(event: PointerEvent) {
		if (!show || !closeOnOutsideClick) return;
		if (!(event.target instanceof Node)) return;
		if (triggerEl?.contains(event.target)) return;
		if (contentEl?.contains(event.target)) return;
		closeDropdown(false);
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape' && show) {
			closeDropdown();
		}
	}

	/** Close the dropdown programmatically */
	export function close() {
		closeDropdown();
	}

	import { onMount, onDestroy } from 'svelte';

	let onPointerDown: ((e: PointerEvent) => void) | undefined;
	onMount(() => {
		onPointerDown = (e) => handleWindowPointerDown(e);
		document.addEventListener('pointerdown', onPointerDown, true);
		if (visualViewportAware) {
			window.visualViewport?.addEventListener('resize', scheduleSettledPositionUpdates);
			window.visualViewport?.addEventListener('scroll', schedulePositionUpdate);
		}
	});
	onDestroy(() => {
		if (positionFrame != null) cancelAnimationFrame(positionFrame);
		for (const timer of settleTimers) window.clearTimeout(timer);
		if (onPointerDown) {
			document.removeEventListener('pointerdown', onPointerDown, true);
		}
		if (visualViewportAware) {
			window.visualViewport?.removeEventListener('resize', scheduleSettledPositionUpdates);
			window.visualViewport?.removeEventListener('scroll', schedulePositionUpdate);
		}
	});
</script>

<svelte:window
	on:keydown={handleKeydown}
	on:scroll|capture={positionContent}
	on:resize={positionContent}
/>

<span
	use:trigger
	style="display: contents; cursor: pointer;"
	role="button"
	aria-haspopup="true"
	aria-expanded={show}
>
	<slot />
</span>

{#if show}
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<div
		use:portal
		bind:this={contentEl}
		class={contentClass}
		role="menu"
		tabindex="-1"
		style:max-height={resolvedMaxHeight}
		style:overflow-y="auto"
		transition:flyAndScale
		on:click={(e) => e.stopPropagation()}
		on:pointerdown={(e) => e.stopPropagation()}
	>
		<slot name="content" />
	</div>
{/if}
