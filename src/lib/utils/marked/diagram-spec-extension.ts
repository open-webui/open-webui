/**
 * Diagram Spec Extension for Marked
 *
 * Handles <diagram-spec>...</diagram-spec> blocks containing JSON diagram specifications.
 * Used to render diagrams with nodes (rectangle, rounded_rectangle, diamond, ellipse) and edges.
 * Supports multiple tag names: diagram_spec, diagram-spec, diagramspec
 */

// 지원하는 태그 이름 목록 (export하여 외부에서 확인 가능)
export const DIAGRAM_SPEC_TAGS = ['diagram_spec', 'diagram-spec', 'diagramspec'];

// 태그 이름들을 regex alternation 패턴으로 변환
function buildTagPattern(tags: string[]): string {
	return tags.map(tag => tag.replace(/-/g, '\\-')).join('|');
}

// 동적 regex 생성
const TAG_PATTERN = buildTagPattern(DIAGRAM_SPEC_TAGS);
const DIAGRAM_SPEC_REGEX = new RegExp(`^<(${TAG_PATTERN})>\\n?([\\s\\S]*?)\\n?<\\/(${TAG_PATTERN})>`);

export interface DiagramNode {
	id: string;
	label: string;
	shape: 'rectangle' | 'rounded_rectangle' | 'diamond' | 'ellipse';
}

export interface DiagramEdge {
	from: string;
	to: string;
	label?: string;
	style?: 'solid' | 'dashed' | 'dotted';
}

export interface DiagramLayout {
	direction: 'TB' | 'LR' | 'BT' | 'RL';
}

export interface DiagramSpec {
	nodes: DiagramNode[];
	edges: DiagramEdge[];
	layout?: DiagramLayout;
}

export interface DiagramSpecToken {
	type: 'diagramSpec';
	raw: string;
	spec: DiagramSpec | null;
	error?: string;
}

function diagramSpecTokenizer(src: string): DiagramSpecToken | undefined {
	const match = DIAGRAM_SPEC_REGEX.exec(src);

	if (match) {
		// match[1] = 여는 태그 이름, match[2] = 내용, match[3] = 닫는 태그 이름
		let jsonContent = match[2].trim();
		let spec: DiagramSpec | null = null;
		let error: string | undefined;

		//console.log('[DiagramSpec Tokenizer] Raw JSON:', jsonContent);

		try {
			spec = JSON.parse(jsonContent);
			console.log('[DiagramSpec Tokenizer] Parsed spec:', spec);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Invalid JSON';
			console.error('[DiagramSpec Tokenizer] Parse error:', error);
			console.error('[DiagramSpec Tokenizer] Failed JSON:', jsonContent);
		}

		return {
			type: 'diagramSpec',
			raw: match[0],
			spec,
			error
		};
	}
}

function diagramSpecStart(src: string): number {
	// 모든 지원 태그 중 가장 먼저 나오는 위치 찾기
	let minIndex = -1;
	for (const tag of DIAGRAM_SPEC_TAGS) {
		const index = src.indexOf(`<${tag}>`);
		if (index !== -1 && (minIndex === -1 || index < minIndex)) {
			minIndex = index;
		}
	}
	return minIndex;
}

function diagramSpecRenderer(token: DiagramSpecToken): string {
	// The actual rendering is handled by the Svelte component
	// This renderer returns a placeholder that will be replaced
	if (token.error) {
		return `<div class="diagram-spec-error">Diagram Spec Error: ${token.error}</div>`;
	}
	return `<div class="diagram-spec" data-spec='${JSON.stringify(token.spec)}'></div>`;
}

function diagramSpecExtension() {
	return {
		name: 'diagramSpec',
		level: 'block' as const,
		start: diagramSpecStart,
		tokenizer: diagramSpecTokenizer,
		renderer: diagramSpecRenderer
	};
}

export default function (options = {}) {
	return {
		extensions: [diagramSpecExtension()]
	};
}
