import { get, writable } from 'svelte/store';

export type ShortcutDefinition = {
	name: string;
	keys: string[];
	category: string;
	tooltip?: string;
	configurable?: boolean;
	setting?: {
		id: string;
		value: unknown;
	};
};

type ShortcutRegistry = {
	[key in Shortcut]?: ShortcutDefinition;
};

export enum Shortcut {
	//Chat
	NEW_CHAT = 'newChat',
	NEW_TEMPORARY_CHAT = 'newTemporaryChat',
	DELETE_CHAT = 'deleteChat',
	OPEN_MODEL_SELECTOR = 'openModelSelector',
	TOGGLE_DICTATION = 'toggleDictation',

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
	GENERATE_MESSAGE_PAIR = 'generateMessagePair',
	REGENERATE_RESPONSE = 'regenerateResponse',
	COPY_LAST_CODE_BLOCK = 'copyLastCodeBlock',
	COPY_LAST_RESPONSE = 'copyLastResponse',
	STOP_GENERATING = 'stopGenerating',

	//Voice
	TOGGLE_MUTE = 'toggleMute'
}

export const CONFIGURABLE_SHORTCUTS = [
	Shortcut.NEW_CHAT,
	Shortcut.NEW_TEMPORARY_CHAT,
	Shortcut.DELETE_CHAT,
	Shortcut.OPEN_MODEL_SELECTOR,
	Shortcut.TOGGLE_DICTATION,
	Shortcut.SEARCH,
	Shortcut.OPEN_SETTINGS,
	Shortcut.SHOW_SHORTCUTS,
	Shortcut.TOGGLE_SIDEBAR,
	Shortcut.CLOSE_MODAL,
	Shortcut.FOCUS_INPUT,
	Shortcut.GENERATE_MESSAGE_PAIR,
	Shortcut.REGENERATE_RESPONSE,
	Shortcut.COPY_LAST_CODE_BLOCK,
	Shortcut.COPY_LAST_RESPONSE
] as const;

export type ConfigurableShortcut = (typeof CONFIGURABLE_SHORTCUTS)[number];
export type KeybindingsMap = Record<ConfigurableShortcut, string>;

export const DEFAULT_KEYBINDINGS: KeybindingsMap = {
	[Shortcut.NEW_CHAT]: 'Cmd+Shift+O',
	[Shortcut.NEW_TEMPORARY_CHAT]: "Cmd+Shift+'",
	[Shortcut.DELETE_CHAT]: 'Cmd+Shift+Backspace',
	[Shortcut.OPEN_MODEL_SELECTOR]: 'Cmd+Shift+M',
	[Shortcut.TOGGLE_DICTATION]: 'Cmd+Shift+L',
	[Shortcut.SEARCH]: 'Cmd+K',
	[Shortcut.OPEN_SETTINGS]: 'Cmd+.',
	[Shortcut.SHOW_SHORTCUTS]: 'Cmd+/',
	[Shortcut.TOGGLE_SIDEBAR]: 'Cmd+Shift+S',
	[Shortcut.CLOSE_MODAL]: 'Escape',
	[Shortcut.FOCUS_INPUT]: 'Shift+Escape',
	[Shortcut.GENERATE_MESSAGE_PAIR]: 'Cmd+Shift+Enter',
	[Shortcut.REGENERATE_RESPONSE]: 'Cmd+R',
	[Shortcut.COPY_LAST_CODE_BLOCK]: 'Cmd+Shift+;',
	[Shortcut.COPY_LAST_RESPONSE]: 'Cmd+Shift+C'
};

export const keybindings = writable<KeybindingsMap>({ ...DEFAULT_KEYBINDINGS });

export function isConfigurableShortcut(id: Shortcut): id is ConfigurableShortcut {
	return (CONFIGURABLE_SHORTCUTS as readonly Shortcut[]).includes(id);
}

export function loadKeybindings(saved: Partial<Record<string, string>> | undefined): void {
	if (!saved || typeof saved !== 'object') return;

	keybindings.update((current) => {
		const updated = { ...current };
		for (const id of CONFIGURABLE_SHORTCUTS) {
			if (typeof saved[id] === 'string') {
				updated[id] = saved[id]!;
			}
		}
		return updated;
	});
}

export function resetKeybindings(): void {
	keybindings.set({ ...DEFAULT_KEYBINDINGS });
}

const IS_MAC = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.userAgent);

export function eventToChord(event: KeyboardEvent): string {
	const parts: string[] = [];

	if (IS_MAC) {
		if (event.metaKey) parts.push('Cmd');
		if (event.ctrlKey) parts.push('Ctrl');
	} else if (event.ctrlKey) {
		parts.push('Cmd');
	}

	if (event.altKey) parts.push('Alt');
	if (event.shiftKey) parts.push('Shift');

	let key = event.key;
	if (['Meta', 'Control', 'Alt', 'Shift'].includes(key)) return '';

	if (key === ' ') key = 'Space';
	if (key.length === 1) key = key.toUpperCase();

	if (key === '"') key = "'";
	if (key === ':') key = ';';
	if (key === '?') key = '/';
	if (key === '{') key = '[';
	if (key === '}') key = ']';

	parts.push(key);
	return parts.join('+');
}

