/**
 * Scene Spec Extension for Marked
 *
 * Handles <scene_spec>...</scene_spec> blocks containing JSON scene specifications.
 * Used to render spatial scenes with entities, relations, and annotations.
 * Supports multiple tag names: scene_spec, scene-spec, scenespec
 */

// 지원하는 태그 이름 목록 (export하여 외부에서 확인 가능)
export const SCENE_SPEC_TAGS = ['scene_spec', 'scene-spec', 'scenespec'];

// 태그 이름들을 regex alternation 패턴으로 변환
function buildTagPattern(tags: string[]): string {
	return tags.map(tag => tag.replace(/-/g, '\\-')).join('|');
}

// 동적 regex 생성
const TAG_PATTERN = buildTagPattern(SCENE_SPEC_TAGS);
const SCENE_SPEC_REGEX = new RegExp(`^<(${TAG_PATTERN})>\\n?([\\s\\S]*?)\\n?<\\/(${TAG_PATTERN})>`);

export interface EntityAppearance {
	type: 'svg' | 'icon' | 'shape';
	viewBox?: string;
	svg?: string;
	icon?: string;
	shape?: 'circle' | 'rectangle' | 'triangle';
	color?: string;
}

export interface SceneEntity {
	id: string;
	kind: string;
	label: string;
	appearance?: EntityAppearance;
	position?: { x: number; y: number };
}

export interface SceneRelation {
	type: 'distance' | 'motion' | 'angle' | 'force' | 'connection';
	from?: string;
	to?: string;
	entity?: string;
	value?: string;
	direction?: string;
	label?: string;
}

export interface SceneAnnotation {
	type: 'value' | 'label' | 'formula';
	text: string;
	attachTo: string;
	position: 'top' | 'bottom' | 'left' | 'right';
	offset?: { x: number; y: number };
}

export interface SceneView {
	projection: '2d_side' | '2d_top' | '3d_isometric';
	orientation: 'left_to_right' | 'right_to_left' | 'top_to_bottom';
	zoom?: number;
}

export interface SceneSpec {
	type: 'scene';
	entities: SceneEntity[];
	relations?: SceneRelation[];
	annotations?: SceneAnnotation[];
	view?: SceneView;
	background?: string;
}

export interface SceneSpecToken {
	type: 'sceneSpec';
	raw: string;
	spec: SceneSpec | null;
	error?: string;
}

function sceneSpecTokenizer(src: string): SceneSpecToken | undefined {
	const match = SCENE_SPEC_REGEX.exec(src);

	if (match) {
		// match[1] = 여는 태그 이름, match[2] = 내용, match[3] = 닫는 태그 이름
		let jsonContent = match[2].trim();
		let spec: SceneSpec | null = null;
		let error: string | undefined;

		//console.log('[SceneSpec Tokenizer] Raw JSON:', jsonContent);

		try {
			spec = JSON.parse(jsonContent);
			console.log('[SceneSpec Tokenizer] Parsed spec:', spec);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Invalid JSON';
			console.error('[SceneSpec Tokenizer] Parse error:', error);
			console.error('[SceneSpec Tokenizer] Failed JSON:', jsonContent);
		}

		return {
			type: 'sceneSpec',
			raw: match[0],
			spec,
			error
		};
	}
}

function sceneSpecStart(src: string): number {
	// 모든 지원 태그 중 가장 먼저 나오는 위치 찾기
	let minIndex = -1;
	for (const tag of SCENE_SPEC_TAGS) {
		const index = src.indexOf(`<${tag}>`);
		if (index !== -1 && (minIndex === -1 || index < minIndex)) {
			minIndex = index;
		}
	}
	return minIndex;
}

function sceneSpecRenderer(token: SceneSpecToken): string {
	if (token.error) {
		return `<div class="scene-spec-error">Scene Spec Error: ${token.error}</div>`;
	}
	return `<div class="scene-spec" data-spec='${JSON.stringify(token.spec)}'></div>`;
}

function sceneSpecExtension() {
	return {
		name: 'sceneSpec',
		level: 'block' as const,
		start: sceneSpecStart,
		tokenizer: sceneSpecTokenizer,
		renderer: sceneSpecRenderer
	};
}

export default function (options = {}) {
	return {
		extensions: [sceneSpecExtension()]
	};
}
