<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { tick, getContext, onMount, createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	import { settings, mobile } from '$lib/stores';
	import { copyToClipboard } from '$lib/utils';

	import MultiResponseMessages from './MultiResponseMessages.svelte';
	import ResponseMessage from './ResponseMessage.svelte';
	import UserMessage from './UserMessage.svelte';

	// Resizable bubble state - SIMPLIFIED
	let isResizing = false;
	let bubbleWidth = 'auto';
	let bubbleElement;
	let showResizeHandle = false;
	let isInitialRender = true;

	// STRICT WIDTH SYSTEM - NO REACTIVE CALCULATIONS
	// Evaluate once and never change
	let isUserMessage = false;
	let minWidth = 400;
	let maxWidth = 900;
	// FIXED WIDTH - never changes automatically
	const defaultWidth = '1152px'; // Always use prompt width

	// Disable resize functionality on mobile
	$: enableResize = !$mobile;

	// Clean initialization without logging

	// STRICT initialization - set everything once and never change automatically
	onMount(() => {
		// Set message type and constraints ONCE
		isUserMessage = history.messages[messageId]?.role === 'user';
		minWidth = isUserMessage ? 300 : 400;
		maxWidth = isUserMessage ? 800 : 900;

		// Load saved width - STRICT
		const savedKey = isUserMessage ? 'userBubbleWidth' : 'llmBubbleWidth';
		const savedWidth = localStorage.getItem(savedKey);

		if (savedWidth && savedWidth !== 'auto') {
			bubbleWidth = savedWidth;
		} else {
			// FIXED default width - never changes
			bubbleWidth = defaultWidth;
		}

		// Apply STRICT CSS immediately and LOCK IT
		setTimeout(() => {
			if (bubbleElement) {
				bubbleElement.style.width = bubbleWidth;
				bubbleElement.style.maxWidth = bubbleWidth;
				bubbleElement.style.minWidth = `${minWidth}px`;
				// PREVENT any future automatic changes
				bubbleElement.style.setProperty('width', bubbleWidth, 'important');
				bubbleElement.style.setProperty('max-width', bubbleWidth, 'important');
			}
			isInitialRender = false;
		}, 50);
	});

	const handleResizeStart = (e) => {
		isResizing = true;
		e.preventDefault();

		const startX = e.clientX;
		const startWidth = bubbleElement.offsetWidth;

		// Disable transitions during resize for instant feedback
		bubbleElement.style.transition = 'none';

		const handleMouseMove = (e) => {
			if (!isResizing) return;

			// Use requestAnimationFrame for smooth 60fps updates
			requestAnimationFrame(() => {
				const deltaX = e.clientX - startX;
				// For user messages with left handle, dragging left increases width (reverse deltaX)
				// For LLM messages with right handle, dragging right increases width (normal deltaX)
				const adjustedDeltaX = isUserMessage ? -deltaX : deltaX;

				// STRICT resize with fixed constraints
				const newWidth = Math.max(minWidth, Math.min(maxWidth, startWidth + adjustedDeltaX));
				const newWidthPx = `${newWidth}px`;

				// Update width directly with STRICT CSS
				bubbleElement.style.setProperty('width', newWidthPx, 'important');
				bubbleElement.style.setProperty('max-width', newWidthPx, 'important');
				bubbleElement.style.setProperty('min-width', `${minWidth}px`, 'important');

				// Update reactive variable
				bubbleWidth = newWidthPx;
			});
		};

		const handleMouseUp = () => {
			isResizing = false;

			// Re-enable transitions
			bubbleElement.style.transition = '';

			// STRICT save to localStorage
			const savedKey = isUserMessage ? 'userBubbleWidth' : 'llmBubbleWidth';
			localStorage.setItem(savedKey, bubbleWidth);

			// LOCK the final width with !important
			bubbleElement.style.setProperty('width', bubbleWidth, 'important');
			bubbleElement.style.setProperty('max-width', bubbleWidth, 'important');

			document.removeEventListener('mousemove', handleMouseMove);
			document.removeEventListener('mouseup', handleMouseUp);
		};

		document.addEventListener('mousemove', handleMouseMove);
		document.addEventListener('mouseup', handleMouseUp);
	};

	const resetWidth = () => {
		// STRICT reset to default width
		bubbleWidth = defaultWidth;
		const savedKey = isUserMessage ? 'userBubbleWidth' : 'llmBubbleWidth';
		localStorage.setItem(savedKey, defaultWidth);

		// Apply STRICT CSS with !important to LOCK it
		if (bubbleElement) {
			bubbleElement.style.setProperty('width', bubbleWidth, 'important');
			bubbleElement.style.setProperty('max-width', bubbleWidth, 'important');
			bubbleElement.style.setProperty('min-width', `${minWidth}px`, 'important');
		}
	};

	// Cleanup not needed anymore

	export let chatId;
	export let selectedModels = [];
	export let idx = 0;

	export let history;
	export let messageId;

	export let user;

	export let setInputText: Function = () => {};
	export let gotoMessage;
	export let showPreviousMessage;
	export let showNextMessage;
	export let updateChat;

	export let editMessage;
	export let saveMessage;
	export let deleteMessage;
	export let rateMessage;
	export let actionMessage;
	export let submitMessage;

	export let regenerateResponse;
	export let continueResponse;
	export let mergeResponses;

	export let addMessages;
	export let triggerScroll;
	export let readOnly = false;
	export let topPadding = false;
</script>

<div
	class="{($settings?.widescreenMode ?? null) ? 'max-w-full' : 'max-w-6xl'} {$mobile
		? 'px-1'
		: 'px-2.5'} mx-auto"
