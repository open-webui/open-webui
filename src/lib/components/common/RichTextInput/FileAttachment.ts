import { Node } from '@tiptap/core';
import { createClassComponent } from 'svelte/legacy';
import FileItem from '../FileItem.svelte';

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
					item: { ...node.attrs, type: 'file' },
					name: node.attrs.name,
					type: 'file',
					size: node.attrs.size,
					url: node.attrs.id,
					dismissible: editor.isEditable,
					edit: editor.isEditable,
					small: true,
					modal: true,
					className: 'w-56 max-w-full',
					colorClassName:
						'bg-gray-50/60 dark:bg-white/[0.03] border border-gray-100/80 dark:border-white/5'
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
