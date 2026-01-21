import { Extension, type Editor, type Range } from '@tiptap/core';
import Suggestion from '@tiptap/suggestion';

interface CommandProps {
	command: (args: { editor: Editor; range: Range }) => void;
}

export default Extension.create({
	name: 'commands',

	addOptions() {
		return {
			suggestion: {
				char: '/',
				command: ({ editor, range, props }: { editor: Editor; range: Range; props: CommandProps }) => {
					props.command({ editor, range });
				}
			}
		};
	},

	addProseMirrorPlugins() {
		return [
			Suggestion({
				editor: this.editor,
				...this.options.suggestion
			})
		];
	}
});
