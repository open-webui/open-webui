import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight';
import { toast } from 'svelte-sonner';
import { copyToClipboard } from '$lib/utils';

export const codeBlockWithCopy = (translate: (key: string) => string) =>
	CodeBlockLowlight.extend({
		addNodeView() {
			return ({ node }) => {
				let currentNode = node;
				let resetTimer: ReturnType<typeof setTimeout> | undefined;
				const pre = document.createElement('pre');
				pre.className = 'relative';
				const code = document.createElement('code');
				const button = document.createElement('button');
				button.type = 'button';
				button.contentEditable = 'false';
				button.className =
					'absolute end-2 top-2 rounded bg-gray-700 px-2 py-1 text-xs text-white hover:bg-gray-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white';
				button.setAttribute('aria-live', 'polite');

				const setLabel = (key: string) => {
					button.textContent = translate(key);
					button.setAttribute('aria-label', translate(key));
				};
				const setLanguage = (language: string | null) => {
					code.className = `block pe-16${language ? ` language-${language}` : ''}`;
				};
				setLabel('Copy');
				setLanguage(node.attrs.language);
				pre.append(code, button);

				const onCopy = async () => {
					const copied = await copyToClipboard(currentNode.textContent).catch(() => false);
					if (!copied) {
						clearTimeout(resetTimer);
						setLabel('Copy');
						toast.error(translate('Could not copy to clipboard. Please try again.'));
						return;
					}
					setLabel('Copied');
					clearTimeout(resetTimer);
					resetTimer = setTimeout(() => setLabel('Copy'), 2000);
				};
				button.addEventListener('click', onCopy);

				return {
					dom: pre,
					contentDOM: code,
					update(updatedNode) {
						if (updatedNode.type !== node.type) return false;
						currentNode = updatedNode;
						setLanguage(updatedNode.attrs.language);
						return true;
					},
					stopEvent: (event) => button.contains(event.target as Node),
					ignoreMutation: (mutation) => button.contains(mutation.target),
					destroy() {
						clearTimeout(resetTimer);
						button.removeEventListener('click', onCopy);
					}
				};
			};
		}
	});
