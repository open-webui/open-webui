import DOMPurify from 'dompurify';
/*
LaTeX Math Formula Extension for TipTap/ProseMirror
Provides Obsidian-style inline math rendering with cursor-aware toggling.

When cursor is outside $$...$$ regions, formulas are rendered with KaTeX.
When cursor enters the region, raw LaTeX code is shown for editing.
*/

import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from 'prosemirror-state';
import { Decoration, DecorationSet } from 'prosemirror-view';
import { TextSelection } from 'prosemirror-state';

// Delimiter list copied from katex-extension.ts
const DELIMITER_LIST = [
	{ left: '$$', right: '$$', display: true },
	{ left: '$', right: '$', display: false },
	{ left: '\\pu{', right: '}', display: false },
	{ left: '\\ce{', right: '}', display: false },
	{ left: '\\(', right: '\\)', display: false },
	{ left: '\\[', right: '\\]', display: true },
	{ left: '\\begin{equation}', right: '\\end{equation}', display: true }
];

// KaTeX lazy loading
let katexModule = null;

async function loadKaTeX() {
	if (!katexModule) {
		try {
			const [katex] = await Promise.all([
				import('katex'),
				import('katex/contrib/mhchem'),
				import('katex/dist/katex.min.css') // Load KaTeX CSS
			]);
			katexModule = katex.default;
			console.log('KaTeX loaded successfully');
		} catch (err) {
			console.error('Failed to load KaTeX:', err);
		}
	}
	return katexModule;
}

// Render cache for performance
const renderCache = new Map();

/**
 * Find matching right delimiter for a given left delimiter
 * @param {string} text - Text to search
 * @param {number} startPos - Position after left delimiter
 * @param {string} rightDelim - Right delimiter to find
 * @param {string} leftDelim - Left delimiter (to avoid matching itself)
 * @returns {number} - Position of right delimiter, or -1 if not found
 */
function findMatchingRight(text, startPos, rightDelim, leftDelim) {
	let pos = startPos;

	while (pos < text.length) {
		// Check for escape character
		if (text[pos] === '\\' && pos + 1 < text.length) {
			// Check if next char is the start of delimiter
			const nextChar = text[pos + 1];
			if (nextChar === '$' || nextChar === '(' || nextChar === '[' || nextChar === '{') {
				pos += 2; // Skip escaped delimiter
				continue;
			}
		}

		// Check for matching right delimiter
		if (text.substring(pos, pos + rightDelim.length) === rightDelim) {
			// For symmetric delimiters like $$, ensure we're not at the start
			if (leftDelim === rightDelim && pos === startPos) {
				pos += rightDelim.length;
				continue;
			}
			return pos;
		}

		pos++;
	}

	return -1; // No match found
}

/**
 * Find all math regions in a single line of text
 * @param {Object} doc - ProseMirror document
 * @param {number} lineStart - Absolute position of line start
 * @param {number} lineEnd - Absolute position of line end
 * @param {string} lineText - Text content of the line
 * @param {number} cursorPos - Current cursor position
 * @returns {Array} - Array of MathRegion objects
 */
