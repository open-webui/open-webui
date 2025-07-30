import { mergeAttributes, Node, nodeInputRule } from '@tiptap/core';

export interface ImageOptions {
	/**
	 * Controls if the image node should be inline or not.
	 * @default false
	 * @example true
	 */
	inline: boolean;

	/**
	 * Controls if base64 images are allowed. Enable this if you want to allow
	 * base64 image urls in the `src` attribute.
	 * @default false
	 * @example true
	 */
	allowBase64: boolean;

	/**
	 * HTML attributes to add to the image element.
	 * @default {}
	 * @example { class: 'foo' }
	 */
	HTMLAttributes: Record<string, any>;
}

export interface SetImageOptions {
	src: string;
	alt?: string;
	title?: string;
	width?: number;
	height?: number;
}

declare module '@tiptap/core' {
	interface Commands<ReturnType> {
		image: {
			/**
			 * Add an image
			 * @param options The image attributes
			 * @example
			 * editor
			 *   .commands
			 *   .setImage({ src: 'https://tiptap.dev/logo.png', alt: 'tiptap', title: 'tiptap logo' })
			 */
			setImage: (options: SetImageOptions) => ReturnType;
		};
	}
}

/**
 * Matches an image to a ![image](src "title") on input.
 */
export const inputRegex = /(?:^|\s)(!\[(.+|:?)]\((\S+)(?:(?:\s+)["'](\S+)["'])?\))$/;

/**
 * This extension allows you to insert images.
 * @see https://www.tiptap.dev/api/nodes/image
 */
export const Image = Node.create<ImageOptions>({
	name: 'image',

	addOptions() {
		return {
			inline: false,
			allowBase64: false,
			HTMLAttributes: {}
		};
	},

	inline() {
		return this.options.inline;
	},

	group() {
		return this.options.inline ? 'inline' : 'block';
	},

	draggable: true,

	addAttributes() {
		return {
			file: {
				default: null
			},
			src: {
				default: null
			},
			alt: {
				default: null
			},
			title: {
				default: null
			},
			width: {
				default: null
			},
			height: {
				default: null
			}
		};
	},

	parseHTML() {
		return [
			{
				tag: this.options.allowBase64 ? 'img[src]' : 'img[src]:not([src^="data:"])'
			}
		];
	},

	renderHTML({ HTMLAttributes }) {
		if (HTMLAttributes.file) {
			delete HTMLAttributes.file;
		}

		return ['img', mergeAttributes(this.options.HTMLAttributes, HTMLAttributes)];
	},

	addNodeView() {
		return ({ node, editor }) => {
			const domImg = document.createElement('img');
			domImg.setAttribute('src', node.attrs.src || '');
			domImg.setAttribute('alt', node.attrs.alt || '');
			domImg.setAttribute('title', node.attrs.title || '');

			const container = document.createElement('div');
			const img = document.createElement('img');

			const fileId = node.attrs.src.replace('data://', '');
			img.setAttribute('id', `image:${fileId}`);

			img.classList.add('rounded-md', 'max-h-72', 'w-fit', 'object-contain');

			const editorFiles = editor.storage?.files || [];

			if (editorFiles && node.attrs.src.startsWith('data://')) {
				const file = editorFiles.find((f) => f.id === fileId);
				if (file) {
					img.setAttribute('src', file.url || '');
				} else {
					img.setAttribute('src', '/image-placeholder.png');
				}
			} else {
				img.setAttribute('src', node.attrs.src || '');
			}

			img.setAttribute('alt', node.attrs.alt || '');
			img.setAttribute('title', node.attrs.title || '');

			img.addEventListener('data', (e) => {
				const files = e?.files || [];
				if (files && node.attrs.src.startsWith('data://')) {
					const file = editorFiles.find((f) => f.id === fileId);
					if (file) {
						img.setAttribute('src', file.url || '');
					} else {
						img.setAttribute('src', '/image-placeholder.png');
					}
				}
			});

			container.append(img);
			return {
				dom: img,
				contentDOM: domImg
			};
		};
	},

	addCommands() {
		return {
			setImage:
				(options) =>
				({ commands }) => {
					return commands.insertContent({
						type: this.name,
						attrs: options
					});
				}
		};
	},

	addInputRules() {
		return [
			nodeInputRule({
				find: inputRegex,
				type: this.type,
				getAttributes: (match) => {
					const [, , alt, src, title] = match;

					return { src, alt, title };
				}
			})
		];
	}
});
