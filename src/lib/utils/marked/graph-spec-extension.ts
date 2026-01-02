/**
 * Graph Spec Extension for Marked
 *
 * Handles <graph_spec>...</graph_spec> blocks containing JSON graph specifications.
 * Used to render mathematical function graphs using math.js + Plotly.js
 */

// 2D 도메인 (단순 튜플) 또는 3D 도메인 (객체)
export type Domain2D = [number, number];
export type Domain3D = {
	x?: [number, number];
	y?: [number, number];
	u?: [number, number];
	v?: [number, number];
	t?: [number, number];
};

// 2D 샘플링 (숫자) 또는 3D 샘플링 (객체)
export type Sampling2D = number;
export type Sampling3D = {
	x?: number;
	y?: number;
	u?: number;
	v?: number;
	t?: number;
};

export interface GraphSpecLayer {
	type: 'function_2d' | 'parametric_2d' | 'phase_plane' | 'scatter_2d' | 'point_2d' |
		'function_3d' | 'parametric_3d' | 'scatter_3d' | 'point_3d' | 'histogram_2d' | 'vector_2d';
	expression?: string; // function_3d용 단일 표현식
	expressions?: string | string[];
	domain?: Domain2D | Domain3D;
	sampling?: Sampling2D | Sampling3D;
	data?: any; // 2D/3D 데이터 또는 vector_2d의 {start, end, color, width}[] 형식
	coordinates?: [number, number][]; // point_2d용 좌표 배열
	position?: [number, number, number]; // point_3d용 위치
	label?: string; // point_3d용 라벨
	binEdges?: number[]; // histogram_2d용 구간 경계값
	counts?: number[]; // histogram_2d용 각 구간의 빈도수
	style?: {
		color?: string | string[];
		colorMap?: string; // 3D용 컬러맵 (viridis, plasma 등)
		lineWidth?: number;
		lineStyle?: 'solid' | 'dashed' | 'dotted';
		marker?: 'circle' | 'square' | 'triangle' | 'diamond' | 'cross' | 'sphere';
		size?: number;
		opacity?: number;
		barGap?: number; // histogram_2d용 막대 간격 (0~1)
	};
}

export interface GraphSpec {
	type: 'function_2d' | 'parametric_2d' | 'phase_plane' | 'scatter_2d' | 'composite_2d' | 'multi_scatter_2d' |
		'function_3d' | 'parametric_3d' | 'scatter_3d' | 'composite_3d' | 'cartesian' | 'histogram_2d' | 'vector_2d';
	expression?: string; // function_3d용 단일 표현식
	expressions?: string | string[];
	domain?: Domain2D | Domain3D;
	sampling?: Sampling2D | Sampling3D;
	data?: any; // 2D/3D 데이터 또는 vector_2d의 {start, end, color, width}[] 형식
	binEdges?: number[]; // histogram_2d용 구간 경계값
	counts?: number[]; // histogram_2d용 각 구간의 빈도수
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
	};
	axis?: {
		xLabel?: string;
		yLabel?: string;
		zLabel?: string; // 3D용
		xRange?: [number, number]; // histogram_2d용 x축 범위
		yRange?: [number, number]; // histogram_2d용 y축 범위
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
}

function graphSpecTokenizer(src: string): GraphSpecToken | undefined {
	const regex = /^<graph_spec>\n?([\s\S]*?)\n?<\/graph_spec>/;
	const match = regex.exec(src);

	if (match) {
		let jsonContent = match[1].trim();
		let spec: GraphSpec | null = null;
		let error: string | undefined;

		console.log('[GraphSpec Tokenizer] Raw JSON:', jsonContent);

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
			spec = JSON.parse(jsonContent);
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
			error
		};
	}
}

function graphSpecStart(src: string): number {
	const index = src.indexOf('<graph_spec>');
	return index !== -1 ? index : -1;
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
