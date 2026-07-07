type PlainTextEditor = {
	state: {
		doc: {
			content: {
				size: number;
			};
			textBetween: (from: number, to: number, blockSeparator: string) => string;
		};
	};
};

export const getEditorPlainText = (editor: PlainTextEditor) => {
	return editor.state.doc.textBetween(0, editor.state.doc.content.size, '\n');
};