function findMathRegions(doc, lineStart, lineEnd, lineText, cursorPos) {
	const regions = [];
	const matchedRanges = []; // Track matched ranges to avoid overlaps

	// Sort delimiters by length (longest first) for precedence
	const sortedDelimiters = [...DELIMITER_LIST].sort((a, b) => b.left.length - a.left.length);

	let searchIndex = 0;

	// First pass: Find complete delimiter pairs
	while (searchIndex < lineText.length) {
		let bestMatch = null;

		// Try each delimiter at current position
		for (const delimiter of sortedDelimiters) {
			const { left, right } = delimiter;

			// Check if left delimiter matches at searchIndex
			if (lineText.substring(searchIndex, searchIndex + left.length) === left) {
				// Find matching right delimiter
				const contentStart = searchIndex + left.length;
				const rightIndex = findMatchingRight(lineText, contentStart, right, left);

				if (rightIndex !== -1) {
					// Valid match found
					bestMatch = {
						startOffset: searchIndex,
						endOffset: rightIndex + right.length,
						contentStart: contentStart,
						contentEnd: rightIndex,
						delimiter: delimiter
					};
					break; // Use first (longest) matching delimiter
				}
			}
		}

		if (bestMatch) {
			const from = lineStart + bestMatch.startOffset;
			const to = lineStart + bestMatch.endOffset;
			const latex = lineText.substring(bestMatch.contentStart, bestMatch.contentEnd);

			// Track this range as matched
			matchedRanges.push({ start: bestMatch.startOffset, end: bestMatch.endOffset });

			// Check if cursor is inside this region (exclusive boundaries)
			// Cursor at boundaries (e.g., right after typing closing $) is considered OUTSIDE
			// This allows immediate rendering when user closes the delimiter
			const cursorInside = cursorPos > from && cursorPos < to;

			if (cursorInside) {
				// Cursor inside - show as code input mode with highlighting
				regions.push({
					from,
					to,
					latex,
					delimiter: {
						left: bestMatch.delimiter.left,
						right: bestMatch.delimiter.right
					},
					rendered: null,
					error: false,
					incomplete: false,
					codeMode: true, // Flag for code input styling
					lineStart,
					lineEnd
				});
			} else {
				// Cursor outside - render the formula
				regions.push({
					from,
					to,
					latex,
					delimiter: {
						left: bestMatch.delimiter.left,
						right: bestMatch.delimiter.right
					},
					rendered: null, // To be filled by renderMath()
					error: false,
					incomplete: false,
					codeMode: false,
					lineStart,
					lineEnd
				});
			}

			// Continue search after this match
			searchIndex = bestMatch.endOffset;
		} else {
			// No match at this position, advance by 1
			searchIndex++;
		}
	}

	// Second pass: Find incomplete delimiters (only $ and $$ for simplicity)
	const incompleteDelimiters = [
		{ left: '$$', right: '$$' },
		{ left: '$', right: '$' }
	];

	for (const delimiter of incompleteDelimiters) {
		const { left, right } = delimiter;
		let index = 0;

		while (index < lineText.length) {
			index = lineText.indexOf(left, index);
			if (index === -1) break;

			// Check if this position is already matched
			const isMatched = matchedRanges.some(
				(range) => index >= range.start && index < range.end
			);

			if (!isMatched) {
				// Check if there's a matching right delimiter
				const contentStart = index + left.length;
				const rightIndex = findMatchingRight(lineText, contentStart, right, left);

				if (rightIndex === -1) {
					// Incomplete delimiter found
					const from = lineStart + index;
					const to = lineStart + lineText.length; // End of line

					// Only show if cursor is inside
					if (cursorPos > from && cursorPos <= to) {
						regions.push({
							from,
							to,
							latex: lineText.substring(contentStart),
							delimiter: { left, right },
							rendered: null,
							error: false,
							incomplete: true,
							codeMode: true, // Always code mode for incomplete
							lineStart,
							lineEnd
						});
					}
				}
			}

			index += left.length;
		}
	}

	return regions;
}

/**
 * Scan entire document for math regions
 * @param {Object} doc - ProseMirror document
 * @param {number} cursorPos - Current cursor position
 * @returns {Array} - Array of all MathRegion objects in document
 */
function scanDocument(doc, cursorPos) {
	const regions = [];

	// Iterate through all text blocks (paragraphs, headings, etc.)
	doc.descendants((node, pos) => {
		// Only process text block nodes
		if (!node.isTextblock) return;

		const lineStart = pos + 1; // Content starts after opening token
		const lineEnd = pos + node.nodeSize - 1; // Before closing token
		const lineText = node.textContent;

		// Find math regions in this line
		const lineRegions = findMathRegions(doc, lineStart, lineEnd, lineText, cursorPos);
		regions.push(...lineRegions);
	});

	return regions;
}

/**
 * Render a math region with KaTeX
 * @param {Object} region - MathRegion object
 * @returns {Promise<Object>} - Updated region with rendered HTML
 */
async function renderMath(region) {
	// Check cache first
	const cacheKey = region.latex;
	if (renderCache.has(cacheKey)) {
		const cached = renderCache.get(cacheKey);
		region.rendered = cached.rendered;
		region.error = cached.error;
		return region;
	}

	try {
		const katex = await loadKaTeX();
		if (!katex) {
			throw new Error('KaTeX not loaded');
		}

		// Render with options (always inline mode)
		const html = katex.renderToString(region.latex, {
			displayMode: false, // Always inline per requirements
			throwOnError: true, // Throw errors to catch them
			errorColor: '#cc0000', // Red for errors
			strict: false, // Allow some non-standard features
			trust: false, // Don't allow \url or \href for security
			output: 'html' // Output HTML instead of MathML
		});

		region.rendered = html;
		region.error = false;

		// Cache the result
		renderCache.set(cacheKey, { rendered: html, error: false });
	} catch (err) {
		console.error('KaTeX render error for:', region.latex, err.message);
		region.rendered = null;
		region.error = true;

		// Cache the error result
		renderCache.set(cacheKey, { rendered: null, error: true });
	}

	return region;
}

