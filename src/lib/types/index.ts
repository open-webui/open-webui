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

import type { IOptions } from '@tsparticles/engine';

export type ThemeVariable =
	| '--color-black'
	| '--color-white'
	| '--color-gray-50'
	| '--color-gray-100'
	| '--color-gray-200'
	| '--color-gray-300'
	| '--color-gray-400'
	| '--color-gray-500'
	| '--color-gray-600'
	| '--color-gray-700'
	| '--color-gray-800'
	| '--color-gray-850'
	| '--color-gray-900'
	| '--color-gray-950'
	| '--color-blue-100'
	| '--color-blue-200'
	| '--color-blue-300'
	| '--color-blue-400'
	| '--color-blue-500'
	| '--color-blue-600'
	| '--color-blue-700'
	| '--color-blue-800'
	| '--color-blue-900'
	| '--color-blue-950';

export interface Theme {
  id: string;
  name: string;
  description?: string;
  version?: string;
  author?: string;
  repository?: string;
  targetWebUIVersion?: string;
  base: 'light' | 'dark' | 'oled-dark' | 'her';
  emoji?: string;
  metaThemeColor?: string;
  systemBackgroundImageUrl?: string;
  systemBackgroundImageDarken?: number;
  chatBackgroundImageUrl?: string;
  chatBackgroundImageDarken?: number;
  variables?: Partial<Record<ThemeVariable, string>>;
  gradient?: {
    enabled: boolean;
    colors: string[];
    direction: number;
    intensity: number;
  };
  tsparticlesConfig?: IOptions;
  animationScript?: string;
  animation?: {
    start: (canvas: HTMLCanvasElement) => void;
    stop: () => void;
  };
  css?: string;
  sourceUrl?: string;
  codeMirrorTheme?: string;
  toggles?: {
    cssVariables?: boolean;
    customCss?: boolean;
    animationScript?: boolean;
    tsParticles?: boolean;
    gradient?: boolean;
    systemBackgroundImage?: boolean;
    chatBackgroundImage?: boolean;
  };
}
