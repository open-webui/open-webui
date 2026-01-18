/**
 * Graph Spec Extension for Marked
 *
 * Handles <graph_spec>...</graph_spec> blocks containing JSON graph specifications.
 * Used to render mathematical function graphs using math.js + Plotly.js
 * Supports multiple tag names: graph_spec, graph-spec, graphspec
 */

// 지원하는 태그 이름 목록 (export하여 외부에서 확인 가능)
export const GRAPH_SPEC_TAGS = ['graph_spec', 'graph-spec', 'graphspec', 'base-graph-spec'];

// 태그 이름들을 regex alternation 패턴으로 변환
function buildTagPattern(tags: string[]): string {
	return tags.map(tag => tag.replace(/-/g, '\\-')).join('|');
}

// 동적 regex 생성
const TAG_PATTERN = buildTagPattern(GRAPH_SPEC_TAGS);
const GRAPH_SPEC_REGEX = new RegExp(`^<(${TAG_PATTERN})>\\n?([\\s\\S]*?)\\n?<\\/(${TAG_PATTERN})>`);

// 2D 도메인 (단순 튜플) 또는 3D 도메인 (객체)
export type Domain2D = [number, number];
export type Domain3D = {
	x?: [number, number];
	y?: [number, number];
	z?: [number, number]; // 3D vector field용
	u?: [number, number];
	v?: [number, number];
	t?: [number, number];
};

// 2D 샘플링 (숫자) 또는 3D 샘플링 (객체)
export type Sampling2D = number;
export type Sampling3D = {
	x?: number;
	y?: number;
	z?: number; // 3D vector field용
	u?: number;
	v?: number;
	t?: number;
};

export interface GraphSpecLayer {
	type: 'function_2d' | 'parametric_2d' | 'function_parametric_2d' | 'phase_plane' | 'scatter_2d' | 'point_2d' | 'line_2d' |
		'heatmap_2d' | 'contour_2d' | 'implicit_2d' |
		'function_3d' | 'parametric_3d' | 'scatter_3d' | 'point_3d' | 'histogram_2d' | 'vector_2d' | 'vector_field_3d' |
		'pie_2d' | 'bar_2d';
	expression?: string | { x: string; y: string; z?: string }; // 문자열 또는 객체 형식 지원
	expressions?: string | string[];
	field?: { dx?: string; dy?: string; dz?: string }; // vector field용 (phase_plane, vector_field_3d)
	domain?: Domain2D | Domain3D;
	sampling?: Sampling2D | Sampling3D;
	data?: any; // 2D/3D 데이터 또는 vector_2d의 {start, end, color, width}[] 형식
	coordinates?: [number, number][]; // point_2d용 좌표 배열
	position?: [number, number, number]; // point_3d용 위치
	label?: string; // point_3d용 라벨
	binEdges?: number[]; // histogram_2d용 구간 경계값
	counts?: number[]; // histogram_2d용 각 구간의 빈도수
	labels?: string[]; // pie_2d용 레이블 배열
	percentages?: number[]; // pie_2d용 백분율 배열
	categories?: string[]; // bar_2d용 카테고리 배열
	values?: number[]; // bar_2d용 값 배열
	orientation?: 'vertical' | 'horizontal'; // bar_2d용 방향
	style?: {
		color?: string | string[];
		colorMap?: string; // 3D용 컬러맵 (viridis, plasma 등)
		lineWidth?: number;
		lineStyle?: 'solid' | 'dashed' | 'dotted';
		marker?: 'circle' | 'square' | 'triangle' | 'diamond' | 'cross' | 'sphere';
		size?: number;
		opacity?: number;
		barGap?: number; // histogram_2d용 막대 간격 (0~1)
		width?: number; // vector_2d용 선 두께
		barWidth?: number; // bar_2d용 막대 너비 (0~1)
		glyph?: 'arrow'; // vector field용 glyph 타입
		scale?: number; // vector field용 arrow 길이 스케일
		labelFormat?: 'percent' | 'value'; // pie_2d용 레이블 형식
		ncontours?: number; // contour_2d, implicit_2d용 등고선 레벨 수
		showColorbar?: boolean; // heatmap_2d, contour_2d용 컬러바 표시 여부
	};
}

