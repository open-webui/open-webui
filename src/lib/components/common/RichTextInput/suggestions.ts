import { mount, unmount } from 'svelte';
import { createClassComponent } from 'svelte/legacy';

import tippy, { type Instance as TippyInstance } from 'tippy.js';

interface SuggestionItem {
	id: string;
	label: string;
}

interface ComponentPropsWithI18n {
	i18n?: unknown;
	[key: string]: unknown;
}

interface SvelteClassComponent {
	$set: (props: Record<string, unknown>) => void;
	$destroy: () => void;
	_onKeyDown?: (event: KeyboardEvent) => boolean;
}

export function getSuggestionRenderer(Component: unknown, ComponentProps: ComponentPropsWithI18n = {}) {
	return function suggestionRenderer() {
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		let component: any = null;
		let container: HTMLDivElement | null = null;

		let popup: TippyInstance | null = null;
		let refEl: HTMLDivElement | null = null; // dummy reference

		return {
			onStart: (props: any) => {
				container = document.createElement('div');
				container.className = 'suggestion-list-container';
				document.body.appendChild(container);

				// mount Svelte component
				component = createClassComponent({
					// eslint-disable-next-line @typescript-eslint/no-explicit-any
					component: Component as any,
					target: container,
					props: {
						char: props?.text,
						query: props?.query,
						command: (item: SuggestionItem) => {
							props.command({ id: item.id, label: item.label });
						},
						...ComponentProps
					},
					context: new Map<string, unknown>([['i18n', ComponentProps?.i18n]])
				});

				// Create a tiny reference element so outside taps are truly "outside"
				refEl = document.createElement('div');
				Object.assign(refEl.style, {
					position: 'fixed',
					left: '0px',
					top: '0px',
					width: '0px',
					height: '0px'
				});
				document.body.appendChild(refEl);

				popup = tippy(refEl, {
					getReferenceClientRect: props.clientRect as any,
					appendTo: () => document.body,
					content: container,
					interactive: true,
					trigger: 'manual',
					theme: 'transparent',
					placement: 'top-start',
					offset: [-10, -2],
					arrow: false,
					popperOptions: {
						strategy: 'fixed',
						modifiers: [
							{
								name: 'preventOverflow',
								options: {
									boundary: 'viewport', // keep within the viewport
									altAxis: true, // also prevent overflow on the cross axis (X)
									tether: true,
									padding: 8
								}
							},
							{
								name: 'flip',
								options: {
									boundary: 'viewport',
									fallbackPlacements: ['top-end', 'bottom-start', 'bottom-end']
								}
							},
							// Ensure transforms don’t cause layout widening in some browsers
							{ name: 'computeStyles', options: { adaptive: true } }
						]
					},
					// Helps avoid accidental focus/hover “linking” from far away elements
					interactiveBorder: 8
				});
				popup?.show();
			},

			onUpdate: (props: any) => {
				if (!component) return;

				component.$set({
					query: props.query,
					command: (item: SuggestionItem) => {
						props.command({ id: item.id, label: item.label });
					}
				});

				if (props.clientRect && popup) {
					popup.setProps({ getReferenceClientRect: props.clientRect as any });
				}
			},

			onKeyDown: (props: any) => {
				// forward to the Svelte component’s handler
				// (expose this from component as `export function onKeyDown(evt)`)
				// @ts-ignore
				return component?._onKeyDown?.(props.event) ?? false;
			},

			onExit: () => {
				popup?.destroy();
				popup = null;

				try {
					component.$destroy();
				} catch (e) {
					console.error('Error unmounting component:', e);
				}

				component = null;

				if (container?.parentNode) container.parentNode.removeChild(container);
				container = null;

				if (refEl?.parentNode) refEl.parentNode.removeChild(refEl);
				refEl = null;
			}
		};
	};
}