>
	<div
		bind:this={bubbleElement}
		data-message-bubble
		class="relative flex flex-col justify-between {$mobile
			? 'px-2'
			: 'px-5'} mb-3 w-full {enableResize && isUserMessage
			? 'ml-auto'
			: enableResize && !isUserMessage
				? 'mr-auto'
				: ''} rounded-lg group {isResizing
			? 'select-none'
			: !isInitialRender
				? 'transition-all duration-300 ease-in-out'
				: ''} overflow-hidden"
		style="
			min-height: 60px !important; 
			contain: layout !important; 
			overflow-wrap: break-word !important;
			word-break: break-word !important;
			width: {bubbleWidth} !important;
			max-width: {bubbleWidth} !important;
			min-width: {minWidth}px !important;
			height: auto !important;
		"
		on:mouseenter={() => enableResize && (showResizeHandle = true)}
		on:mouseleave={() => enableResize && !isResizing && (showResizeHandle = false)}
	>
		{#if history.messages[messageId]}
			{#if history.messages[messageId].role === 'user'}
				<UserMessage
					{user}
					{chatId}
					{history}
					{messageId}
					isFirstMessage={idx === 0}
					siblings={history.messages[messageId].parentId !== null
						? (history.messages[history.messages[messageId].parentId]?.childrenIds ?? [])
						: (Object.values(history.messages)
								.filter((message) => message.parentId === null)
								.map((message) => message.id) ?? [])}
					{gotoMessage}
					{showPreviousMessage}
					{showNextMessage}
					{editMessage}
					{deleteMessage}
					{readOnly}
					{topPadding}
					showResizeHandle={enableResize && showResizeHandle}
					{isResizing}
					handleResizeStart={enableResize ? handleResizeStart : () => {}}
					resetWidth={enableResize ? resetWidth : () => {}}
				/>
			{:else if (history.messages[history.messages[messageId].parentId]?.models?.length ?? 1) === 1}
				<ResponseMessage
					{chatId}
					{history}
					{messageId}
					{selectedModels}
					isLastMessage={messageId === history.currentId}
					siblings={history.messages[history.messages[messageId].parentId]?.childrenIds ?? []}
					{setInputText}
					{gotoMessage}
					{showPreviousMessage}
					{showNextMessage}
					{updateChat}
					{editMessage}
					{saveMessage}
					{rateMessage}
					{actionMessage}
					{submitMessage}
					{deleteMessage}
					{continueResponse}
					{regenerateResponse}
					{addMessages}
					{readOnly}
					{topPadding}
				/>
			{:else}
				<MultiResponseMessages
					bind:history
					{chatId}
					{messageId}
					{selectedModels}
					isLastMessage={messageId === history?.currentId}
					{setInputText}
					{updateChat}
					{editMessage}
					{saveMessage}
					{rateMessage}
					{actionMessage}
					{submitMessage}
					{deleteMessage}
					{continueResponse}
					{regenerateResponse}
					{mergeResponses}
					{triggerScroll}
					{addMessages}
					{readOnly}
					{topPadding}
				/>
			{/if}
		{/if}

		<!-- Resize Handle (only for LLM messages, user messages handle in UserMessage component) -->
		{#if enableResize && !isUserMessage && (showResizeHandle || isResizing)}
			<div
				class="absolute right-0 top-0 bottom-0 w-2 cursor-col-resize opacity-0 hover:opacity-20 bg-blue-500 transition-opacity duration-200 z-10"
				on:mousedown={handleResizeStart}
				on:dblclick={resetWidth}
				title="Drag to resize bubble | Double-click to reset"
			>
				<!-- Resize indicator dots -->
				<div
					class="absolute inset-y-0 left-1/2 transform -translate-x-1/2 flex flex-col justify-center space-y-1"
				>
					<div class="w-0.5 h-0.5 bg-white rounded-full opacity-60"></div>
					<div class="w-0.5 h-0.5 bg-white rounded-full opacity-60"></div>
					<div class="w-0.5 h-0.5 bg-white rounded-full opacity-60"></div>
				</div>
			</div>
		{/if}
	</div>
</div>
