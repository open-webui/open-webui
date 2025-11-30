export type Banner = {
	id: string;
	type: string;
	title?: string;
	content: string;
	url?: string;
	dismissible?: boolean;
	timestamp: number;
};

export type WatermarkConfig = {
	enabled: boolean;
	useModelIcon: boolean;
	customUrl?: string;
	opacity: number;
	position: 'center' | 'bottom-right' | 'bottom-center';
	size: string;
};

export type BadgeConfig = {
	enabled: boolean;
	size: string;
};

export type ModelColorMapping = {
	pattern: string;
	color: string;
	priority: number;
	watermark?: WatermarkConfig;
	badge?: BadgeConfig;
};

export type ModelColorsConfig = {
	enabled: boolean;
	defaultColor: string;
	mappings: ModelColorMapping[];
};

export enum TTS_RESPONSE_SPLIT {
	PUNCTUATION = 'punctuation',
	PARAGRAPHS = 'paragraphs',
	NONE = 'none'
}
