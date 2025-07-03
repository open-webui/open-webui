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
	export let popperOptions = {};
	export let tippyOptions = {};
	export let tooltipID = '';

	let tooltipElement;
	let tooltipInstance;

	const hideOnEsc = {
		name: 'hideOnEsc',
		defaultValue: true,
		fn({ hide }) {
			function onKeyDown(event) {
				if (event.keyCode === 27) {
					hide();
				}
			}

			return {
				onShow() {
					document.addEventListener('keydown', onKeyDown);
				},
				onHide() {
					document.removeEventListener('keydown', onKeyDown);
				}
			};
		}
	};

	$: if (tooltipElement && content) {
		if (tooltipInstance) {
			tooltipInstance.setContent(DOMPurify.sanitize(content));
		} else {
			tooltipInstance = tippy(tooltipElement, {
				appendTo: () => document.body,
				content: DOMPurify.sanitize(content),
				trigger: 'mouseenter focus focusin',
				interactive: true,
				placement: placement,
				aria: {
					content: 'auto',
					expanded: false
				},
				allowHTML: allowHTML,
				touch: touch,
				...(theme !== '' ? { theme } : { theme: 'dark' }),
				arrow: false,
				offset: offset,
				...tippyOptions,
				plugins: [hideOnEsc],
				popperOptions: popperOptions
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

<div bind:this={tooltipElement} class={className}>
	<slot />
</div>
