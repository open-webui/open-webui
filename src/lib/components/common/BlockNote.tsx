import { WEBUI_BASE_URL } from '$lib/constants';
import { createOpenAICompatible } from '@ai-sdk/openai-compatible';
import { BlockNoteEditor, filterSuggestionItems } from '@blocknote/core';
import '@blocknote/core/fonts/inter.css';
import { en } from '@blocknote/core/locales';
import { BlockNoteView } from '@blocknote/mantine';
import '@blocknote/mantine/style.css';
import {
	FormattingToolbar,
	FormattingToolbarController,
	SuggestionMenuController,
	getDefaultReactSlashMenuItems,
	getFormattingToolbarItems,
	useCreateBlockNote
} from '@blocknote/react';
import {
	AIMenuController,
	AIToolbarButton,
	createAIExtension,
	getAISlashMenuItems
} from '@blocknote/xl-ai';
import { en as aiEn } from '@blocknote/xl-ai/locales';
import '@blocknote/xl-ai/style.css'; // add the AI stylesheet
import { useEffect } from 'react';

const provider = createOpenAICompatible({
	baseURL: WEBUI_BASE_URL + '/api',
	name: 'openai',
	apiKey: localStorage.getItem('token') || ''
});

const model = provider('gpt-4-0613');
console.log('MODEL', model);

export default function BlockNote({ content }: { content: string }) {
	console.log('content', content);
	// Creates a new editor instance.
	const editor = useCreateBlockNote({
		dictionary: {
			...en,
			ai: aiEn
		},
		extensions: [
			createAIExtension({
				model,
				stream: false
			})
		]
	});

	useEffect(() => {
		const replaceBlocks = async () => {
			editor.replaceBlocks(editor.document, await editor.tryParseMarkdownToBlocks(content));
		};
		replaceBlocks();
	}, [content]);

	console.log('something !!!!');
	// Renders the editor instance using a React component.
	return (
		<BlockNoteView theme={'light'} editor={editor} formattingToolbar={false} slashMenu={false}>
			{/* Add the AI Command menu to the editor */}
			<AIMenuController />

			{/* Create you own Formatting Toolbar with an AI button,
    (see the full example code below) */}
			<FormattingToolbarWithAI />

			{/* Create you own SlashMenu with an AI option,
    (see the full example code below) */}
			<SuggestionMenuWithAI editor={editor} />
		</BlockNoteView>
	);
}

function FormattingToolbarWithAI() {
	return (
		<FormattingToolbarController
			formattingToolbar={() => (
				<FormattingToolbar>
					{...getFormattingToolbarItems()}
					{/* Add the AI button */}
					<AIToolbarButton />
				</FormattingToolbar>
			)}
		/>
	);
}

// Slash menu with the AI option added
function SuggestionMenuWithAI(props: { editor: BlockNoteEditor<any, any, any> }) {
	return (
		<SuggestionMenuController
			triggerCharacter="/"
			getItems={async (query) =>
				filterSuggestionItems(
					[
						...getDefaultReactSlashMenuItems(props.editor),
						// add the default AI slash menu items, or define your own
						...getAISlashMenuItems(props.editor)
					],
					query
				)
			}
		/>
	);
}