/**
 * Render all math regions in parallel
 * @param {Array} regions - Array of MathRegion objects
 * @returns {Promise<Array>} - Array of rendered regions
 */
async function renderAllRegions(regions) {
	// Render ALL regions (including code mode for preview)
	await Promise.all(regions.map((region) => renderMath(region)));
	return regions;
}

/**
 * Create a widget DOM element for rendered math
 * @param {any} region - MathRegion object with rendered HTML
 * @returns {Function} - Widget creation function for ProseMirror
 */
function createMathWidget(region) {
	return (view) => {
		const span = document.createElement('span');
		span.className = 'math-render-widget';
		span.innerHTML = DOMPurify.sanitize(region.rendered || '');
		span.contentEditable = 'false';

		// Store region data as attributes
		const from = region.from || 0;
		const to = region.to || 0;
		const delimiterLeft = (region.delimiter && region.delimiter.left) || '$';
		const delimiterRight = (region.delimiter && region.delimiter.right) || '$';

		span.setAttribute('data-latex', region.latex || '');
		span.setAttribute('data-from', String(from));
		span.setAttribute('data-to', String(to));
		span.setAttribute('data-delimiter-left', delimiterLeft);
		span.setAttribute('data-delimiter-right', delimiterRight);

		// Click handler to move cursor INSIDE the formula (after opening delimiter)
		span.onclick = (event) => {
			event.preventDefault();
			const fromAttr = span.getAttribute('data-from');
			const delimiterLeftAttr = span.getAttribute('data-delimiter-left');

			if (fromAttr && delimiterLeftAttr) {
				const from = parseInt(fromAttr, 10);
				// Move cursor inside the formula, right after the opening delimiter
				const cursorPos = from + delimiterLeftAttr.length;

				view.dispatch(
					view.state.tr.setSelection(TextSelection.create(view.state.doc, cursorPos, cursorPos))
				);
				view.focus();
			}
		};

		return span;
	};
}

/**
 * Create a floating preview widget for code mode
 * @param {any} region - MathRegion object with rendered HTML
 * @param {any} view - ProseMirror editor view
 * @returns {Node} - DOM node for preview
 */
function createMathPreviewWidget(region, view) {
	const preview = document.createElement('span');
	preview.className = 'math-preview-widget';

	if (region.error) {
		// Show error message
		preview.innerHTML = DOMPurify.sanitize('<span class="math-preview-error">Invalid LaTeX</span>');
	} else if (region.rendered) {
		// Show rendered preview
		preview.innerHTML = DOMPurify.sanitize(region.rendered);
	} else {
		// Empty or loading
		preview.innerHTML = DOMPurify.sanitize('<span class="math-preview-loading">...</span>');
	}



	return preview;
}

/**
 * Build decoration set from math regions
 * @param {Object} state - ProseMirror editor state
 * @param {Array} regions - Array of rendered MathRegion objects
 * @param {any} view - ProseMirror editor view
 * @returns {DecorationSet} - Decoration set to apply
 */
function buildDecorations(state, regions, view) {
	const decorations = [];

	for (const region of regions) {
		if (region.codeMode) {
			// Code input mode: highlight with blue box and code styling
			decorations.push(
				Decoration.inline(region.from, region.to, {
					class: region.incomplete ? 'math-code-input math-incomplete' : 'math-code-input',
					nodeName: 'span'
				})
			);

			// Add floating preview widget above the code input
			// Only show if there's actual content and it's not just the opening delimiter
			if (region.latex && region.latex.trim() !== '') {
				decorations.push(
					Decoration.widget(region.from, createMathPreviewWidget(region, view), {
						side: -1, // Insert before the position
						key: `math-preview-${region.from}-${region.to}`
					})
				);
			}
		} else if (region.error) {
			// Error: red underline on original text
			decorations.push(
				Decoration.inline(region.from, region.to, {
					class: 'math-error',
					style: 'color: #cc0000; text-decoration: underline wavy #cc0000;',
					title: 'Invalid LaTeX syntax'
				})
			);
		} else if (region.rendered) {
			// Success: hide source and show widget
			// 1. Hide the original text
			decorations.push(
				Decoration.inline(region.from, region.to, {
					class: 'math-source-hidden',
					nodeName: 'span'
				})
			);

			// 2. Insert rendered widget at the start position
			decorations.push(
				Decoration.widget(region.from, createMathWidget(region), {
					side: 1, // Insert after the position
					key: `math-widget-${region.from}-${region.to}`
				})
			);
		}
	}

	return DecorationSet.create(state.doc, decorations);
}

