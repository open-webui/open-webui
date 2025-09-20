/* eslint-disable */

import { findChildren } from '@tiptap/core';
import type { Node as ProsemirrorNode } from '@tiptap/pm/model';
import { Plugin, PluginKey, type PluginView } from '@tiptap/pm/state';
import { Decoration, DecorationSet, EditorView } from '@tiptap/pm/view';
// @ts-ignore
import highlight from 'highlight.js/lib/core';

import type { CodeBlockOptions } from '@tiptap/extension-code-block';
import CodeBlock from '@tiptap/extension-code-block';

import { loadLanguage, lowlight } from './index';

function parseNodes(nodes: any[], className: string[] = []): { text: string; classes: string[] }[] {
	return nodes.flatMap((node) => {
		const classes = [...className, ...(node.properties ? node.properties.className : [])];

		if (node.children) {
			return parseNodes(node.children, classes);
		}

		return {
			text: node.value,
			classes
		};
	});
}

function getHighlightNodes(result: any) {
	// `.value` for lowlight v1, `.children` for lowlight v2
	return result.value || result.children || [];
}

function registered(aliasOrLanguage: string) {
	return Boolean(highlight.getLanguage(aliasOrLanguage));
}

function getDecorations({
	doc,
	name,
	defaultLanguage,
	view
}: {
	doc: ProsemirrorNode;
	name: string;
	defaultLanguage: string | null | undefined;
	view: LowlightPluginView;
}) {
	const decorations: Decoration[] = [];

	findChildren(doc, (node) => node.type.name === name).forEach((block) => {
		let from = block.pos + 1;
		const language = block.node.attrs.language || defaultLanguage;
		const languages = lowlight.listLanguages();

		const isLanguageRegistered =
			language &&
			(languages.includes(language) || registered(language) || lowlight.registered(language));

		if (language && !isLanguageRegistered) {
			view.loadLanguage(language);
		}

		const nodes = isLanguageRegistered
			? getHighlightNodes(lowlight.highlight(language, block.node.textContent))
			: getHighlightNodes(lowlight.highlightAuto(block.node.textContent));

		parseNodes(nodes).forEach((node) => {
			const to = from + node.text.length;

			if (node.classes.length) {
				const decoration = Decoration.inline(from, to, {
					class: node.classes.join(' ')
				});

				decorations.push(decoration);
			}

			from = to;
		});
	});

	return DecorationSet.create(doc, decorations);
}

const HighLightJSLanguageLoaded = new PluginKey('HighLightJSLanguageLoaded');

class LowlightPluginView implements PluginView {
	private view: EditorView | undefined;

	public update(view: EditorView) {
		this.view = view;
	}

	public destroy() {}

	public loadLanguage(language: string) {
		loadLanguage(language).then(() => {
			this.view?.dispatch(this.view.state.tr.setMeta(HighLightJSLanguageLoaded, language));
		});
	}
}

function LowlightPlugin({
	name,
	defaultLanguage
}: {
	name: string;
	defaultLanguage: string | null | undefined;
}) {
	const lowlightPluginView = new LowlightPluginView();

	const lowlightPlugin: Plugin<any> = new Plugin({
		key: new PluginKey('lowlight'),

		view(view) {
			lowlightPluginView.update(view);
			return lowlightPluginView;
		},

		state: {
			init: (_, { doc }) =>
				getDecorations({
					doc,
					name,
					defaultLanguage,
					view: lowlightPluginView
				}),
			apply: (transaction, decorationSet, oldState, newState) => {
				const oldNodeName = oldState.selection.$head.parent.type.name;
				const newNodeName = newState.selection.$head.parent.type.name;
				const oldNodes = findChildren(oldState.doc, (node) => node.type.name === name);
				const newNodes = findChildren(newState.doc, (node) => node.type.name === name);

				const loadedLanguages = transaction.getMeta(HighLightJSLanguageLoaded);

				if (
					(loadedLanguages &&
						findChildren(
							transaction.doc,
							(node) => node.type.name === name && loadedLanguages === node.attrs.language
						)) ||
					(transaction.docChanged &&
						// Apply decorations if:
						// selection includes named node,
						([oldNodeName, newNodeName].includes(name) ||
							// OR transaction adds/removes named node,
							newNodes.length !== oldNodes.length ||
							// OR transaction has changes that completely encapsulte a node
							// (for example, a transaction that affects the entire document).
							// Such transactions can happen during collab syncing via y-prosemirror, for example.
							transaction.steps.some((step) => {
								// @ts-ignore
								return (
									// @ts-ignore
									step.from !== undefined &&
									// @ts-ignore
									step.to !== undefined &&
									oldNodes.some((node) => {
										// @ts-ignore
										return (
											// @ts-ignore
											node.pos >= step.from &&
											// @ts-ignore
											node.pos + node.node.nodeSize <= step.to
										);
									})
								);
							})))
				) {
					return getDecorations({
						doc: transaction.doc,
						name,
						defaultLanguage,
						view: lowlightPluginView
					});
				}

				return decorationSet.map(transaction.mapping, transaction.doc);
			}
		},

		props: {
			decorations(state) {
				return lowlightPlugin.getState(state);
			}
		}
	});

	return lowlightPlugin;
}

/**
 * This extension allows you to highlight code blocks with lowlight.
 * @see https://tiptap.dev/api/nodes/code-block-lowlight
 */
export const CodeBlockLowlight = CodeBlock.extend<CodeBlockOptions>({
	addOptions() {
		return {
			...this.parent?.(),
			languageClassPrefix: 'language-',
			exitOnTripleEnter: true,
			exitOnArrowDown: true,
			defaultLanguage: null,
			enableTabIndentation: false,
			tabSize: 4,
			HTMLAttributes: {}
		};
	},

	addProseMirrorPlugins() {
		return [
			...(this.parent?.() || []),
			LowlightPlugin({
				name: this.name,
				defaultLanguage: this.options.defaultLanguage
			})
		];
	}
});
