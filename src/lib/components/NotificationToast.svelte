<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { settings, isLastActiveTab } from '$lib/stores';
	import { playNotificationSound } from '$lib/utils/audio';
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';

	import { createEventDispatcher, getContext, onMount } from 'svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n: any = getContext('i18n');

	const dispatch = createEventDispatcher();

	export let onClick: Function = () => {};
	export let title: string = 'HI';
	export let content: string;
	export let playSound = true;

	let startX = 0,
		startY = 0;
	let moved = false;
	let closeButtonElement: HTMLButtonElement;
	const DRAG_THRESHOLD_PX = 6;

	const clickHandler = () => {
		onClick();
		dispatch('closeToast');
	};

	const closeHandler = () => {
		dispatch('closeToast');
	};

	function onPointerDown(e: PointerEvent) {
		startX = e.clientX;
		startY = e.clientY;
		moved = false;
		// Ensure we continue to get events even if the toast moves under the pointer.
		(e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId);
	}

	function onPointerMove(e: PointerEvent) {
		if (moved) return;
		const dx = e.clientX - startX;
		const dy = e.clientY - startY;
		if (dx * dx + dy * dy > DRAG_THRESHOLD_PX * DRAG_THRESHOLD_PX) {
			moved = true;
		}
	}

	function onPointerUp(e: PointerEvent) {
		// Release capture if taken
		(e.currentTarget as HTMLElement).releasePointerCapture?.(e.pointerId);

		// Skip if clicking the close button
		if (
			closeButtonElement &&
			(e.target === closeButtonElement || closeButtonElement.contains(e.target as Node))
		) {
			return;
		}

		// Only treat as a click if there wasn't a drag
		if (!moved) {
			clickHandler();
		}
	}

	onMount(() => {
		if (playSound && ($settings?.notificationSound ?? true) && $isLastActiveTab) {
			void playNotificationSound($settings?.notificationSoundType);
		}
	});
</script>

<div
	role="status"
	aria-live="polite"
	data-toast-custom
	class="flex w-full items-start gap-2.5 rounded-[inherit] p-3 text-left cursor-pointer select-none"
	on:dragstart|preventDefault
	on:pointerdown={onPointerDown}
	on:pointermove={onPointerMove}
	on:pointerup={onPointerUp}
	on:pointercancel={() => (moved = true)}
	on:keydown={(e) => {
		if (e.target !== e.currentTarget) return;
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			clickHandler();
		}
	}}
>
	<div class="-mt-0.5 shrink-0">
		<!-- LICENSE covers this Open WebUI notification logo.
		Do not alter, remove, obscure, or replace it except as LICENSE permits:
		https://docs.openwebui.com/license. -->
		<img src="{WEBUI_BASE_URL}/static/favicon.png" alt="" class="size-6 rounded-full" />
	</div>

	<div class="flex min-w-0 flex-1 flex-col gap-0.5">
		{#if title}
			<div class="line-clamp-1 font-medium text-base-900 dark:text-base-50">{title}</div>
		{/if}

		<div class="line-clamp-2 text-xs text-base-500 dark:text-base-400">
			{@html DOMPurify.sanitize(marked(DOMPurify.sanitize(content, { ALLOWED_TAGS: [] })))}
		</div>
	</div>

	<button
		bind:this={closeButtonElement}
		class="-mr-0.5 flex size-5 shrink-0 items-center justify-center rounded-md text-base-400 transition hover:bg-base-100 hover:text-base-700 dark:text-base-500 dark:hover:bg-base-800 dark:hover:text-base-200"
		on:click|stopPropagation={closeHandler}
		aria-label={$i18n.t('Dismiss notification')}
	>
		<XMark className="size-3.5" />
	</button>
</div>
