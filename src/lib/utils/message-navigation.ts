export const isJumpToMessagesShortcut = (event: KeyboardEvent) =>
	event.key === 'ArrowUp' && event.altKey && !event.ctrlKey && !event.metaKey && !event.shiftKey;

export function focusActiveMessage(): boolean {
	const messages = document.querySelectorAll<HTMLElement>('[data-keyboard-message]');
	const target =
		document.querySelector<HTMLElement>('[data-keyboard-message][tabindex="0"]') ??
		messages[messages.length - 1];
	if (!target) return false;
	target.focus();
	return true;
}

export function messageNavigation(node: HTMLElement) {
	let lastFocused: HTMLElement | null = null;
	const controls = () =>
		Array.from(node.querySelectorAll<HTMLButtonElement>('[data-message-actions] button'));
	const availableControls = () =>
		controls().filter((button) => !button.disabled && button.getClientRects().length > 0);

	const syncControls = () => {
		for (const button of controls()) {
			if (button !== document.activeElement) button.tabIndex = -1;
		}
		if (lastFocused && !lastFocused.isConnected && document.activeElement === document.body) {
			node.focus();
		}
	};
	const observer = new MutationObserver(syncControls);
	observer.observe(node, { childList: true, subtree: true });
	syncControls();

	const setCurrentMessage = (message: HTMLElement) => {
		const list = node.parentElement;
		for (const sibling of list?.querySelectorAll<HTMLElement>('[data-keyboard-message]') ?? []) {
			sibling.tabIndex = sibling === message ? 0 : -1;
		}
	};
	const focusMessage = (message: HTMLElement) => {
		setCurrentMessage(message);
		message.focus();
	};
	const focusin = (event: FocusEvent) => {
		if (event.target instanceof HTMLElement) {
			lastFocused = event.target;
			setCurrentMessage(node);
		}
	};
	const focusout = (event: FocusEvent) => {
		if (!(event.relatedTarget instanceof Node) || !node.contains(event.relatedTarget)) {
			for (const button of controls()) button.tabIndex = -1;
		}
	};

	const keydown = (event: KeyboardEvent) => {
		const target = event.target;
		if (!(target instanceof HTMLElement)) return;
		if (target === node) {
			const messages = Array.from(
				node.parentElement?.querySelectorAll<HTMLElement>('[data-keyboard-message]') ?? []
			);
			const index = messages.indexOf(node);
			let next: HTMLElement | undefined;
			if (event.key === 'ArrowDown') next = messages[Math.min(index + 1, messages.length - 1)];
			if (event.key === 'ArrowUp') next = messages[Math.max(index - 1, 0)];
			if (event.key === 'Home') next = messages[0];
			if (event.key === 'End') next = messages.at(-1);
			if (next) {
				event.preventDefault();
				focusMessage(next);
			} else if (event.key === 'Enter') {
				event.preventDefault();
				const button = availableControls()[0];
				if (button) {
					button.tabIndex = 0;
					button.focus();
				}
			}
		} else if (target instanceof HTMLButtonElement && target.closest('[data-message-actions]')) {
			const buttons = availableControls();
			const index = buttons.indexOf(target);
			let next: HTMLButtonElement | undefined;
			if (event.key === 'ArrowRight' || event.key === 'ArrowDown')
				next = buttons[(index + 1) % buttons.length];
			if (event.key === 'ArrowLeft' || event.key === 'ArrowUp')
				next = buttons[(index - 1 + buttons.length) % buttons.length];
			if (event.key === 'Home') next = buttons[0];
			if (event.key === 'End') next = buttons.at(-1);
			if (next) {
				event.preventDefault();
				event.stopPropagation();
				target.tabIndex = -1;
				next.tabIndex = 0;
				next.focus();
			} else if (event.key === 'Escape') {
				event.preventDefault();
				event.stopPropagation();
				target.tabIndex = -1;
				focusMessage(node);
			} else if (event.key === 'Tab') {
				target.tabIndex = -1;
			}
		}
	};

	node.addEventListener('keydown', keydown);
	node.addEventListener('focusin', focusin);
	node.addEventListener('focusout', focusout);
	return {
		destroy() {
			observer.disconnect();
			node.removeEventListener('keydown', keydown);
			node.removeEventListener('focusin', focusin);
			node.removeEventListener('focusout', focusout);
		}
	};
}
