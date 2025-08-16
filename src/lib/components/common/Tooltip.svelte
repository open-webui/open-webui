<script lang="ts">
	import DOMPurify from 'dompurify';

	import { onDestroy } from 'svelte';

	import tippy from 'tippy.js';

	export let elementId = '';

	export let placement = 'top';
	export let content = `I'm a tooltip!`;
	export let touch = true;
	export let className = 'flex';
	export let theme = '';
	export let offset = [0, 4];
	export let allowHTML = true;
	export let tippyOptions = {};
	export let interactive = false;

	let tooltipElement;
	let tooltipInstance;

	$: if (tooltipElement && (content || elementId)) {
		let tooltipContent = null;

		if (elementId) {
			tooltipContent = document.getElementById(`${elementId}`);
		} else {
			tooltipContent = DOMPurify.sanitize(content);
		}

		if (tooltipInstance) {
			tooltipInstance.setContent(tooltipContent);
		} else {
			if (content) {
				tooltipInstance = tippy(tooltipElement, {
					content: tooltipContent,
					placement: placement,
					allowHTML: allowHTML,
					touch: touch,
					...(theme !== '' ? { theme } : { theme: 'dark' }),
					arrow: false,
					offset: offset,
					...(interactive ? { interactive: true } : {}),
					...tippyOptions
				});
			}
		}
	} else if (tooltipInstance && content === '') {
		if (tooltipInstance) {
			tooltipInstance.destroy();
		}
	}

	onDestroy(() => {
		if (tooltipInstance) {
			tooltipInstance.destroy();
		}
	});
</script>

<div bind:this={tooltipElement} class={className}>
	<slot />
</div>

<slot name="tooltip"></slot>
