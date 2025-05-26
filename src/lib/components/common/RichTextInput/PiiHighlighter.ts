import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from 'prosemirror-state';
import { Decoration, DecorationSet } from 'prosemirror-view';
import type { ExtendedPiiEntity } from '$lib/utils/pii';
import { PiiSessionManager } from '$lib/utils/pii';

export interface PiiHighlighterOptions {
	piiEntities: ExtendedPiiEntity[];
	highlightClass: string;
	onHover?: (entity: ExtendedPiiEntity, position: { x: number, y: number }) => void;
	onHoverEnd?: () => void;
}

export const PiiHighlighter = Extension.create<PiiHighlighterOptions>({
	name: 'piiHighlighter',

	addOptions() {
		return {
			piiEntities: [],
			highlightClass: 'pii-highlight',
			onHover: undefined,
			onHoverEnd: undefined
		};
	},

	addProseMirrorPlugins() {
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
						const { piiEntities, highlightClass } = this.options;

						piiEntities.forEach((entity) => {
							entity.occurrences.forEach((occurrence, occurrenceIndex) => {
								// Add 1 to account for the document structure offset
								const from = occurrence.start_idx + 1;
								const to = occurrence.end_idx + 1;
								
								// Ensure the range is valid for the current document
								if (from >= 1 && to <= tr.doc.content.size && from < to) {
									const shouldMask = entity.shouldMask ?? true;
									const maskingClass = shouldMask ? 'pii-masked' : 'pii-unmasked';
									const statusText = shouldMask ? 'Will be masked' : 'Will NOT be masked';
									
									decorations.push(
										Decoration.inline(from, to, {
											class: `${highlightClass} ${maskingClass}`,
											'data-pii-type': entity.type,
											'data-pii-label': entity.label,
											'data-pii-text': entity.text,
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
									entities: piiSessionManager.getEntities() 
								});
								view.dispatch(tr);
								
								event.preventDefault();
								return true;
							}
						}
						return false;
					},
					handleDOMEvents: {
						mouseenter: (view, event) => {
							const target = event.target as HTMLElement;
							if (target.classList.contains('pii-highlight')) {
								const entityIndex = parseInt(target.getAttribute('data-entity-index') || '0');
								const { piiEntities, onHover } = this.options;
								
								if (onHover && piiEntities[entityIndex]) {
									const rect = target.getBoundingClientRect();
									const position = {
										x: rect.left + rect.width / 2,
										y: rect.top
									};
									onHover(piiEntities[entityIndex], position);
								}
							}
							return false;
						},
						mouseleave: (view, event) => {
							const target = event.target as HTMLElement;
							if (target.classList.contains('pii-highlight')) {
								const { onHoverEnd } = this.options;
								if (onHoverEnd) {
									// Add a small delay to prevent flickering when moving between elements
									setTimeout(onHoverEnd, 100);
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
		return {
			updatePiiEntities: (entities: ExtendedPiiEntity[]) => ({ tr, dispatch }: any) => {
				if (dispatch) {
					// Update the options with new entities
					this.options.piiEntities = entities;
					// Force a state update to refresh decorations
					dispatch(tr.setMeta('piiHighlighter', { entities }));
				}
				return true;
			}
		} as any;
	}
}); 