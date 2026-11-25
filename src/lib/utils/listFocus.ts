import { tick } from 'svelte';

export function focusIfLost(target: HTMLElement | null | undefined) {
	if (target?.isConnected && target.ownerDocument.activeElement === target.ownerDocument.body) {
		target.focus();
	}
}

export async function withListFocus<T extends string | { id: string }>(
	list: HTMLElement,
	item: T,
	remove: (item: T) => Promise<unknown> | void,
	fallback?: HTMLElement
) {
	const controls = () => Array.from(list.querySelectorAll<HTMLElement>('[data-focus-row]'));
	const ids = controls().map((control) => control.dataset.focusRow);
	const index = ids.indexOf(typeof item === 'string' ? item : item.id);

	await remove(item);
	await tick();
	if (index < 0 || !list.isConnected) return;

	const remaining = controls();
	const byId = new Map(remaining.map((control) => [control.dataset.focusRow, control]));
	const nearest = [...ids.slice(index), ...ids.slice(0, index).reverse()].find((id) =>
		byId.has(id)
	);
	focusIfLost(
		byId.get(nearest) ??
			remaining[0] ??
			fallback ??
			list.querySelector<HTMLElement>('[data-focus-fallback]')
	);
}
