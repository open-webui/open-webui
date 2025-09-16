import { ViewPlugin, Decoration } from '@codemirror/view';
import { RangeSetBuilder } from '@codemirror/state';
import hljs from 'highlight.js/lib/core';

// Pre-load essential languages
import javascript from 'highlight.js/lib/languages/javascript';
import typescript from 'highlight.js/lib/languages/typescript';
import python from 'highlight.js/lib/languages/python';
import xml from 'highlight.js/lib/languages/xml'; // for HTML
import css from 'highlight.js/lib/languages/css';
import elixir from 'highlight.js/lib/languages/elixir';

// Register core languages
hljs.registerLanguage('javascript', javascript);
hljs.registerLanguage('typescript', typescript);
hljs.registerLanguage('python', python);
hljs.registerLanguage('html', xml);
hljs.registerLanguage('css', css);
hljs.registerLanguage('elixir', elixir);

// Custom HCL language definition (since it's not available in highlight.js)
const hclLanguage = {
	keywords: {
		keyword: 'resource data variable locals output module provider terraform required_providers',
		built_in: 'true false null',
		type: 'string number bool list map set object tuple'
	},
	contains: [
		{
			className: 'string',
			begin: '"',
			end: '"',
			contains: [
				{
					className: 'subst',
					begin: '\\$\\{',
					end: '\\}'
				}
			]
		},
		{
			className: 'comment',
			begin: '#',
			end: '$'
		},
		{
			className: 'comment',
			begin: '/\\*',
			end: '\\*/'
		},
		{
			className: 'number',
			begin: '\\b\\d+(\\.\\d+)?'
		}
	]
};

// Register custom HCL language
hljs.registerLanguage('hcl', () => hclLanguage);
hljs.registerLanguage('terraform', () => hclLanguage);

// Language import cache for dynamic loading
const languageCache = new Map();

const loadLanguage = async (lang) => {
	if (hljs.getLanguage(lang)) {
		return true; // Already loaded
	}

	if (languageCache.has(lang)) {
		return languageCache.get(lang);
	}

	try {
		const languageModule = await import(`highlight.js/lib/languages/${lang}`);
		hljs.registerLanguage(lang, languageModule.default);
		languageCache.set(lang, true);
		return true;
	} catch (error) {
		console.warn(`Failed to load language: ${lang}`, error);
		languageCache.set(lang, false);
		return false;
	}
};

export const highlightJSExtension = (language) => ViewPlugin.fromClass(
	class {
		constructor(view) {
			this.view = view;
			this.decorations = this.buildDecorations(view);
			this.loadLanguageIfNeeded(language);
		}

		async loadLanguageIfNeeded(lang) {
			if (lang && !hljs.getLanguage(lang)) {
				const loaded = await loadLanguage(lang);
				if (loaded && this.view) {
					// Trigger re-highlighting after language loads
					this.decorations = this.buildDecorations(this.view);
				}
			}
		}

		update(update) {
			if (update.docChanged || update.viewportChanged) {
				this.decorations = this.buildDecorations(update.view);
			}
		}

		buildDecorations(view) {
			const builder = new RangeSetBuilder();
			const code = view.state.doc.toString();

			if (language && hljs.getLanguage(language)) {
				const result = hljs.highlight(code, { language });

				// Collect all decorations first, then sort them
				const decorations = [];
				const tempDiv = document.createElement('div');
				tempDiv.innerHTML = result.value;

				let pos = 0;

				const walkNodes = (node) => {
					if (node.nodeType === Node.TEXT_NODE) {
						pos += node.textContent.length;
					} else if (node.nodeType === Node.ELEMENT_NODE) {
						const start = pos;

						// Process children first to get correct end position
						for (const child of node.childNodes) {
							walkNodes(child);
						}

						const end = pos;

						// Add decoration for this element if it has a class
						if (node.className && start < end) {
							decorations.push({
								from: start,
								to: end,
								decoration: Decoration.mark({
									class: node.className // Use the exact class from highlight.js
								})
							});
						}
					}
				};

				for (const child of tempDiv.childNodes) {
					walkNodes(child);
				}

				// Sort decorations by position before adding to builder
				decorations.sort((a, b) => a.from - b.from);

				// Add sorted decorations to builder
				for (const dec of decorations) {
					if (dec.from < dec.to) { // Ensure valid range
						builder.add(dec.from, dec.to, dec.decoration);
					}
				}
			}

			return builder.finish();
		}
	},
	{ decorations: v => v.decorations }
);
