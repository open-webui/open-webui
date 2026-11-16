export type Banner = {
	i18n?: Record<string, { content: string }>;
	id: string;
	type: string;
	title?: string;
	content: string;
	url?: string;
	dismissible?: boolean;
	timestamp: number;
};

export enum TTS_RESPONSE_SPLIT {
	PUNCTUATION = 'punctuation',
	PARAGRAPHS = 'paragraphs',
	NONE = 'none'
}

export type TerminalContext = {
	terminalId: string | null;
	currentDirectory: string;
	file?: import('$lib/apis/terminal').FilesystemFile | null;
};

export type AppLayoutContext = {
	openPageTab?: (tab: { href: string; label: string }) => void;
	initNewChat?: (preserveTabs?: boolean, keepDraft?: boolean, temporary?: boolean) => Promise<void>;
};

/** State of the chat a component is rendered in, so a side chat doesn't read the main chat's. */
export type ChatContext = {
	chatId: typeof import('$lib/stores').chatId;
	models: typeof import('$lib/stores').models;
	temporary: typeof import('$lib/stores').temporaryChat;
	audioQueue: typeof import('$lib/stores').audioQueue;
	submitPrompt?: (prompt: string) => void;
};

export type WorkspaceContext = {
	workspaceActions: import('svelte/store').Writable<import('$lib/stores').WorkspaceAction[]>;
	workspaceCounts: import('svelte/store').Writable<
		Record<import('$lib/stores').WorkspaceSection, number | null>
	>;
};
