import { Node } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';
import { createClassComponent } from 'svelte/legacy';
import { ySyncPluginKey } from 'y-prosemirror';
import FileItem from '../FileItem.svelte';

export const fileUploadsKey = new PluginKey<DecorationSet>('fileUploads');

const fileItemStyle = {
	small: true,
	className: 'w-56 max-w-full',
	colorClassName: 'bg-gray-50/60 dark:bg-white/[0.03] border border-gray-100/80 dark:border-white/5'
};

export default Node.create<{ context: Map<any, any> }>({
	name: 'fileAttachment',
	group: 'block',
	atom: true,
	draggable: true,
	addOptions() {
		return { context: new Map() };
	},
	addAttributes() {
		return {
			id: { default: '', rendered: false },
			name: { default: '', rendered: false },
			size: { default: 0, rendered: false }
		};
	},
	parseHTML() {
		return [
			{
				tag: 'div[data-file-id]',
				getAttrs: (element) => ({
					id: element.getAttribute('data-file-id'),
					name: element.textContent,
					size: Number(element.getAttribute('data-file-size')) || 0
				})
			},
			{
				tag: 'a[href^="/api/v1/files/"]',
				priority: 100,
				getAttrs: (element) => {
					const match = element
						.getAttribute('href')
						?.match(/^\/api\/v1\/files\/([\w-]+)\/content$/);
					return match ? { id: match[1], name: element.textContent, size: 0 } : false;
				}
			}
		];
	},
	renderHTML({ node }) {
		return [
			'div',
			{ 'data-file-id': node.attrs.id, 'data-file-size': node.attrs.size },
			['a', { href: `/api/v1/files/${encodeURIComponent(node.attrs.id)}/content` }, node.attrs.name]
		];
	},
	renderText({ node }) {
		return node.attrs.name;
	},
	addProseMirrorPlugins() {
		return [
			new Plugin({
				key: fileUploadsKey,
				state: {
					init: () => DecorationSet.empty,
					apply: (transaction, decorations) => {
						// Yjs replaces the whole document, including on undo, dropping local widgets.
						if (transaction.docChanged && transaction.getMeta(ySyncPluginKey)?.isChangeOrigin) {
							const widgets = decorations.find().map((widget) => {
								// shortcut: Keep the old offset; use Yjs relative positions for exact placement across edits.
								const pos = Math.min(widget.from, transaction.doc.content.size);
								return widget.spec.create(pos);
							});
							decorations = DecorationSet.create(transaction.doc, widgets);
						} else {
							decorations = decorations.map(transaction.mapping, transaction.doc);
						}
						const action = transaction.getMeta(fileUploadsKey);
						if (action?.add) {
							const { id, pos, file } = action.add;
							const create = (pos: number) => {
								let component;
								return Decoration.widget(
									pos,
									(view) => {
										const dom = document.createElement('div');
										dom.className = 'not-prose my-2 w-fit max-w-full';
										dom.setAttribute('aria-busy', 'true');
										component = createClassComponent({
											component: FileItem,
											target: dom,
											context: this.options.context,
											props: {
												...fileItemStyle,
												name: file.name,
												size: file.size,
												type: 'file',
												loading: true,
												dismissible: true
											}
										});
										component.$on('dismiss', () => {
											view.dispatch(view.state.tr.setMeta(fileUploadsKey, { remove: id }));
										});
										return dom;
									},
									{
										id,
										create,
										side: -1,
										stopEvent: () => true,
										destroy: () => component?.$destroy()
									}
								);
							};
							decorations = decorations.add(transaction.doc, [create(pos)]);
						}
						if (action?.remove) {
							decorations = decorations.remove(
								decorations.find(undefined, undefined, (spec) => spec.id === action.remove)
							);
						}
						return decorations;
					}
				},
				props: { decorations: (state) => fileUploadsKey.getState(state) }
			})
		];
	},
	addNodeView() {
		return ({ node, editor, getPos }) => {
			const dom = document.createElement('div');
			dom.className = 'not-prose my-2 w-fit max-w-full';
			dom.contentEditable = 'false';
			dom.dataset.fileId = node.attrs.id;
			const component = createClassComponent({
				component: FileItem,
				target: dom,
				context: this.options.context,
				props: {
					...fileItemStyle,
					item: { ...node.attrs, type: 'file' },
					name: node.attrs.name,
					type: 'file',
					size: node.attrs.size,
					url: node.attrs.id,
					dismissible: editor.isEditable,
					edit: editor.isEditable,
					modal: true
				}
			});
			component.$on('dismiss', () => {
				const pos = getPos();
				if (editor.isEditable && typeof pos === 'number') {
					editor
						.chain()
						.focus()
						.deleteRange({ from: pos, to: pos + node.nodeSize })
						.run();
				}
			});
			return {
				dom,
				stopEvent: (event) => !event.type.startsWith('drag'),
				ignoreMutation: () => true,
				destroy: () => component.$destroy()
			};
		};
	}
});
