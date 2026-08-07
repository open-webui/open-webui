const CSS_VARIABLE = '--right-pane-width';

let owner: HTMLElement | null = null;

export const trackRightPaneWidth = (el: HTMLElement) => {
	owner = el;

	const publish = (width: number) => {
		if (owner !== el) {
			return;
		}
		document.documentElement.style.setProperty(CSS_VARIABLE, `${width}px`);
	};

	const observer = new ResizeObserver((entries) => {
		for (const entry of entries) {
			publish(entry.borderBoxSize?.[0]?.inlineSize ?? entry.contentRect.width);
		}
	});

	observer.observe(el);
	publish(el.offsetWidth);

	return () => {
		observer.disconnect();

		if (owner === el) {
			owner = null;
			document.documentElement.style.removeProperty(CSS_VARIABLE);
		}
	};
};
