/**
 * Flow Spec Extension for Marked
 *
 * Handles <flow-spec>...</flow-spec> blocks containing JSON flowchart specifications.
 * Used to render flowcharts with nodes (oval, rectangle, diamond) and edges.
 * Supports multiple tag names: flow_spec, base-flow-spec, flow-spec, flowspec
 */

// 지원하는 태그 이름 목록 (export하여 외부에서 확인 가능)
export const FLOW_SPEC_TAGS = ['flow_spec', 'base-flow-spec', 'flow-spec', 'flowspec'];

// 태그 이름들을 regex alternation 패턴으로 변환
function buildTagPattern(tags: string[]): string {
	return tags.map(tag => tag.replace(/-/g, '\\-')).join('|');
}

// 동적 regex 생성
const TAG_PATTERN = buildTagPattern(FLOW_SPEC_TAGS);
const FLOW_SPEC_REGEX = new RegExp(`^<(${TAG_PATTERN})>\\n?([\\s\\S]*?)\\n?<\\/(${TAG_PATTERN})>`);

export interface FlowNode {
	id: string;
	label: string;
	shape: 'oval' | 'rectangle' | 'diamond';
}

export interface FlowEdge {
	from: string;
	to: string;
	label?: string;
	condition?: string;
}

export interface FlowLayout {
	direction: 'TB' | 'LR' | 'BT' | 'RL';
}

export interface FlowSpec {
	nodes: FlowNode[];
	edges: FlowEdge[];
	layout?: FlowLayout;
}

export interface FlowSpecToken {
	type: 'flowSpec';
	raw: string;
	spec: FlowSpec | null;
	error?: string;
}

function flowSpecTokenizer(src: string): FlowSpecToken | undefined {
	const match = FLOW_SPEC_REGEX.exec(src);

	if (match) {
		// match[1] = 여는 태그 이름, match[2] = 내용, match[3] = 닫는 태그 이름
		let jsonContent = match[2].trim();
		let spec: FlowSpec | null = null;
		let error: string | undefined;

		//console.log('[FlowSpec Tokenizer] Raw JSON:', jsonContent);

		try {
			spec = JSON.parse(jsonContent);
			console.log('[FlowSpec Tokenizer] Parsed spec:', spec);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Invalid JSON';
			console.error('[FlowSpec Tokenizer] Parse error:', error);
			console.error('[FlowSpec Tokenizer] Failed JSON:', jsonContent);
		}

		return {
			type: 'flowSpec',
			raw: match[0],
			spec,
			error
		};
	}
}

function flowSpecStart(src: string): number {
	// 모든 지원 태그 중 가장 먼저 나오는 위치 찾기
	let minIndex = -1;
	for (const tag of FLOW_SPEC_TAGS) {
		const index = src.indexOf(`<${tag}>`);
		if (index !== -1 && (minIndex === -1 || index < minIndex)) {
			minIndex = index;
		}
	}
	return minIndex;
}

function flowSpecRenderer(token: FlowSpecToken): string {
	// The actual rendering is handled by the Svelte component
	// This renderer returns a placeholder that will be replaced
	if (token.error) {
		return `<div class="flow-spec-error">Flow Spec Error: ${token.error}</div>`;
	}
	return `<div class="flow-spec" data-spec='${JSON.stringify(token.spec)}'></div>`;
}

function flowSpecExtension() {
	return {
		name: 'flowSpec',
		level: 'block' as const,
		start: flowSpecStart,
		tokenizer: flowSpecTokenizer,
		renderer: flowSpecRenderer
	};
}

export default function (options = {}) {
	return {
		extensions: [flowSpecExtension()]
	};
}
