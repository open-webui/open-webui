/*
Here we initialize the plugin with keyword mapping.
Intended to handle user interactions seamlessly.

Observe the keydown events for proactive suggestions.
Provide a mechanism for accepting AI suggestions.
Evaluate each input change with debounce logic.
Next, we implement touch and mouse interactions.

Anchor the user experience to intuitive behavior.
Intelligently reset suggestions on new input.
*/

import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from 'prosemirror-state';

export const AIAutocompletion = Extension.create({
	name: 'aiAutocompletion',

	addOptions() {
		return {
			generateCompletion: () => Promise.resolve(''),
			debounceTime: 1000
		};
	},

	addGlobalAttributes() {
		return [
			{
				types: ['paragraph'],
				attributes: {
					class: {
						default: null,
						parseHTML: (element) => element.getAttribute('class'),
						renderHTML: (attributes) => {
							if (!attributes.class) return {};
							return { class: attributes.class };
						}
					},
					'data-prompt': {
						default: null,
						parseHTML: (element) => element.getAttribute('data-prompt'),
						renderHTML: (attributes) => {
							if (!attributes['data-prompt']) return {};
							return { 'data-prompt': attributes['data-prompt'] };
						}
					},
					'data-suggestion': {
						default: null,
						parseHTML: (element) => element.getAttribute('data-suggestion'),
						renderHTML: (attributes) => {
							if (!attributes['data-suggestion']) return {};
							return { 'data-suggestion': attributes['data-suggestion'] };
						}
					}
				}
			}
		];
	},

	addProseMirrorPlugins() {
		let debounceTimer = null;
		let loading = false;

		let touchStartX = 0;
		let touchStartY = 0;

		return [
			new Plugin({
				key: new PluginKey('aiAutocompletion'),
				props: {
					handleKeyDown: (view, event) => {
						const { state, dispatch } = view;
						const { selection } = state;
						const { $head } = selection;

						if ($head.parent.type.name !== 'paragraph') return false;

						const node = $head.parent;

						if (event.key === 'Tab') {
							// if (!node.attrs['data-suggestion']) {
							//   // Generate completion
							//   if (loading) return true
							//   loading = true
							//   const prompt = node.textContent
							//   this.options.generateCompletion(prompt).then(suggestion => {
							//     if (suggestion && suggestion.trim() !== '') {
							//       dispatch(state.tr.setNodeMarkup($head.before(), null, {
							//         ...node.attrs,
							//         class: 'ai-autocompletion',
							//         'data-prompt': prompt,
							//         'data-suggestion': suggestion,
							//       }))
							//     }
							//     // If suggestion is empty or null, do nothing
							//   }).finally(() => {
							//     loading = false
							//   })
							// }

							if (node.attrs['data-suggestion']) {
								// Accept suggestion
								const suggestion = node.attrs['data-suggestion'];
								dispatch(
									state.tr.insertText(suggestion, $head.pos).setNodeMarkup($head.before(), null, {
										...node.attrs,
										class: null,
										'data-prompt': null,
										'data-suggestion': null
									})
								);
								return true;
							}
						} else {
							if (node.attrs['data-suggestion']) {
								// Reset suggestion on any other key press
								dispatch(
									state.tr.setNodeMarkup($head.before(), null, {
										...node.attrs,
										class: null,
										'data-prompt': null,
										'data-suggestion': null
									})
								);
							}

							// Start debounce logic for AI generation only if the cursor is at the end of the paragraph
							if (selection.empty && $head.pos === $head.end()) {
								// Set up debounce for AI generation
								if (this.options.debounceTime !== null) {
									clearTimeout(debounceTimer);

									// Capture current position
									const currentPos = $head.before();

									debounceTimer = setTimeout(() => {
										const newState = view.state;
										const newSelection = newState.selection;
										const newNode = newState.doc.nodeAt(currentPos);

										// Check if the node still exists and is still a paragraph
										if (
											newNode &&
											newNode.type.name === 'paragraph' &&
											newSelection.$head.pos === newSelection.$head.end() &&
											newSelection.$head.pos === currentPos + newNode.nodeSize - 1
										) {
											const prompt = newNode.textContent;

											if (prompt.trim() !== '') {
												if (loading) return true;
												loading = true;
												this.options
													.generateCompletion(prompt)
													.then((suggestion) => {
														if (suggestion && suggestion.trim() !== '') {
															if (
																view.state.selection.$head.pos === view.state.selection.$head.end()
															) {
																view.dispatch(
																	newState.tr.setNodeMarkup(currentPos, null, {
																		...newNode.attrs,
																		class: 'ai-autocompletion',
																		'data-prompt': prompt,
																		'data-suggestion': suggestion
																	})
																);
															}
														}
													})
													.finally(() => {
														loading = false;
													});
											}
										}
									}, this.options.debounceTime);
								}
							}
						}
						return false;
					},
					handleDOMEvents: {
						touchstart: (view, event) => {
							touchStartX = event.touches[0].clientX;
							touchStartY = event.touches[0].clientY;
							return false;
						},
						touchend: (view, event) => {
							const touchEndX = event.changedTouches[0].clientX;
							const touchEndY = event.changedTouches[0].clientY;

							const deltaX = touchEndX - touchStartX;
							const deltaY = touchEndY - touchStartY;

							// Check if the swipe was primarily horizontal and to the right
							if (Math.abs(deltaX) > Math.abs(deltaY) && deltaX > 50) {
								const { state, dispatch } = view;
								const { selection } = state;
								const { $head } = selection;
								const node = $head.parent;

								if (node.type.name === 'paragraph' && node.attrs['data-suggestion']) {
									const suggestion = node.attrs['data-suggestion'];
									dispatch(
										state.tr.insertText(suggestion, $head.pos).setNodeMarkup($head.before(), null, {
											...node.attrs,
											class: null,
											'data-prompt': null,
											'data-suggestion': null
										})
									);
									return true;
								}
							}
							return false;
						},
						// Add mousedown behavior
						// mouseup: (view, event) => {
						// 	const { state, dispatch } = view;
						// 	const { selection } = state;
						// 	const { $head } = selection;
						// 	const node = $head.parent;

						// 	// Reset debounce timer on mouse click
						// 	clearTimeout(debounceTimer);

						// 	// If a suggestion exists and the cursor moves, remove the suggestion
						// 	if (
						// 		node.type.name === 'paragraph' &&
						// 		node.attrs['data-suggestion'] &&
						// 		view.state.selection.$head.pos !== view.state.selection.$head.end()
						// 	) {
						// 		dispatch(
						// 			state.tr.setNodeMarkup($head.before(), null, {
						// 				...node.attrs,
						// 				class: null,
						// 				'data-prompt': null,
						// 				'data-suggestion': null
						// 			})
						// 		);
						// 	}

						// 	return false;
						// }
						mouseup: (view, event) => {
							const { state, dispatch } = view;

							// Reset debounce timer on mouse click
							clearTimeout(debounceTimer);

							// Iterate over all nodes in the document
							const tr = state.tr;
							state.doc.descendants((node, pos) => {
								if (node.type.name === 'paragraph' && node.attrs['data-suggestion']) {
									// Remove suggestion from this paragraph
									tr.setNodeMarkup(pos, null, {
										...node.attrs,
										class: null,
										'data-prompt': null,
										'data-suggestion': null
									});
								}
							});

							// Apply the transaction if any changes were made
							if (tr.docChanged) {
								dispatch(tr);
							}

							return false;
						}
					}
				}
			})
		];
	}
});
