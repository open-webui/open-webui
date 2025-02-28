<script lang="ts">
	import { run } from 'svelte/legacy';

	import DOMPurify from 'dompurify';

	import { onDestroy } from 'svelte';
	import { marked } from 'marked';

	import tippy from 'tippy.js';
	import { roundArrow } from 'tippy.js';

	interface Props {
		placement?: string;
		content?: any;
		touch?: boolean;
		className?: string;
		theme?: string;
		offset?: any;
		allowHTML?: boolean;
		tippyOptions?: any;
		children?: import('svelte').Snippet;
	}

	let {
		placement = 'top',
		content = `I'm a tooltip!`,
		touch = true,
		className = 'flex',
		theme = '',
		offset = [0, 4],
		allowHTML = true,
		tippyOptions = {},
		children
	}: Props = $props();

	let tooltipElement = $state();
	let tooltipInstance = $state();

	run(() => {
		if (tooltipElement && content) {
			if (tooltipInstance) {
				tooltipInstance.setContent(DOMPurify.sanitize(content));
			} else {
				tooltipInstance = tippy(tooltipElement, {
					content: DOMPurify.sanitize(content),
					placement: placement,
					allowHTML: allowHTML,
					touch: touch,
					...(theme !== '' ? { theme } : { theme: 'dark' }),
					arrow: false,
					offset: offset,
					...tippyOptions
				});
			}
		} else if (tooltipInstance && content === '') {
			if (tooltipInstance) {
				tooltipInstance.destroy();
			}
		}
	});

	onDestroy(() => {
		if (tooltipInstance) {
			tooltipInstance.destroy();
		}
	});
</script>

<div bind:this={tooltipElement} class={className} aria-label={DOMPurify.sanitize(content)}>
	{@render children?.()}
</div>
