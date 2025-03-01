import { getContext, setContext } from 'svelte';
import createI18nStore from '$lib/i18n';
import type { i18n } from 'i18next';
import { type Readable, type Writable } from 'svelte/store';

const i18nKey = Symbol('user');

export function setI18nContext() {
	setContext(i18nKey, createI18nStore());
}

export function getI18nContext(): Readable<i18n> {
	return getContext(i18nKey);
}
