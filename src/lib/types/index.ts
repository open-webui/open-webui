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
	initNewChat?: (preserveTabs?: boolean, keepDraft?: boolean) => Promise<void>;
};

export type WorkspaceContext = {
	workspaceActions: import('svelte/store').Writable<import('$lib/stores').WorkspaceAction[]>;
	workspaceCounts: import('svelte/store').Writable<
		Record<import('$lib/stores').WorkspaceSection, number | null>
	>;
};