export interface GraphSpec {
	type: 'function_2d' | 'parametric_2d' | 'function_parametric_2d' | 'phase_plane' | 'scatter_2d' | 'composite_2d' | 'multi_scatter_2d' | 'line_2d' |
		'heatmap_2d' | 'contour_2d' | 'implicit_2d' |
		'function_3d' | 'parametric_3d' | 'scatter_3d' | 'composite_3d' | 'cartesian' | 'histogram_2d' | 'vector_2d' | 'vector_field_3d' |
		'pie_2d' | 'bar_2d';
	expression?: string | { x: string; y: string; z?: string }; // 문자열 또는 객체 형식 지원
	expressions?: string | string[];
	field?: { dx?: string; dy?: string; dz?: string }; // vector field용 (phase_plane, vector_field_3d)
	domain?: Domain2D | Domain3D;
	sampling?: Sampling2D | Sampling3D;
	data?: any; // 2D/3D 데이터 또는 vector_2d의 {start, end, color, width}[] 형식
	binEdges?: number[]; // histogram_2d용 구간 경계값
	counts?: number[]; // histogram_2d용 각 구간의 빈도수
	labels?: string[]; // pie_2d용 레이블 배열
	percentages?: number[]; // pie_2d용 백분율 배열
	categories?: string[]; // bar_2d용 카테고리 배열
	values?: number[]; // bar_2d용 값 배열
	orientation?: 'vertical' | 'horizontal'; // bar_2d용 방향
	layers?: GraphSpecLayer[]; // composite용 레이어
	annotations?: Annotation[]; // 텍스트 라벨 등
	style?: {
		color?: string | string[];
		colorMap?: string; // 3D용 컬러맵 (viridis, plasma 등)
		lineWidth?: number;
		lineStyle?: 'solid' | 'dashed' | 'dotted';
		marker?: 'circle' | 'square' | 'triangle' | 'diamond' | 'cross' | 'sphere';
		size?: number;
		opacity?: number;
		barGap?: number; // histogram_2d용 막대 간격 (0~1)
		width?: number; // vector_2d용 선 두께
		barWidth?: number; // bar_2d용 막대 너비 (0~1)
		glyph?: 'arrow'; // vector field용 glyph 타입
		scale?: number; // vector field용 arrow 길이 스케일
		labelFormat?: 'percent' | 'value'; // pie_2d용 레이블 형식
		ncontours?: number; // contour_2d, implicit_2d용 등고선 레벨 수
		showColorbar?: boolean; // heatmap_2d, contour_2d용 컬러바 표시 여부
	};
	axis?: {
		xLabel?: string;
		yLabel?: string;
		zLabel?: string; // 3D용
		xRange?: [number, number]; // x축 범위
		yRange?: [number, number]; // y축 범위
		zRange?: [number, number]; // 3D용 z축 범위
		grid?: boolean;
	};
	meta?: {
		title?: string;
		caption?: string;
	};
}

export interface Annotation {
	type: 'label' | 'arrow' | 'line';
	text?: string; // label용
	position?: { x: number; y: number }; // label용 위치
	start?: [number, number]; // arrow/line용 시작점
	end?: [number, number]; // arrow/line용 끝점
	style?: {
		color?: string;
		fontSize?: number;
		anchor?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' | 'center';
		opacity?: number;
		lineWidth?: number;
	};
}

export interface GraphSpecToken {
	type: 'graphSpec';
	raw: string;
	spec: GraphSpec | null;
	error?: string;
	rawJson?: string; // 원본 JSON 내용 (파싱 실패 시 디버깅용)
}

