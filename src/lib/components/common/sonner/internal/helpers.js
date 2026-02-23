import { writable } from 'svelte/store';
export function cn(...classes) {
    return classes.filter(Boolean).join(' ');
}
export const isBrowser = typeof document !== 'undefined';
/**
 * A custom store that only allows setting/updating the value from the
 * browser to avoid SSR data leaks. By defining this helper, we don't
 * have to worry about checking for `isBrowser` in every place we
 * mutate the various stores.
 *
 * This should only ever be initialized with an empty array or object,
 * as otherwise the initial value will persist across requests.
 */
export function clientWritable(initialValue) {
    const store = writable(initialValue);
    function set(value) {
        if (isBrowser) {
            store.set(value);
        }
    }
    function update(updater) {
        if (isBrowser) {
            store.update(updater);
        }
    }
    return {
        subscribe: store.subscribe,
        set,
        update
    };
}
