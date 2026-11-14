import { getContext, onDestroy } from 'svelte';
import { derived, readable, type Readable, type Writable } from 'svelte/store';
import { page } from '$app/stores';
import { goto } from '$app/navigation';

export type PageContext = {
	url: Writable<URL>;
	active: Readable<boolean>;
	goto: typeof goto;
	setTitle: (title: string) => void;
	beforeLeave: Set<() => boolean | void | Promise<boolean | void>>;
};

export function getPageContext() {
	const tab = getContext<PageContext | undefined>('page');
	return {
		tab,
		active: tab?.active ?? readable(true),
		url: tab?.url ?? derived(page, ($page) => $page.url),
		goto: tab?.goto ?? goto
	};
}

export function onTabLeave(callback: () => boolean | void | Promise<boolean | void>) {
	const { tab } = getPageContext();
	tab?.beforeLeave.add(callback);
	onDestroy(() => tab?.beforeLeave.delete(callback));
}
