export type Banner = {
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

export interface Theme {
  id: string;
  name: string;
  version?: string;
  author?: string;
  repository?: string;
  targetWebUIVersion?: string;
  base: 'light' | 'dark' | 'oled-dark';
  emoji?: string;
  metaThemeColor?: string;
  variables?: { [key: string]: string };
  particleConfig?: any;
  tsparticlesConfig?: any;
  animationScript?: string;
  animation?: {
    start: (canvas: HTMLCanvasElement) => void;
    stop: () => void;
  };
  css?: string;
  sourceUrl?: string;
  codeMirrorTheme?: string;
}
