export type BannerType = 'info' | 'success' | 'warning' | 'error' | 'html';

export type Banner = {
	id: string;
	type: BannerType;
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
