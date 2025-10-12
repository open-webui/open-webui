type ShortcutRegistry = {
	[key in Shortcut]: {
		name: string;
		keys: string[];
		category: string;
		tooltip?: string;
	};
};

export enum Shortcut {
	//Chat
	NEW_CHAT = 'newChat',
	NEW_TEMPORARY_CHAT = 'newTemporaryChat',
	DELETE_CHAT = 'deleteChat',
	GENERATE_PROMPT_PAIR = 'generatePromptPair',

	//Global
	SEARCH = 'search',
	OPEN_SETTINGS = 'openSettings',
	SHOW_SHORTCUTS = 'showShortcuts',
	TOGGLE_SIDEBAR = 'toggleSidebar',
	CLOSE_MODAL = 'closeModal',

	//Input
	FOCUS_INPUT = 'focusInput',
	ACCEPT_AUTOCOMPLETE = 'acceptAutocomplete',
	PREVENT_FILE_CREATION = 'preventFileCreation',
	NAVIGATE_PROMPT_HISTORY_UP = 'navigatePromptHistoryUp',
	ATTACH_FILE = 'attachFile',
	ADD_PROMPT = 'addPrompt',
	TALK_TO_MODEL = 'talkToModel',

	//Message
	COPY_LAST_CODE_BLOCK = 'copyLastCodeBlock',
	COPY_LAST_RESPONSE = 'copyLastResponse',
	STOP_GENERATING = 'stopGenerating'
}

export const shortcuts: ShortcutRegistry = {
	//Chat
	[Shortcut.NEW_CHAT]: {
		name: 'New Chat',
		keys: ['mod', 'shift', 'KeyO'],
		category: 'Chat'
	},
	[Shortcut.NEW_TEMPORARY_CHAT]: {
		name: 'New Temporary Chat',
		keys: ['mod', 'shift', 'Quote'],
		category: 'Chat'
	},
	[Shortcut.DELETE_CHAT]: {
		name: 'Delete Chat',
		keys: ['mod', 'shift', 'Backspace'],
		category: 'Chat'
	},
	[Shortcut.GENERATE_PROMPT_PAIR]: {
		name: 'Generate Prompt Pair',
		keys: ['mod', 'shift', 'Enter'],
		category: 'Chat',
        tooltip: 'Only active when the chat input is in focus and an LLM is generating a response.'
	},

	//Global
	[Shortcut.SEARCH]: {
		name: 'Search',
		keys: ['mod', 'KeyK'],
		category: 'Global'
	},
	[Shortcut.OPEN_SETTINGS]: {
		name: 'Open Settings',
		keys: ['mod', 'Period'],
		category: 'Global'
	},
	[Shortcut.SHOW_SHORTCUTS]: {
		name: 'Show Shortcuts',
		keys: ['mod', 'Slash'],
		category: 'Global'
	},
	[Shortcut.TOGGLE_SIDEBAR]: {
		name: 'Toggle Sidebar',
		keys: ['mod', 'shift', 'KeyS'],
		category: 'Global'
	},
	[Shortcut.CLOSE_MODAL]: {
		name: 'Close Modal',
		keys: ['Escape'],
		category: 'Global'
	},

	//Input
	[Shortcut.FOCUS_INPUT]: {
		name: 'Focus Text Area',
		keys: ['shift', 'Escape'],
		category: 'Input'
	},
	[Shortcut.ACCEPT_AUTOCOMPLETE]: {
		name: 'Accept Autocomplete Generation\nJump to Prompt Variable',
		keys: ['Tab'],
		category: 'Input'
	},
	[Shortcut.PREVENT_FILE_CREATION]: {
		name: 'Prevent File Creation',
		keys: ['mod', 'shift', 'KeyV'],
		category: 'Input',
		tooltip: 'Only active when "Paste Large Text as File" setting is toggled on.'
	},
	[Shortcut.NAVIGATE_PROMPT_HISTORY_UP]: {
		name: 'Edit Last Message',
		keys: ['ArrowUp'],
		category: 'Input',
        tooltip: 'Only can be triggered when the chat input is in focus.'
	},
	[Shortcut.ATTACH_FILE]: {
		name: 'Attach File From Knowledge',
		keys: ['#'],
		category: 'Input'
	},
	[Shortcut.ADD_PROMPT]: {
		name: 'Add Custom Prompt',
		keys: ['/'],
		category: 'Input'
	},
	[Shortcut.TALK_TO_MODEL]: {
		name: 'Talk to Model',
		keys: ['@'],
		category: 'Input'
	},

	//Message
	[Shortcut.COPY_LAST_CODE_BLOCK]: {
		name: 'Copy Last Code Block',
		keys: ['mod', 'shift', 'Semicolon'],
		category: 'Message'
	},
	[Shortcut.COPY_LAST_RESPONSE]: {
		name: 'Copy Last Response',
		keys: ['mod', 'shift', 'KeyC'],
		category: 'Message'
	},
	[Shortcut.STOP_GENERATING]: {
		name: 'Stop Generating',
		keys: ['Escape'],
		category: 'Message',
		tooltip: 'Only active when the chat input is in focus and an LLM is generating a response.'
	}
};