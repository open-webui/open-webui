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
