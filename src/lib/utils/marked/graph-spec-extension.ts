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
	type: 'function_2d' | 'parametric_2d' | 'phase_plane' | 'scatter_2d' |
		'function_3d' | 'parametric_3d' | 'scatter_3d';
	expression?: string; // function_3d용 단일 표현식
	expressions?: string | string[];
	domain?: Domain2D | Domain3D;
	sampling?: Sampling2D | Sampling3D;
	data?: [number, number][] | [number, number, number][]; // 2D 또는 3D 데이터
	style?: {
		color?: string | string[];
		colorMap?: string; // 3D용 컬러맵 (viridis, plasma 등)
		lineWidth?: number;
		lineStyle?: 'solid' | 'dashed' | 'dotted';
		marker?: 'circle' | 'square' | 'triangle' | 'diamond' | 'cross' | 'sphere';
		size?: number;
		opacity?: number;
	};
}

export interface GraphSpec {
	type: 'function_2d' | 'parametric_2d' | 'phase_plane' | 'scatter_2d' | 'composite_2d' | 'multi_scatter_2d' |
		'function_3d' | 'parametric_3d' | 'scatter_3d' | 'composite_3d';
	expression?: string; // function_3d용 단일 표현식
	expressions?: string | string[];
	domain?: Domain2D | Domain3D;
	sampling?: Sampling2D | Sampling3D;
	data?: [number, number][] | [number, number, number][]; // 2D 또는 3D 데이터
	layers?: GraphSpecLayer[]; // composite용 레이어
	style?: {
		color?: string | string[];
		colorMap?: string; // 3D용 컬러맵 (viridis, plasma 등)
		lineWidth?: number;
		lineStyle?: 'solid' | 'dashed' | 'dotted';
		marker?: 'circle' | 'square' | 'triangle' | 'diamond' | 'cross' | 'sphere';
		size?: number;
		opacity?: number;
	};
	axis?: {
		xLabel?: string;
		yLabel?: string;
		zLabel?: string; // 3D용
		grid?: boolean;
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
