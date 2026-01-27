<script lang="ts">
	import DOMPurify from 'dompurify';

	import { onDestroy } from 'svelte';
	import { marked } from 'marked';

	import tippy from 'tippy.js';
	import { roundArrow } from 'tippy.js';

	export let placement = 'top';
	export let content = `I'm a tooltip!`;
	export let touch = true;
	export let className = 'flex';
	export let theme = '';
	export let offset = [0, 4];
	export let allowHTML = true;
	export let tippyOptions = {};

	let tooltipElement: HTMLElement | undefined;
	let tooltipInstance: any;

	$: if (tooltipElement && content) {
		if (tooltipInstance) {
			tooltipInstance.setContent(DOMPurify.sanitize(content));
		} else {
			tooltipInstance = tippy(tooltipElement, {
				content: DOMPurify.sanitize(content),
				placement: placement as any,
				allowHTML: allowHTML,
				touch: touch,
				...(theme !== '' ? { theme } : { theme: 'dark' }),
				arrow: false,
				offset: offset as any,
				...tippyOptions
			});
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

<div bind:this={tooltipElement} aria-label={DOMPurify.sanitize(content)} class={className}>
	<slot />
</div>
