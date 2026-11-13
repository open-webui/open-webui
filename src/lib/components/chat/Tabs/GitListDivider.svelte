<script lang="ts">
	import { getContext } from 'svelte';

	const i18n = getContext<any>('i18n');

	export let width: number;
	export let max: number;
	export let onResize: (width: number) => void;

	let resizing = false;
	let startX = 0;
	let startWidth = 0;
	const clamp = (value: number) => Math.max(160, Math.min(max, value));
</script>

<!-- svelte-ignore a11y_no_noninteractive_tabindex a11y_no_noninteractive_element_interactions -->
<div
	tabindex="0"
	role="separator"
	aria-label={$i18n.t('Resize Git list')}
	aria-orientation="vertical"
	aria-valuemin={160}
	aria-valuemax={max}
	aria-valuenow={Math.round(width)}
	class="relative z-10 hidden w-px shrink-0 @min-[560px]:block touch-none cursor-col-resize border-l border-gray-100/50 dark:border-white/2 hover:border-gray-200 dark:hover:border-gray-800 transition"
	on:pointerdown={(event) => {
		if (event.button !== 0) return;
		event.preventDefault();
		event.currentTarget.setPointerCapture(event.pointerId);
		resizing = true;
		startX = event.clientX;
		startWidth = width;
	}}
	on:pointermove={(event) => {
		if (resizing) onResize(clamp(startWidth + event.clientX - startX));
	}}
	on:pointerup={() => (resizing = false)}
	on:pointercancel={() => (resizing = false)}
	on:lostpointercapture={() => (resizing = false)}
	on:keydown={(event) => {
		if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
			event.preventDefault();
			onResize(
				clamp(
					event.key === 'Home'
						? 160
						: event.key === 'End'
							? max
							: width + (event.key === 'ArrowRight' ? 20 : -20)
				)
			);
		}
	}}
>
	<span class="absolute inset-y-0 -left-1.5 -right-1.5 bg-transparent"></span>
</div>