/**
 * Main TipTap Extension
 */
export const MathFormula = Extension.create({
	name: 'mathFormula',

	addProseMirrorPlugins() {
		let debounceTimer = null;
		/** @type {number | null} */
		let animationFrameId = null;
		let isComposing = false;
		let katexLoaded = false;

		const pluginKey = new PluginKey('mathFormula');

		// Debounced update function
		const scheduleUpdate = (view, immediate = false) => {
			clearTimeout(debounceTimer);
			if (animationFrameId) {
				cancelAnimationFrame(animationFrameId);
				animationFrameId = null;
			}

			const doUpdate = async () => {
				if (isComposing) return; // Skip during composition

				const { state, dispatch } = view;
				const cursorPos = state.selection.from;

				// Scan document for math regions
				const regions = scanDocument(state.doc, cursorPos);

				// Load KaTeX if needed
				if (!katexLoaded) {
					await loadKaTeX();
					katexLoaded = true;
				}

				// Render all regions
				await renderAllRegions(regions);

				// Build decorations
				const decorations = buildDecorations(state, regions, view);

				// Update plugin state
				dispatch(
					state.tr.setMeta(pluginKey, {
						type: 'update-decorations',
						decorations,
						regions
					})
				);
			};

			if (immediate) {
				// Use requestAnimationFrame for smooth, immediate update without blocking
				animationFrameId = requestAnimationFrame(() => {
					doUpdate();
				});
			} else {
				debounceTimer = setTimeout(doUpdate, 300); // 300ms debounce
			}
		};

		return [
			new Plugin({
				key: pluginKey,

				state: {
					init(_, state) {
						return {
							decorations: DecorationSet.empty,
							isComposing: false,
							updateScheduled: false,
							cursorPos: state.selection.from,
							regions: []
						};
					},

					apply(tr, prevState, oldState, newState) {
						// Handle meta updates from scheduleUpdate
						const meta = tr.getMeta(pluginKey);
						if (meta?.type === 'set-composing') {
							return { ...prevState, isComposing: meta.value };
						}
						if (meta?.type === 'update-decorations') {
							return {
								...prevState,
								decorations: meta.decorations,
								regions: meta.regions,
								cursorPos: newState.selection.from
							};
						}

						// Map decorations through document changes
						if (tr.docChanged) {
							return {
								...prevState,
								decorations: prevState.decorations.map(tr.mapping, tr.doc),
								cursorPos: newState.selection.from
							};
						}

						// Track cursor position changes
						if (tr.selectionSet) {
							return {
								...prevState,
								cursorPos: newState.selection.from
							};
						}

						return prevState;
					}
				},

				props: {
					decorations(state) {
						return pluginKey.getState(state)?.decorations;
					},

					handleDOMEvents: {
						compositionstart(view, event) {
							isComposing = true;
							view.dispatch(
								view.state.tr.setMeta(pluginKey, {
									type: 'set-composing',
									value: true
								})
							);
							return false;
						},

						compositionend(view, event) {
							isComposing = false;
							view.dispatch(
								view.state.tr.setMeta(pluginKey, {
									type: 'set-composing',
									value: false
								})
							);
							// Trigger update after composition
							scheduleUpdate(view);
							return false;
						}
					}
				},

				view(editorView) {
					// Initial render
					scheduleUpdate(editorView, true);

					return {
						update(view, prevState) {
							const { state } = view;

							// Check if this update is from our own decoration update
							const meta = state.tr.getMeta(pluginKey);
							if (meta?.type === 'update-decorations') {
								// Skip to avoid infinite loop
								return;
							}

							// Trigger update on document or selection change
							if (prevState.doc !== state.doc) {
								// Document changed - instant update for immediate feedback
								scheduleUpdate(view, true);
							} else if (prevState.selection.from !== state.selection.from) {
								// Only cursor moved - instant update
								scheduleUpdate(view, true);
							}
						},

						destroy() {
							clearTimeout(debounceTimer);
						}
					};
				}
			})
		];
	}
});
