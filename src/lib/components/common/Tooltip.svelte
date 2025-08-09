<script lang="ts">
	import { onDestroy } from 'svelte';
	import tippy from 'tippy.js';
	import DOMPurify from 'dompurify';

	export let placement = 'top';
	export let content = '';
	export let touch = true;
	export let className = 'flex';
	export let theme = '';
	export let offset = [0, 4];
	export let interactive = false;
	export let tippyOptions = {};
	export let allowHTML = true;

	let triggerElement;
	let contentElement;
	let tooltipInstance;

	$: if (triggerElement) {
		let tooltipContentSource = null;

		// Prioritize slotted content
		if (contentElement && contentElement.innerHTML.trim() !== '') {
			tooltipContentSource = contentElement;
		}
		// Fallback to content prop
		else if (content) {
			tooltipContentSource = DOMPurify.sanitize(content);
		}

		// Destroy old instance if it exists
		if (tooltipInstance) {
			tooltipInstance.destroy();
			tooltipInstance = null;
		}

		// Create new instance if we have content
		if (tooltipContentSource) {
			tooltipInstance = tippy(triggerElement, {
				content: tooltipContentSource,
				placement: placement,
				allowHTML: allowHTML,
				touch: touch,
				...(theme !== '' ? { theme } : { theme: 'dark' }),
				arrow: false,
				offset: offset,
				interactive: interactive,
				...tippyOptions
			});
		}
	}

	onDestroy(() => {
		if (tooltipInstance) {
			tooltipInstance.destroy();
		}
	});
</script>

<div bind:this={triggerElement} class={className}>
	<slot />
</div>

<div style="display: none;">
	<div bind:this={contentElement}>
		<slot name="tooltip" />
	</div>
</div>
