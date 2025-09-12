import tippy from 'tippy.js';

export function getSuggestionRenderer(Component: any, ComponentProps = {}) {
	return function suggestionRenderer() {
		let component = null;
		let container: HTMLDivElement | null = null;
		let popup: TippyInstance | null = null;

		return {
			onStart: (props: any) => {
				container = document.createElement('div');
				container.className = 'suggestion-list-container';
				document.body.appendChild(container);

				// mount Svelte component
				component = new Component({
					target: container,
					props: {
						char: props?.text,
						command: (item) => {
							props.command({ id: item.id, label: item.label });
						},
						...ComponentProps
					},
					context: new Map<string, any>([['i18n', ComponentProps?.i18n]])
				});

				popup = tippy(document.body, {
					getReferenceClientRect: props.clientRect as any,
					appendTo: () => document.body,
					content: container, // ✅ real element, not Svelte internals
					interactive: true,
					trigger: 'manual',
					theme: 'transparent',
					placement: 'top-start',
					offset: [-10, -2],
					arrow: false
				});
				popup?.show();
			},

			onUpdate: (props: any) => {
				if (!component) return;
				component.$set({ query: props.query });
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

				component?.$destroy();
				component = null;

				if (container?.parentNode) container.parentNode.removeChild(container);
				container = null;
			}
		};
	};
}
