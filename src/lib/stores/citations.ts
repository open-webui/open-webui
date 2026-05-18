import { writable } from 'svelte/store';

export interface CitationModalState {
	citation: any | null;
	show: boolean;
	showRelevance: boolean;
	showPercentage: boolean;
}

export const citationModal = writable<CitationModalState>({
	citation: null,
	show: false,
	showRelevance: true,
	showPercentage: false
});

export function openCitation(
	citation: any,
	opts: { showRelevance?: boolean; showPercentage?: boolean } = {}
) {
	citationModal.set({
		citation,
		show: true,
		showRelevance: opts.showRelevance ?? true,
		showPercentage: opts.showPercentage ?? false
	});
}

export function closeCitation() {
	citationModal.update((s) => ({ ...s, show: false }));
}