function graphSpecTokenizer(src: string): GraphSpecToken | undefined {
	const match = GRAPH_SPEC_REGEX.exec(src);

	if (match) {
		// match[1] = 여는 태그 이름, match[2] = 내용, match[3] = 닫는 태그 이름
		let jsonContent = match[2].trim();
		let spec: GraphSpec | null = null;
		let error: string | undefined;

		console.log('[GraphSpec Tokenizer] Raw JSON:', jsonContent);

		// 1. Remove markdown code block wrapper if present (```json ... ``` or ``` ... ```)
		if (jsonContent.startsWith('```')) {
			jsonContent = jsonContent.replace(/^```(?:json)?\s*\n?/, '');
			jsonContent = jsonContent.replace(/\n?```\s*$/, '');
			jsonContent = jsonContent.trim();
			console.log('[GraphSpec Tokenizer] After removing code block wrapper:', jsonContent);
		}

		// 2. Convert ** to ^ for mathjs compatibility (Python-style power operator)
		// Only convert within string values (expression fields)
		const stringPlaceholders: string[] = [];
		jsonContent = jsonContent.replace(/"(?:[^"\\]|\\[\\"/bfnrt]|\\u[0-9a-fA-F]{4})*"/g, (match) => {
			// Convert ** to ^ within the string
			const converted = match.replace(/\*\*/g, '^');
			stringPlaceholders.push(converted);
			return `__STRING_${stringPlaceholders.length - 1}__`;
		});

		// Restore strings
		jsonContent = jsonContent.replace(/__STRING_(\d+)__/g, (_, idx) => {
			return stringPlaceholders[parseInt(idx)];
		});

		console.log('[GraphSpec Tokenizer] Processed JSON:', jsonContent);

		try {
			let parsed = JSON.parse(jsonContent);

			// Handle wrapper format: { "vector_field_3d": { "type": "vector_field_3d", ... } }
			// or { "function_2d": { "type": "function_2d", ... } } etc.
			// If parsed object has a single key that matches a known type, unwrap it
			const knownTypes = [
				'function_2d', 'parametric_2d', 'function_parametric_2d', 'phase_plane', 'scatter_2d', 'composite_2d',
				'multi_scatter_2d', 'line_2d', 'heatmap_2d', 'contour_2d', 'implicit_2d',
				'function_3d', 'parametric_3d', 'scatter_3d',
				'composite_3d', 'cartesian', 'histogram_2d', 'vector_2d', 'vector_field_3d', 'pie_2d', 'bar_2d'
			];
			const keys = Object.keys(parsed);
			if (keys.length === 1 && knownTypes.includes(keys[0]) && typeof parsed[keys[0]] === 'object') {
				console.log('[GraphSpec Tokenizer] Unwrapping wrapper format:', keys[0]);
				parsed = parsed[keys[0]];
			}

			spec = parsed as GraphSpec;
			console.log('[GraphSpec Tokenizer] Parsed spec:', spec);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Invalid JSON';
			console.error('[GraphSpec Tokenizer] Parse error:', error);
			console.error('[GraphSpec Tokenizer] Failed JSON:', jsonContent);
		}

		return {
			type: 'graphSpec',
			raw: match[0],
			spec,
			error,
			rawJson: error ? match[2].trim() : undefined // 파싱 실패 시 원본 JSON 포함
		};
	}
}

function graphSpecStart(src: string): number {
	// 모든 지원 태그 중 가장 먼저 나오는 위치 찾기
	let minIndex = -1;
	for (const tag of GRAPH_SPEC_TAGS) {
		const index = src.indexOf(`<${tag}>`);
		if (index !== -1 && (minIndex === -1 || index < minIndex)) {
			minIndex = index;
		}
	}
	return minIndex;
}

function graphSpecRenderer(token: GraphSpecToken): string {
	// The actual rendering is handled by the Svelte component
	// This renderer returns a placeholder that will be replaced
	if (token.error) {
		return `<div class="graph-spec-error">Graph Spec Error: ${token.error}</div>`;
	}
	return `<div class="graph-spec" data-spec='${JSON.stringify(token.spec)}'></div>`;
}

function graphSpecExtension() {
	return {
		name: 'graphSpec',
		level: 'block' as const,
		start: graphSpecStart,
		tokenizer: graphSpecTokenizer,
		renderer: graphSpecRenderer
	};
}

export default function (options = {}) {
	return {
		extensions: [graphSpecExtension()]
	};
}
