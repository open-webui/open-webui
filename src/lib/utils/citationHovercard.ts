import { writable } from 'svelte/store';

export type CitationHovercardOwner = object;

export const activeCitationHovercard = writable<CitationHovercardOwner | null>(null);

export const openCitationHovercard = (owner: CitationHovercardOwner): void => {
	activeCitationHovercard.set(owner);
};

export const closeCitationHovercard = (owner: CitationHovercardOwner): void => {
	activeCitationHovercard.update((activeOwner) => (activeOwner === owner ? null : activeOwner));
};

export const clampCitationIndex = (index: number, count: number): number => {
	if (!Number.isFinite(index) || count <= 0) return 0;
	return Math.min(Math.max(Math.trunc(index), 0), count - 1);
};

export const stepCitationIndex = (index: number, count: number, delta: number): number =>
	clampCitationIndex(index + delta, count);
