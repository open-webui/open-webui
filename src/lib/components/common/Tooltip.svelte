<script lang="ts">
	import DOMPurify from 'dompurify';

	import { onDestroy } from 'svelte';

	import tippy, {
		type Instance as TippyInstance,
		type Placement as TippyPlacement,
		type Props as TippyProps
	} from 'tippy.js';

	export let elementId = '';

	export let as = 'div';
	export let className = 'flex';

	export let placement: TippyPlacement = 'top';
	export let content = `I'm a tooltip!`;
	export let touch = true;
	export let theme = '';
	export let offset: TippyProps['offset'] = [0, 4];
	export let allowHTML = true;
	export let tippyOptions: Partial<TippyProps> = {};
	export let interactive = false;

	export let onClick = () => {};

	let tooltipElement: HTMLElement | null = null;
	let tooltipInstance: TippyInstance | null = null;

	function destroyInstance() {
		if (tooltipInstance) {
			tooltipInstance.destroy();
			tooltipInstance = null;
		}
	}

	$: if (tooltipElement && (content || elementId)) {
		let tooltipContent: string | Element | DocumentFragment | null = null;

		if (elementId) {
			tooltipContent = document.getElementById(elementId);
		} else {
			tooltipContent = DOMPurify.sanitize(content);
		}

		// After the element changes, the old instance must be destroyed, otherwise the detached tippy floating DOM will be left behind
		if (tooltipInstance && tooltipInstance.reference !== tooltipElement) {
			destroyInstance();
		}

		if (tooltipInstance) {
			tooltipInstance.setContent(tooltipContent ?? '');
		} else {
			if (content) {
				tooltipInstance = tippy(tooltipElement, {
					content: tooltipContent ?? '',
					placement,
					allowHTML,
					touch,
					...(theme !== '' ? { theme } : { theme: 'dark' }),
					arrow: false,
					offset,
					...(interactive ? { interactive: true } : {}),
					...tippyOptions
				});
			}
		}
	} else if (tooltipInstance && content === '') {
		destroyInstance();
	}

	onDestroy(() => {
		destroyInstance();
	});
</script>

<!-- svelte-ignore a11y-no-static-element-interactions -->
<svelte:element this={as} bind:this={tooltipElement} class={className} on:click={onClick}>
	<slot />
</svelte:element>

<slot name="tooltip"></slot>
