/**
 * Graph Spec Extension for Marked
 *
 * Handles <graph_spec>...</graph_spec> blocks containing JSON graph specifications.
 * Used to render mathematical function graphs using math.js + Plotly.js
 */

export interface GraphSpecLayer {
	type: 'function_2d' | 'parametric_2d' | 'phase_plane' | 'scatter_2d';
	expressions?: string | string[];
	domain?: [number, number];
	sampling?: number;
	data?: [number, number][];
	style?: {
		color?: string | string[];
		lineWidth?: number;
		lineStyle?: 'solid' | 'dashed' | 'dotted';
		marker?: 'circle' | 'square' | 'triangle' | 'diamond' | 'cross';
		size?: number;
		opacity?: number;
	};
}

export interface GraphSpec {
	type: 'function_2d' | 'parametric_2d' | 'phase_plane' | 'scatter_2d' | 'composite_2d' | 'multi_scatter_2d';
	expressions?: string | string[];
	domain?: [number, number];
	sampling?: number;
	data?: [number, number][]; // scatter_2d용 데이터 포인트
	layers?: GraphSpecLayer[]; // composite_2d, multi_scatter_2d용 레이어
	style?: {
		color?: string | string[];
		lineWidth?: number;
		lineStyle?: 'solid' | 'dashed' | 'dotted';
		marker?: 'circle' | 'square' | 'triangle' | 'diamond' | 'cross';
		size?: number;
		opacity?: number;
	};
	axis?: {
		xLabel?: string;
		yLabel?: string;
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
		jsonContent = jsonContent.replace(/(\d+(?:\.\d+)?)\s*\*\s*PI/gi, (_, num) => {
			return String(parseFloat(num) * Math.PI);
		});
		jsonContent = jsonContent.replace(/PI\s*\*\s*(\d+(?:\.\d+)?)/gi, (_, num) => {
			return String(parseFloat(num) * Math.PI);
		});
		jsonContent = jsonContent.replace(/PI\s*\/\s*(\d+(?:\.\d+)?)/gi, (_, num) => {
			return String(Math.PI / parseFloat(num));
		});
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
