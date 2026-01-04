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
	type: 'function_2d' | 'parametric_2d' | 'phase_plane' | 'scatter_2d' | 'point_2d' | 'line_2d' |
		'function_3d' | 'parametric_3d' | 'scatter_3d' | 'point_3d' | 'histogram_2d' | 'vector_2d' | 'vector_field_3d' |
		'pie_2d' | 'bar_2d';
	expression?: string; // function_3d용 단일 표현식
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
	};
}

export interface GraphSpec {
	type: 'function_2d' | 'parametric_2d' | 'phase_plane' | 'scatter_2d' | 'composite_2d' | 'multi_scatter_2d' | 'line_2d' |
		'function_3d' | 'parametric_3d' | 'scatter_3d' | 'composite_3d' | 'cartesian' | 'histogram_2d' | 'vector_2d' | 'vector_field_3d' |
		'pie_2d' | 'bar_2d';
	expression?: string; // function_3d용 단일 표현식
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

		//console.log('[GraphSpec Tokenizer] Raw JSON:', jsonContent);

		// 문자열 외부에서만 수학 상수 변환 (문자열 내용은 보존)
		// 문자열을 임시로 플레이스홀더로 치환 후 복원
		const stringPlaceholders: string[] = [];
		jsonContent = jsonContent.replace(/"(?:[^"\\]|\\.)*"/g, (match) => {
			stringPlaceholders.push(match);
			return `__STRING_${stringPlaceholders.length - 1}__`;
		});

		// JSON 주석 제거 (문자열 외부의 // 주석 제거)
		jsonContent = jsonContent.replace(/\/\/[^\n]*/g, '');

		// 수학 표현식을 숫자로 변환 (PI, E 등) - 문자열 외부만
		// 곱셈: num * PI, PI * num
		jsonContent = jsonContent.replace(/(\d+(?:\.\d+)?)\s*\*\s*PI/gi, (_, num) => {
			return String(parseFloat(num) * Math.PI);
		});
		jsonContent = jsonContent.replace(/PI\s*\*\s*(\d+(?:\.\d+)?)/gi, (_, num) => {
			return String(parseFloat(num) * Math.PI);
		});
		// 나눗셈: PI / num
		jsonContent = jsonContent.replace(/PI\s*\/\s*(\d+(?:\.\d+)?)/gi, (_, num) => {
			return String(Math.PI / parseFloat(num));
		});
		// 뺄셈: PI - num (반드시 PI 치환 전에 처리)
		jsonContent = jsonContent.replace(/PI\s*-\s*(\d+(?:\.\d+)?)/gi, (_, num) => {
			return String(Math.PI - parseFloat(num));
		});
		// 덧셈: PI + num
		jsonContent = jsonContent.replace(/PI\s*\+\s*(\d+(?:\.\d+)?)/gi, (_, num) => {
			return String(Math.PI + parseFloat(num));
		});
		// 뺄셈: num - PI
		jsonContent = jsonContent.replace(/(\d+(?:\.\d+)?)\s*-\s*PI/gi, (_, num) => {
			return String(parseFloat(num) - Math.PI);
		});
		// 덧셈: num + PI
		jsonContent = jsonContent.replace(/(\d+(?:\.\d+)?)\s*\+\s*PI/gi, (_, num) => {
			return String(parseFloat(num) + Math.PI);
		});
		// 단독 PI, E
		jsonContent = jsonContent.replace(/\bPI\b/gi, String(Math.PI));
		jsonContent = jsonContent.replace(/\bE\b/g, String(Math.E));

		// 숫자 * 숫자 형태의 간단한 곱셈 연산 처리 (예: 2.5 * 3.14159265)
		jsonContent = jsonContent.replace(/(\d+(?:\.\d+)?)\s*\*\s*(\d+(?:\.\d+)?)/g, (_, a, b) => {
			return String(parseFloat(a) * parseFloat(b));
		});

		// -숫자 형태 (음수) 처리: 이미 JSON에서 지원하므로 별도 처리 불필요

		// 문자열 복원
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
				'function_2d', 'parametric_2d', 'phase_plane', 'scatter_2d', 'composite_2d',
				'multi_scatter_2d', 'line_2d', 'function_3d', 'parametric_3d', 'scatter_3d',
				'composite_3d', 'cartesian', 'histogram_2d', 'vector_2d', 'vector_field_3d'
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