function formatChordPart(part: string): string {
	if (IS_MAC) {
		switch (part) {
			case 'Cmd':
				return '⌘';
			case 'Ctrl':
				return '⌃';
			case 'Alt':
				return '⌥';
			case 'Shift':
				return '⇧';
			case 'Backspace':
				return '⌫';
			case 'Escape':
				return 'Esc';
			case 'Enter':
				return '↩\uFE0E';
			case 'Tab':
				return '⇥';
		}
	}

	if (part === 'Cmd') return 'Ctrl';
	if (part === 'Escape') return 'Esc';
	return part;
}

export function formatChord(chord: string): string {
	if (!chord) return '';
	const parts = chord.split('+').map(formatChordPart);
	return IS_MAC ? parts.join('') : parts.join('+');
}

function buildReverseLookup(bindings: KeybindingsMap): Map<string, ConfigurableShortcut> {
	const lookup = new Map<string, ConfigurableShortcut>();
	for (const id of CONFIGURABLE_SHORTCUTS) {
		const chord = bindings[id];
		if (chord) lookup.set(chord, id);
	}
	return lookup;
}

export function matchKeybinding(event: KeyboardEvent): ConfigurableShortcut | null {
	const chord = eventToChord(event);
	if (!chord) return null;
	return buildReverseLookup(get(keybindings)).get(chord) ?? null;
}

export const shortcuts: ShortcutRegistry = {
	//Chat
	[Shortcut.NEW_CHAT]: {
		name: 'New Chat',
		keys: ['mod', 'shift', 'O'],
		category: 'Chat',
		configurable: true
	},
	[Shortcut.NEW_TEMPORARY_CHAT]: {
		name: 'New Temporary Chat',
		keys: ['mod', 'shift', `'`],
		category: 'Chat',
		configurable: true
	},
	[Shortcut.DELETE_CHAT]: {
		name: 'Delete Chat',
		keys: ['mod', 'shift', 'Backspace'],
		category: 'Chat',
		configurable: true
	},
	[Shortcut.OPEN_MODEL_SELECTOR]: {
		name: 'Open Model Selector',
		keys: ['mod', 'shift', 'M'],
		category: 'Chat',
		configurable: true
	},
	[Shortcut.TOGGLE_DICTATION]: {
		name: 'Toggle Dictation',
		keys: ['mod', 'shift', 'L'],
		category: 'Chat',
		configurable: true
	},

	//Global
	[Shortcut.SEARCH]: {
		name: 'Search',
		keys: ['mod', 'K'],
		category: 'Global',
		configurable: true
	},
	[Shortcut.OPEN_SETTINGS]: {
		name: 'Open Settings',
		keys: ['mod', '.'],
		category: 'Global',
		configurable: true
	},
	[Shortcut.SHOW_SHORTCUTS]: {
		name: 'Show Shortcuts',
		keys: ['mod', '/'],
		category: 'Global',
		configurable: true
	},
	[Shortcut.TOGGLE_SIDEBAR]: {
		name: 'Toggle Sidebar',
		keys: ['mod', 'shift', 'S'],
		category: 'Global',
		configurable: true
	},
	[Shortcut.CLOSE_MODAL]: {
		name: 'Close Modal',
		keys: ['Escape'],
		category: 'Global',
		configurable: true
	},

	//Input
	[Shortcut.FOCUS_INPUT]: {
		name: 'Focus Chat Input',
		keys: ['shift', 'Escape'],
		category: 'Input',
		configurable: true
	},
	[Shortcut.ACCEPT_AUTOCOMPLETE]: {
		name: 'Accept Autocomplete Generation\nJump to Prompt Variable',
		keys: ['Tab'],
		category: 'Input'
	},
	[Shortcut.PREVENT_FILE_CREATION]: {
		name: 'Prevent File Creation',
		keys: ['mod', 'shift', 'V'],
		category: 'Input',
		tooltip: 'Only active when "Paste Large Text as File" setting is toggled on.'
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
	[Shortcut.GENERATE_MESSAGE_PAIR]: {
		name: 'Generate Message Pair',
		keys: ['mod', 'shift', 'Enter'],
		category: 'Message',
		configurable: true,
		tooltip: 'Only active when the chat input is in focus.'
	},
	[Shortcut.REGENERATE_RESPONSE]: {
		name: 'Regenerate Response',
		keys: ['mod', 'R'],
		category: 'Message',
		configurable: true
	},
	[Shortcut.STOP_GENERATING]: {
		name: 'Stop Generating',
		keys: ['Escape'],
		category: 'Message',
		tooltip: 'Only active when the chat input is in focus and an LLM is generating a response.'
	},
	[Shortcut.NAVIGATE_PROMPT_HISTORY_UP]: {
		name: 'Edit Last Message',
		keys: ['ArrowUp'],
		category: 'Message',
		tooltip: 'Only can be triggered when the chat input is in focus.'
	},
	[Shortcut.COPY_LAST_RESPONSE]: {
		name: 'Copy Last Response',
		keys: ['mod', 'shift', 'C'],
		category: 'Message',
		configurable: true
	},
	[Shortcut.COPY_LAST_CODE_BLOCK]: {
		name: 'Copy Last Code Block',
		keys: ['mod', 'shift', ';'],
		category: 'Message',
		configurable: true
	},

	//Voice
	[Shortcut.TOGGLE_MUTE]: {
		name: 'Toggle Mute',
		keys: ['M'],
		category: 'Voice',
		tooltip: 'Only active during Voice Mode.'
	}
};
