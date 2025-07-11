import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from 'prosemirror-state';
import { Decoration, DecorationSet } from 'prosemirror-view';
import type { ExtendedPiiEntity } from '$lib/utils/pii';
import { PiiSessionManager, mapPlainTextPositionToProseMirror } from '$lib/utils/pii';

export interface PiiHighlighterOptions {
	piiEntities: ExtendedPiiEntity[];
	highlightClass: string;
	editorHtml?: string;
	onHover?: (entity: ExtendedPiiEntity, position: { x: number; y: number }) => void;
	onHoverEnd?: () => void;
}

export const PiiHighlighter = Extension.create<PiiHighlighterOptions>({
	name: 'piiHighlighter',

	addOptions() {
		return {
			piiEntities: [],
			highlightClass: 'pii-highlight',
			editorHtml: undefined,
			onHover: undefined,
			onHoverEnd: undefined
		};
	},

	addProseMirrorPlugins() {
		const options = this.options;

		return [
			new Plugin({
				key: new PluginKey('piiHighlighter'),
				state: {
					init() {
						return DecorationSet.empty;
					},
					apply: (tr, decorationSet) => {
						// Map decorations through document changes
						decorationSet = decorationSet.map(tr.mapping, tr.doc);

						// Update decorations based on current PII entities
						const decorations: Decoration[] = [];
						const { piiEntities, highlightClass, editorHtml } = options;

						piiEntities.forEach((entity) => {
							entity.occurrences.forEach((occurrence, occurrenceIndex) => {
								let from: number;
								let to: number;

								if (editorHtml) {
									// Use position mapping to account for br tags and other structural elements
									from = mapPlainTextPositionToProseMirror(occurrence.start_idx, editorHtml);
									to = mapPlainTextPositionToProseMirror(occurrence.end_idx, editorHtml);
								} else {
									// Fallback to old method with simple offset
									from = occurrence.start_idx + 1;
									to = occurrence.end_idx + 1;
								}

								// Ensure the range is valid for the current document
								if (from >= 1 && to <= tr.doc.content.size && from < to) {
									const shouldMask = entity.shouldMask ?? true;
									const maskingClass = shouldMask ? 'pii-masked' : 'pii-unmasked';

									decorations.push(
										Decoration.inline(from, to, {
											class: `${highlightClass} ${maskingClass}`,
											'data-pii-type': entity.type,
											'data-pii-label': entity.label,
											'data-pii-text': entity.raw_text,
											'data-pii-occurrence': occurrenceIndex.toString(),
											'data-should-mask': shouldMask.toString(),
											'data-entity-index': piiEntities.indexOf(entity).toString()
										})
									);
								}
							});
						});

						return DecorationSet.create(tr.doc, decorations);
					}
				},
				props: {
					decorations(state) {
						return this.getState(state);
					},
					handleClick: (view, pos, event) => {
						const target = event.target as HTMLElement;
						if (target.classList.contains('pii-highlight')) {
							const entityLabel = target.getAttribute('data-pii-label');
							const occurrenceIndex = parseInt(target.getAttribute('data-pii-occurrence') || '0');

							if (entityLabel) {
								const piiSessionManager = PiiSessionManager.getInstance();
								piiSessionManager.toggleEntityMasking(entityLabel, occurrenceIndex);

								// Force a re-render by dispatching a transaction
								const tr = view.state.tr.setMeta('piiHighlighter', {
									entities: piiSessionManager.getEntitiesForDisplay()
								});
								view.dispatch(tr);

								event.preventDefault();
								return true;
							}
						}
						return false;
					},
					handleDOMEvents: {
						mouseover: (view, event) => {
							const target = event.target as HTMLElement;

							// Find the PII element - could be the target itself or need to traverse up
							let piiElement: HTMLElement | null = null;

							if (target.classList.contains('pii-highlight')) {
								piiElement = target;
							} else {
								// Check if we're inside a PII element by traversing up
								let current = target.parentElement;
								while (current && current !== view.dom) {
									if (current.classList.contains('pii-highlight')) {
										piiElement = current;
										break;
									}
									current = current.parentElement;
								}
							}

							if (piiElement) {
								const entityIndex = parseInt(piiElement.getAttribute('data-entity-index') || '0');
								const { piiEntities, onHover } = options;

								if (onHover && piiEntities[entityIndex]) {
									const rect = piiElement.getBoundingClientRect();
									const position = {
										x: rect.left + rect.width / 2,
										y: rect.top
									};
									onHover(piiEntities[entityIndex], position);
								}
								return true; // Prevent further event handling
							}
							return false;
						},
						mouseout: (view, event) => {
							const target = event.target as HTMLElement;
							const relatedTarget = event.relatedTarget as HTMLElement;

							// Find if we're leaving a PII element
							let leavingPiiElement = false;

							if (target.classList.contains('pii-highlight')) {
								// Check if we're moving to a non-PII element
								if (!relatedTarget || !relatedTarget.classList.contains('pii-highlight')) {
									leavingPiiElement = true;
								}
							}

							if (leavingPiiElement) {
								const { onHoverEnd } = options;
								if (onHoverEnd) {
									// Longer delay to allow mouse movement to overlay
									setTimeout(onHoverEnd, 200);
								}
							}
							return false;
						}
					}
				}
			})
		];
	},

	addCommands() {
		const self = this;
		return {
			updatePiiEntities:
				(entities: ExtendedPiiEntity[], editorHtml?: string) =>
				({ tr, dispatch }: any) => {
					if (dispatch) {
						// Update the options with new entities and editor HTML
						self.options.piiEntities = entities;
						if (editorHtml) {
							self.options.editorHtml = editorHtml;
						}
						// Force a state update to refresh decorations
						dispatch(tr.setMeta('piiHighlighter', { entities, editorHtml }));
					}
					return true;
				}
		} as any;
	}
});
