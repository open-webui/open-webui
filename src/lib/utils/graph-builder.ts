/**
 * Graph Builder Utilities
 *
 * 공통 그래프 빌딩 로직을 통합 관리
 * FunctionGraph.svelte (썸네일)와 GraphPreviewModal.svelte (모달)에서 공유
 */

import { create, all } from 'mathjs';
import type { GraphSpec, GraphSpecLayer, Domain3D, Sampling3D } from '$lib/utils/marked/graph-spec-extension';

// ========== Bessel Functions ==========

// Bessel function J0(x) - 제1종 0차 베셀 함수
function besselJ0(x: number): number {
	if (x === 0) return 1;

	const ax = Math.abs(x);

	// 작은 x에 대한 급수 전개 (|x| < 8)
	if (ax < 8) {
		const y = x * x;
		let result = 1;
		let term = 1;
		for (let k = 1; k < 30; k++) {
			term *= -y / (4 * k * k);
			result += term;
			if (Math.abs(term) < 1e-15 * Math.abs(result)) break;
		}
		return result;
	}

	// 큰 x에 대한 점근 전개 (|x| >= 8)
	const z = 8 / ax;
	const y = z * z;
	const xx = ax - 0.785398164; // π/4

	// P0 다항식 근사
	const p0 = 1 + y * (-0.1098628627e-2 + y * (0.2734510407e-4
		+ y * (-0.2073370639e-5 + y * 0.2093887211e-6)));

	// Q0 다항식 근사
	const q0 = -0.1562499995e-1 + y * (0.1430488765e-3
		+ y * (-0.6911147651e-5 + y * (0.7621095161e-6
		- y * 0.934935152e-7)));

	return Math.sqrt(0.636619772 / ax) * (p0 * Math.cos(xx) - z * q0 * Math.sin(xx));
}

// Bessel function J1(x) - 제1종 1차 베셀 함수
function besselJ1(x: number): number {
	const ax = Math.abs(x);

	if (ax === 0) return 0;

	// 작은 x에 대한 급수 전개 (|x| < 8)
	if (ax < 8) {
		const y = x * x;
		let result = x / 2;
		let term = x / 2;
		for (let k = 1; k < 30; k++) {
			term *= -y / (4 * k * (k + 1));
			result += term;
			if (Math.abs(term) < 1e-15 * Math.abs(result)) break;
		}
		return result;
	}

	// 큰 x에 대한 점근 전개 (|x| >= 8)
	const z = 8 / ax;
	const y = z * z;
	const xx = ax - 2.356194491; // 3π/4

	// P1 다항식 근사
	const p1 = 1 + y * (0.183105e-2 + y * (-0.3516396496e-4
		+ y * (0.2457520174e-5 + y * (-0.240337019e-6))));

	// Q1 다항식 근사
	const q1 = 0.04687499995 + y * (-0.2002690873e-3
		+ y * (0.8449199096e-5 + y * (-0.88228987e-6
		+ y * 0.105787412e-6)));

	const result = Math.sqrt(0.636619772 / ax) * (p1 * Math.cos(xx) - z * q1 * Math.sin(xx));
	return x < 0 ? -result : result;
}

// General Bessel function Jn(n, x) - 제1종 n차 베셀 함수
function besselJn(n: number, x: number): number {
	n = Math.floor(n); // n은 정수여야 함

	if (n === 0) return besselJ0(x);
	if (n === 1) return besselJ1(x);
	if (n < 0) return (n % 2 === 0 ? 1 : -1) * besselJn(-n, x);
	if (x === 0) return 0;

	const ax = Math.abs(x);

	// 작은 n과 큰 x에 대한 상향 재귀
	if (ax > n) {
		let j0 = besselJ0(ax);
		let j1 = besselJ1(ax);
		let jn = 0;

		for (let i = 1; i < n; i++) {
			jn = (2 * i / ax) * j1 - j0;
			j0 = j1;
			j1 = jn;
		}

		return x < 0 && n % 2 === 1 ? -jn : jn;
	}

	// Miller의 하향 재귀 알고리즘
	const m = Math.floor((n + Math.floor(Math.sqrt(40 * n))) / 2) * 2;
	let jnp1 = 0;
	let jn = 1;
	let sum = 0;

	for (let j = m; j > 0; j--) {
		const jnm1 = (2 * j / ax) * jn - jnp1;
		jnp1 = jn;
		jn = jnm1;

		if (j % 2 === 0) sum += 2 * jn;
		if (j === n) {
			const ans = jn;
			// 정규화
			const scale = besselJ0(ax) / (sum - jn);
			return x < 0 && n % 2 === 1 ? -ans * scale : ans * scale;
		}
	}

	return 0;
}

// ========== Gamma Function ==========

// Gamma function Γ(z) - Lanczos approximation
function gamma(z: number): number {
	// Lanczos approximation for gamma function
	const g = 7;
	const C = [
		0.99999999999980993,
		676.5203681218851,
		-1259.1392167224028,
		771.32342877765313,
		-176.61502916214059,
		12.507343278686905,
		-0.13857109526572012,
		9.9843695780195716e-6,
		1.5056327351493116e-7
	];

	if (z < 0.5) {
		return Math.PI / (Math.sin(Math.PI * z) * gamma(1 - z));
	}

	z -= 1;
	let x = C[0];
	for (let i = 1; i < g + 2; i++) {
		x += C[i] / (z + i);
	}

	const t = z + g + 0.5;
	return Math.sqrt(2 * Math.PI) * Math.pow(t, z + 0.5) * Math.exp(-t) * x;
}

// Factorial function n! - uses gamma(n+1)
function factorial(n: number): number {
	if (n < 0) return NaN;
	if (n === 0 || n === 1) return 1;
	return gamma(n + 1);
}

// ========== Error Function ==========

// Error function erf(x) - Abramowitz and Stegun approximation
function erf(x: number): number {
	// Constants for approximation
	const a1 =  0.254829592;
	const a2 = -0.284496736;
	const a3 =  1.421413741;
	const a4 = -1.453152027;
	const a5 =  1.061405429;
	const p  =  0.3275911;

	// Save the sign of x
	const sign = x >= 0 ? 1 : -1;
	x = Math.abs(x);

	// Abramowitz and Stegun formula 7.1.26
	const t = 1.0 / (1.0 + p * x);
	const y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-x * x);

	return sign * y;
}

// Complementary error function erfc(x) = 1 - erf(x)
function erfc(x: number): number {
	return 1 - erf(x);
}

// ========== Legendre Polynomials ==========

// Legendre polynomial P_n(x) - Bonnet's recursion
function legendreP(n: number, x: number): number {
	n = Math.floor(n); // Ensure n is integer

	if (n === 0) return 1;
	if (n === 1) return x;

	// Bonnet's recursion: (n+1)P_{n+1} = (2n+1)xP_n - nP_{n-1}
	let p0 = 1;
	let p1 = x;
	let pn = 0;

	for (let k = 1; k < n; k++) {
		pn = ((2 * k + 1) * x * p1 - k * p0) / (k + 1);
		p0 = p1;
		p1 = pn;
	}

	return pn;
}

// Create custom mathjs instance with special functions and constants
const math = create(all);
math.import({
	// Bessel functions
	jn: besselJn,
	j0: besselJ0,
	j1: besselJ1,
	besselj: besselJn,
	besselJ: besselJn,

	// Gamma functions
	gamma: gamma,
	factorial: factorial,

	// Error functions
	erf: erf,
	erfc: erfc,

	// Legendre polynomials
	legendreP: legendreP,

	// Mathematical constants (uppercase aliases for compatibility)
	PI: Math.PI,
	E: Math.E
}, { override: true });

// Export the compile function to use our custom math instance
// This ensures all graph expressions can use Bessel functions and custom constants
export const compile = (expr: string) => math.compile(expr);

// ========== Types ==========

export type LayerSpec = GraphSpec | GraphSpecLayer;

// ========== Helper Functions ==========

// expressions를 배열로 정규화 (expression 또는 expressions 지원)
// expression 객체 형식 {x: "...", y: "..."} 또는 {x: "...", y: "...", z: "..."} 도 지원
export function normalizeExpressions(layer: LayerSpec): string[] {
	// expression (singular) 체크
	if (layer.expression) {
		// 배열 형식: ["expr1", "expr2", ...]
		if (Array.isArray(layer.expression)) {
			return layer.expression as string[];
		}
		// 객체 형식: {x: "...", y: "..."} 또는 {x: "...", y: "...", z: "..."}
		if (typeof layer.expression === 'object' && layer.expression !== null) {
			const exprObj = layer.expression as { x?: string; y?: string; z?: string };
			if (exprObj.x !== undefined && exprObj.y !== undefined) {
				if (exprObj.z !== undefined) {
					return [exprObj.x, exprObj.y, exprObj.z];
				}
				return [exprObj.x, exprObj.y];
			}
		}
		// 문자열 형식
		if (typeof layer.expression === 'string') {
			return [layer.expression];
		}
	}
	// expressions (plural) 체크
	if (!layer.expressions) return [];
	return Array.isArray(layer.expressions) ? layer.expressions : [layer.expressions];
}

// colors를 배열로 정규화
export function normalizeColors(layer: LayerSpec): string[] {
	if (!layer.style?.color) return [];
	return Array.isArray(layer.style.color) ? layer.style.color : [layer.style.color];
}

// lineStyle을 Plotly dash 형식으로 변환
export function getLineDash(lineStyle?: string): string | undefined {
	switch (lineStyle) {
		case 'dashed': return 'dash';
		case 'dotted': return 'dot';
		default: return undefined;
	}
}

// marker 스타일 매핑
export const markerSymbolMap: Record<string, string> = {
	circle: 'circle',
	square: 'square',
	triangle: 'triangle-up',
	diamond: 'diamond',
	cross: 'cross'
};

// 2D 도메인 추출 헬퍼 (배열, 객체 {x: [...]}, 또는 {min, max} 형식 지원)
export function getDomain2D(domain: any, defaultVal: [number, number] = [-10, 10]): [number, number] {
	if (!domain) return defaultVal;
	// 배열 형식: [-2, 2]
	if (Array.isArray(domain)) return domain as [number, number];
	// 객체 형식: { x: [-2, 2] }
	if (domain.x && Array.isArray(domain.x)) return domain.x as [number, number];
	// 객체 형식: { min: -2, max: 2 }
	if (typeof domain.min === 'number' && typeof domain.max === 'number') {
		return [domain.min, domain.max];
	}
	return defaultVal;
}

// 2D 샘플링 추출 헬퍼 (숫자 또는 객체 {x: 200} 형식 지원)
export function getSampling2D(sampling: any, defaultVal: number = 200): number {
	if (!sampling) return defaultVal;
	if (typeof sampling === 'number') return sampling;
	if (typeof sampling === 'object') {
		// { x: 200 } 또는 { t: 200 } 형식
		if (typeof sampling.x === 'number') return sampling.x;
		if (typeof sampling.t === 'number') return sampling.t;
	}
	return defaultVal;
}

// 3D 도메인 헬퍼
export function getDomain3D(domain: Domain3D | undefined, key: 'x' | 'y' | 'u' | 'v' | 't', defaultVal: [number, number]): [number, number] {
	if (!domain || Array.isArray(domain)) return defaultVal;
	return domain[key] || defaultVal;
}

// 3D 샘플링 헬퍼
export function getSampling3D(sampling: Sampling3D | number | undefined, key: 'x' | 'y' | 'u' | 'v' | 't', defaultVal: number): number {
	if (!sampling) return defaultVal;
	if (typeof sampling === 'number') return sampling;
	return sampling[key] || defaultVal;
}

// 3D 그래프인지 확인
export function is3DGraph(type: string): boolean {
	return ['function_3d', 'parametric_3d', 'scatter_3d', 'composite_3d', 'vector_field_3d'].includes(type);
}

// 지원되는 그래프 타입인지 확인
export function isTypeSupported(type: string): boolean {
	const supportedTypes = [
		'function_2d', 'parametric_2d', 'function_parametric_2d', 'phase_plane', 'scatter_2d', 'point_2d', 'line_2d',
		'composite_2d', 'multi_scatter_2d', 'cartesian', 'histogram_2d', 'vector_2d',
		'heatmap_2d', 'contour_2d', 'implicit_2d',
		'pie_2d', 'bar_2d',
		'function_3d', 'parametric_3d', 'scatter_3d', 'composite_3d', 'vector_field_3d'
	];
	return supportedTypes.includes(type);
}

// Validate traces for NaN/Infinity issues
export function validateTraces(traces: any[]): { valid: boolean; error?: string } {
	if (!traces || traces.length === 0) {
		return { valid: false, error: '렌더링할 데이터가 없습니다' };
	}

	let totalPoints = 0;
	let nanCount = 0;

	for (const trace of traces) {
		// Check x, y, z arrays for NaN/Infinity
		for (const key of ['x', 'y', 'z', 'u', 'v', 'w']) {
			const arr = trace[key];
			if (Array.isArray(arr)) {
				for (const val of arr) {
					totalPoints++;
					if (typeof val === 'number' && (!isFinite(val) || isNaN(val))) {
						nanCount++;
					}
				}
			}
		}
	}

	// If more than 80% of points are NaN/Infinity, consider it an error
	if (totalPoints > 0 && nanCount / totalPoints > 0.8) {
		return { valid: false, error: `수식 계산 오류: ${Math.round(nanCount / totalPoints * 100)}%의 값이 유효하지 않습니다` };
	}

	return { valid: true };
}

// ========== 2D Graph Builders ==========

// function_2d: y = f(x)
export function buildFunction2DTraces(layer: LayerSpec) {
	// Handle x_axis format (alternative format support)
	// Note: y_axis is ignored for function_2d as y-range is auto-scaled
	const xAxis = (layer as unknown as Record<string, unknown>).x_axis;

	let domain = layer.domain;

	// Check if using axis format
	if (xAxis && typeof xAxis === 'object' && xAxis !== null) {
		const xAxisObj = xAxis as { min?: number; max?: number; label?: string };
		if (typeof xAxisObj.min === 'number' && typeof xAxisObj.max === 'number') {
			domain = [xAxisObj.min, xAxisObj.max];
		}
	}

	const expressions = normalizeExpressions(layer);
	const colors = normalizeColors(layer);

	return expressions.map((expr, i) => {
		let f;
		try {
			f = compile(expr);
		} catch (e) {
			console.error('[GraphBuilder] Failed to compile expression:', expr, e);
			return {
				x: [],
				y: [],
				type: 'scatter',
				mode: 'lines',
				name: 'Error'
			};
		}

		// Detect which variable name to use (x or t)
		// Check if expression contains 't' and not 'x', or if x_axis label is 't'
		const xAxisObj = xAxis as { label?: string } | undefined;
		const usesT = expr.includes('t') && !expr.match(/\bx\b/);
		const labelIsT = xAxisObj?.label === 't';
		const varName = (usesT || labelIsT) ? 't' : 'x';

		const [x0, x1] = getDomain2D(domain);
		const sampling = getSampling2D(layer.sampling);

		const x: number[] = [];
		const y: number[] = [];

		let errorCount = 0;
		for (let j = 0; j < sampling; j++) {
			const xv = x0 + ((x1 - x0) * j) / (sampling - 1);
			x.push(xv);
			try {
				// Evaluate with detected variable name
				const yv = varName === 't' ? f.evaluate({ t: xv }) : f.evaluate({ x: xv });
				y.push(yv);
			} catch (e) {
				y.push(NaN);
				errorCount++;
				if (errorCount === 1) {
					console.error(`[GraphBuilder] Error evaluating expression at ${varName} =`, xv, ':', e);
				}
			}
		}

		if (errorCount > 0) {
			console.warn(`[GraphBuilder] ${errorCount}/${sampling} points failed for expression: ${expr}`);
		}

		const legendName = expr.length > 30 ? expr.slice(0, 30) + '...' : expr;

		return {
			x,
			y,
			type: 'scatter',
			mode: 'lines',
			line: {
				color: colors[i] || undefined,
				width: layer.style?.lineWidth ?? 2,
				dash: getLineDash(layer.style?.lineStyle)
			},
			opacity: layer.style?.opacity,
			name: legendName,
			showlegend: expressions.length > 1
		};
	});
}

// parametric_2d: x = f(t), y = g(t)
export function buildParametric2DTraces(layer: LayerSpec) {
	console.log('[GraphBuilder] buildParametric2DTraces called with:', {
		expressions: layer.expressions,
		domain: layer.domain,
		sampling: layer.sampling
	});

	// Handle x_expression/y_expression format (alternative format support)
	const xExpr = (layer as unknown as Record<string, unknown>).x_expression;
	const yExpr = (layer as unknown as Record<string, unknown>).y_expression;
	const tAxis = (layer as unknown as Record<string, unknown>).t_axis;

	let expressions: string[];
	let domain = layer.domain;

	if (typeof xExpr === 'string' && typeof yExpr === 'string') {
		console.log('[GraphBuilder] Found x_expression/y_expression format');
		// Convert to expressions array
		expressions = [xExpr, yExpr];

		// Handle t_axis format: { min: 0, max: 10 }
		if (tAxis && typeof tAxis === 'object' && tAxis !== null) {
			const tAxisObj = tAxis as { min?: number; max?: number; label?: string };
			if (typeof tAxisObj.min === 'number' && typeof tAxisObj.max === 'number') {
				domain = {
					t: [tAxisObj.min, tAxisObj.max]
				};
			}
		}
	} else {
		expressions = normalizeExpressions(layer);
	}
	const colors = normalizeColors(layer);

	if (expressions.length < 2) {
		console.error('[GraphBuilder] parametric_2d requires 2 expressions');
		return [];
	}

	let fX, fY;
	try {
		fX = compile(expressions[0]);
		fY = compile(expressions[1]);
		console.log('[GraphBuilder] parametric_2d expressions compiled successfully');
	} catch (e) {
		console.error('[GraphBuilder] Failed to compile parametric_2d expressions:', e);
		return [];
	}

	// domain이 객체 형식 {t: [0, 2*pi]}이거나 배열 형식 [0, 2*pi]일 수 있음
	let t0 = 0, t1 = Math.PI * 2;
	if (domain) {
		const domainObj = domain as unknown as Record<string, unknown>;
		let domainArray: unknown[];
		if (Array.isArray(domainObj)) {
			domainArray = domainObj;
		} else if (domainObj.t && Array.isArray(domainObj.t)) {
			domainArray = domainObj.t as unknown[];
		} else {
			domainArray = [t0, t1];
		}
		// 문자열 수식 평가 (예: "2*pi")
		t0 = typeof domainArray[0] === 'string' ? compile(domainArray[0]).evaluate({}) : (domainArray[0] as number);
		t1 = typeof domainArray[1] === 'string' ? compile(domainArray[1]).evaluate({}) : (domainArray[1] as number);
	}

	// sampling도 객체 형식 {t: 200}이거나 숫자일 수 있음
	const sampling = getSampling2D(layer.sampling);

	// Detect which variable name to use (t or theta)
	// Check if t_axis.label is 'theta', or if expressions contain 'theta' and not 't'
	const tAxisObj = tAxis as { label?: string } | undefined;
	const usesTheta = expressions.some(expr => expr.includes('theta') && !expr.match(/\bt\b/));
	const labelIsTheta = tAxisObj?.label === 'theta';
	const varName = (usesTheta || labelIsTheta) ? 'theta' : 't';

	const x: number[] = [];
	const y: number[] = [];

	for (let j = 0; j < sampling; j++) {
		const t = t0 + ((t1 - t0) * j) / (sampling - 1);
		try {
			// Evaluate with detected variable name
			const vars = varName === 'theta' ? { theta: t } : { t };
			x.push(fX.evaluate(vars));
			y.push(fY.evaluate(vars));
		} catch {
			x.push(NaN);
			y.push(NaN);
		}
	}

	const name = `(${expressions[0]}, ${expressions[1]})`;
	const legendName = name.length > 30 ? name.slice(0, 30) + '...' : name;

	console.log('[GraphBuilder] parametric_2d generated', x.length, 'points, first few:', x.slice(0, 3), y.slice(0, 3));

	return [{
		x,
		y,
		type: 'scatter',
		mode: 'lines',
		line: {
			color: colors[0] || undefined,
			width: layer.style?.lineWidth ?? 2,
			dash: getLineDash(layer.style?.lineStyle)
		},
		opacity: layer.style?.opacity,
		name: legendName,
		showlegend: false
	}];
}

// phase_plane: dx/dt = f(x,y), dy/dt = g(x,y) - vector field
export function buildPhasePlaneTraces(layer: LayerSpec) {
	console.log('[GraphBuilder] buildPhasePlaneTraces called with:', {
		hasField: !!layer.field,
		fieldDx: layer.field?.dx,
		fieldDy: layer.field?.dy,
		domain: layer.domain,
		sampling: layer.sampling
	});

	// field 방식 우선 지원 (신규)
	if (layer.field?.dx && layer.field?.dy) {
		console.log('[GraphBuilder] Using field-based phase_plane');
		let fDx, fDy;
		try {
			fDx = compile(layer.field.dx);
			fDy = compile(layer.field.dy);
			console.log('[GraphBuilder] Expressions compiled successfully:', layer.field.dx, layer.field.dy);
		} catch (e) {
			console.error('[GraphBuilder] Failed to compile phase_plane expressions:', e);
			return [];
		}

		// domain이 객체 형식 {x: [xmin, xmax], y: [ymin, ymax]}
		const domain = layer.domain as any;
		let xmin = -5, xmax = 5, ymin = -5, ymax = 5;
		if (domain) {
			if (domain.x && Array.isArray(domain.x)) {
				const xArr = domain.x;
				xmin = typeof xArr[0] === 'string' ? compile(xArr[0]).evaluate({}) : xArr[0];
				xmax = typeof xArr[1] === 'string' ? compile(xArr[1]).evaluate({}) : xArr[1];
			}
			if (domain.y && Array.isArray(domain.y)) {
				const yArr = domain.y;
				ymin = typeof yArr[0] === 'string' ? compile(yArr[0]).evaluate({}) : yArr[0];
				ymax = typeof yArr[1] === 'string' ? compile(yArr[1]).evaluate({}) : yArr[1];
			}
		}

		// sampling도 객체 형식 {x: 20, y: 20}
		const sampling = layer.sampling as any;
		let Nx = 20, Ny = 20;
		if (sampling) {
			if (typeof sampling.x === 'number') Nx = sampling.x;
			if (typeof sampling.y === 'number') Ny = sampling.y;
		}

		const traces: any[] = [];
		const stepX = (xmax - xmin) / (Nx - 1);
		const stepY = (ymax - ymin) / (Ny - 1);
		const cellSize = Math.min(stepX, stepY);
		const scale = layer.style?.scale ?? 0.8;

		// Magnitude 통계를 위한 사전 계산
		const magnitudes: number[] = [];
		for (let i = 0; i < Nx; i++) {
			for (let j = 0; j < Ny; j++) {
				const x = xmin + i * stepX;
				const y = ymin + j * stepY;
				try {
					const dx = fDx.evaluate({ x, y });
					const dy = fDy.evaluate({ x, y });
					const mag = Math.sqrt(dx * dx + dy * dy);
					magnitudes.push(mag);
				} catch {
					magnitudes.push(0);
				}
			}
		}

		// Median magnitude 계산
		const sortedMags = [...magnitudes].sort((a, b) => a - b);
		const medianMag = sortedMags[Math.floor(sortedMags.length / 2)] || 1;
		const c = medianMag * 0.5; // saturating 상수

		const color = layer.style?.color || 'darkblue';
		const lineWidth = layer.style?.lineWidth ?? 1;
		const opacity = layer.style?.opacity ?? 0.8;

		console.log('[GraphBuilder] phase_plane config:', {
			domain: { xmin, xmax, ymin, ymax },
			sampling: { Nx, Ny },
			cellSize,
			scale,
			medianMag,
			color
		});

		for (let i = 0; i < Nx; i++) {
			for (let j = 0; j < Ny; j++) {
				const x = xmin + i * stepX;
				const y = ymin + j * stepY;
				try {
					const dx = fDx.evaluate({ x, y });
					const dy = fDy.evaluate({ x, y });
					const mag = Math.sqrt(dx * dx + dy * dy);

					// 임계값: 너무 작은 벡터는 생략
					if (mag < 0.05 * medianMag) continue;

					// Saturating scaling: g(m) = m / (m + c)
					const gMag = mag / (mag + c);
					// 기본 배율 5배 적용하여 화살표 가시성 향상
					const len = scale * cellSize * gMag * 5;

					const eps = 1e-9;
					const ux = dx / (mag + eps);
					const uy = dy / (mag + eps);

					const endX = x + ux * len;
					const endY = y + uy * len;

					// Arrow shaft (선분)
					traces.push({
						x: [x, endX],
						y: [y, endY],
						type: 'scatter',
						mode: 'lines',
						line: {
							color: color,
							width: lineWidth
						},
						opacity: opacity,
						showlegend: false,
						hoverinfo: 'skip'
					});

					// Arrowhead (삼각형) - 화살표 크기에 비례하여 머리 크기도 증가
					const headLen = Math.min(0.3 * len, cellSize * 0.5);
					const angle = Math.atan2(uy, ux);
					const angle1 = angle + Math.PI * 0.85;
					const angle2 = angle - Math.PI * 0.85;

					const head1X = endX + headLen * Math.cos(angle1);
					const head1Y = endY + headLen * Math.sin(angle1);
					const head2X = endX + headLen * Math.cos(angle2);
					const head2Y = endY + headLen * Math.sin(angle2);

					traces.push({
						x: [head1X, endX, head2X],
						y: [head1Y, endY, head2Y],
						type: 'scatter',
						mode: 'lines',
						fill: 'toself',
						fillcolor: color,
						line: {
							color: color,
							width: 0
						},
						opacity: opacity,
						showlegend: false,
						hoverinfo: 'skip'
					});
				} catch {
					// Skip invalid points
				}
			}
		}

		console.log('[GraphBuilder] Field-based phase_plane generated', traces.length, 'traces');
		return traces;
	}

	// 기존 expressions 방식 (하위 호환)
	console.log('[GraphBuilder] Using expressions-based phase_plane (fallback)');
	const expressions = normalizeExpressions(layer);
	const colors = normalizeColors(layer);

	if (expressions.length < 2) {
		console.error('[GraphBuilder] phase_plane requires 2 expressions');
		return [];
	}

	const fDx = compile(expressions[0]);
	const fDy = compile(expressions[1]);
	const domainArr = (Array.isArray(layer.domain) ? layer.domain : [-5, 5]) as [number, number];
	const [min, max] = domainArr;
	const sampling = getSampling2D(layer.sampling, 20);

	const traces: any[] = [];
	const step = (max - min) / (sampling - 1);
	const arrowScale = step * 0.4;

	for (let i = 0; i < sampling; i++) {
		for (let j = 0; j < sampling; j++) {
			const xv = min + i * step;
			const yv = min + j * step;
			try {
				const dx = fDx.evaluate({ x: xv, y: yv });
				const dy = fDy.evaluate({ x: xv, y: yv });
				const mag = Math.sqrt(dx * dx + dy * dy);
				if (mag > 0) {
					traces.push({
						x: [xv, xv + (dx / mag) * arrowScale],
						y: [yv, yv + (dy / mag) * arrowScale],
						type: 'scatter',
						mode: 'lines',
						line: { color: colors[0] || '#666', width: 1 },
						showlegend: false,
						hoverinfo: 'skip'
					});
				}
			} catch {
				// Skip invalid points
			}
		}
	}
	return traces;
}

// scatter_2d: 산점도 (data: [[x, y], ...])
export function buildScatter2DTraces(layer: LayerSpec, showLegend = false, legendName?: string) {
	const colors = normalizeColors(layer);
	const data = layer.data || [];

	if (data.length === 0) {
		console.error('[GraphBuilder] scatter_2d requires data array');
		return [];
	}

	const x = data.map((point: any) => point[0]);
	const y = data.map((point: any) => point[1]);
	const name = legendName || layer.style?.marker || 'scatter';

	return [{
		x,
		y,
		type: 'scatter',
		mode: 'markers',
		marker: {
			symbol: markerSymbolMap[layer.style?.marker || 'circle'] || 'circle',
			size: layer.style?.size ?? 8,
			color: colors[0] || '#1f77b4',
			opacity: layer.style?.opacity
		},
		name,
		showlegend: showLegend
	}];
}

// line_2d: 선 (data: [[x, y], ...])
export function buildLine2DTraces(layer: LayerSpec, showLegend = false, legendName?: string) {
	const colors = normalizeColors(layer);
	const data = layer.data || [];

	if (data.length === 0) {
		console.error('[GraphBuilder] line_2d requires data array');
		return [];
	}

	const x = data.map((point: any) => point[0]);
	const y = data.map((point: any) => point[1]);
	const name = legendName || 'line';

	return [{
		x,
		y,
		type: 'scatter',
		mode: 'lines',
		line: {
			color: colors[0] || 'gray',
			width: layer.style?.lineWidth ?? 1,
			dash: getLineDash(layer.style?.lineStyle)
		},
		opacity: layer.style?.opacity,
		name,
		showlegend: showLegend
	}];
}

// vector_2d: 벡터/화살표 (data: [{start, end, color?, width?}, ...])
export function buildVector2DTraces(layer: LayerSpec, showLegend = false, legendName?: string) {
	const data = layer.data || [];

	if (!Array.isArray(data) || data.length === 0) {
		console.error('[GraphBuilder] vector_2d requires data array');
		return [];
	}

	const traces: any[] = [];

	// 각 벡터를 화살표로 렌더링
	data.forEach((vector: any) => {
		const start = vector.start || [0, 0];
		const end = vector.end || [0, 0];
		const color = vector.color || layer.style?.color || 'black';
		const width = vector.width || layer.style?.lineWidth || layer.style?.width || 2;
		const opacity = vector.opacity || layer.style?.opacity || 1;

		// 벡터 선
		traces.push({
			x: [start[0], end[0]],
			y: [start[1], end[1]],
			type: 'scatter',
			mode: 'lines',
			line: {
				color: color,
				width: width
			},
			opacity: opacity,
			showlegend: false,
			hoverinfo: 'skip'
		});

		// 화살표 머리 (간단한 삼각형)
		const dx = end[0] - start[0];
		const dy = end[1] - start[1];
		const len = Math.sqrt(dx * dx + dy * dy);

		if (len > 0) {
			const headLen = Math.min(0.15 * len, width * 0.05); // 화살표 크기
			const angle = Math.atan2(dy, dx);
			const angle1 = angle + Math.PI * 0.85;
			const angle2 = angle - Math.PI * 0.85;

			const arrowX = [
				end[0] + headLen * Math.cos(angle1),
				end[0],
				end[0] + headLen * Math.cos(angle2)
			];
			const arrowY = [
				end[1] + headLen * Math.sin(angle1),
				end[1],
				end[1] + headLen * Math.sin(angle2)
			];

			traces.push({
				x: arrowX,
				y: arrowY,
				type: 'scatter',
				mode: 'lines',
				fill: 'toself',
				fillcolor: color,
				line: {
					color: color,
					width: 1
				},
				opacity: opacity,
				showlegend: false,
				hoverinfo: 'skip'
			});
		}
	});

	return traces;
}

// histogram_2d: 히스토그램 (binEdges, counts)
export function buildHistogram2DTraces(layer: LayerSpec, showLegend = false, legendName?: string) {
	const colors = normalizeColors(layer);
	const binEdges = layer.binEdges || [];
	const counts = layer.counts || [];

	if (binEdges.length === 0 || counts.length === 0) {
		console.error('[GraphBuilder] histogram_2d requires binEdges and counts arrays');
		return [];
	}

	// binEdges의 중간점을 x 좌표로 사용
	const x = [];
	for (let i = 0; i < binEdges.length - 1; i++) {
		x.push((binEdges[i] + binEdges[i + 1]) / 2);
	}

	// 막대 너비 계산
	const barGap = layer.style?.barGap ?? 0.05;
	const widths = [];
	for (let i = 0; i < binEdges.length - 1; i++) {
		const fullWidth = binEdges[i + 1] - binEdges[i];
		widths.push(fullWidth * (1 - barGap));
	}

	const name = legendName || 'histogram';

	return [{
		x,
		y: counts,
		type: 'bar',
		width: widths,
		marker: {
			color: colors[0] || layer.style?.color || 'steelblue',
			opacity: layer.style?.opacity ?? 0.85
		},
		name,
		showlegend: showLegend
	}];
}

// point_2d: 산점도 (coordinates: [[x, y], ...]) - cartesian 그래프용
export function buildPoint2DTraces(layer: LayerSpec, showLegend = false, legendName?: string) {
	const colors = normalizeColors(layer);
	// coordinates 또는 data 필드 지원
	const coordinates = (layer as any).coordinates || layer.data || [];

	if (coordinates.length === 0) {
		console.error('[GraphBuilder] point_2d requires coordinates array');
		return [];
	}

	const x = coordinates.map((point: [number, number]) => point[0]);
	const y = coordinates.map((point: [number, number]) => point[1]);
	const name = legendName || 'points';

	// shape 필드를 marker로 매핑
	const shape = (layer.style as any)?.shape || layer.style?.marker || 'circle';

	return [{
		x,
		y,
		type: 'scatter',
		mode: 'markers',
		marker: {
			symbol: markerSymbolMap[shape] || 'circle',
			size: layer.style?.size ?? 8,
			color: colors[0] || '#1f77b4',
			opacity: layer.style?.opacity ?? 0.8
		},
		name,
		showlegend: showLegend
	}];
}

// pie_2d: 파이 차트
export function buildPie2DTraces(layer: LayerSpec, showLegend = false, legendName?: string) {
	const layerAny = layer as any;
	let labels = layerAny.labels || [];
	let percentages = layerAny.percentages || [];

	// data 배열 형식도 지원: [{label: ..., percentage: ...}, ...]
	if (layerAny.data && Array.isArray(layerAny.data) && layerAny.data.length > 0) {
		if (typeof layerAny.data[0] === 'object') {
			labels = layerAny.data.map((item: any) => item.label || '');
			percentages = layerAny.data.map((item: any) => item.percentage || item.value || 0);
		}
	}

	if (labels.length === 0 || percentages.length === 0) {
		console.error('[GraphBuilder] pie_2d requires labels and percentages arrays or data array');
		return [];
	}

	if (labels.length !== percentages.length) {
		console.error('[GraphBuilder] pie_2d labels and percentages must have the same length');
		return [];
	}

	const colors = normalizeColors(layer);
	const labelFormat = layer.style?.labelFormat || 'percent';
	const textInfo = labelFormat === 'percent' ? 'label+percent' : 'label+value';

	return [{
		type: 'pie',
		labels,
		values: percentages,
		marker: {
			colors: colors.length > 0 ? colors : undefined
		},
		opacity: layer.style?.opacity ?? 1.0,
		textinfo: textInfo,
		textposition: 'auto',
		hoverinfo: 'label+value+percent',
		showlegend: showLegend !== undefined ? showLegend : true,
		name: legendName
	}];
}

// bar_2d: 막대 그래프
export function buildBar2DTraces(layer: LayerSpec, showLegend = false, legendName?: string) {
	const layerAny = layer as any;
	let categories = layerAny.categories || [];
	let values = layerAny.values || [];
	const orientation = layerAny.orientation || 'vertical';

	// data 배열 형식도 지원: [{category: ..., value: ...}, ...]
	if (layerAny.data && Array.isArray(layerAny.data) && layerAny.data.length > 0) {
		if (typeof layerAny.data[0] === 'object') {
			categories = layerAny.data.map((item: any) => item.category || item.label || '');
			values = layerAny.data.map((item: any) => item.value || 0);
		}
	}

	if (categories.length === 0 || values.length === 0) {
		console.error('[GraphBuilder] bar_2d requires categories and values arrays or data array');
		return [];
	}

	if (categories.length !== values.length) {
		console.error('[GraphBuilder] bar_2d categories and values must have the same length');
		return [];
	}

	const colors = normalizeColors(layer);
	const isHorizontal = orientation === 'horizontal';
	const barWidth = (layerAny.style?.barWidth !== undefined) ? layerAny.style.barWidth : undefined;

	return [{
		type: 'bar',
		x: isHorizontal ? values : categories,
		y: isHorizontal ? categories : values,
		orientation: isHorizontal ? 'h' : 'v',
		width: barWidth,
		marker: {
			color: colors[0] || '#17becf',
			opacity: layer.style?.opacity ?? 1.0
		},
		showlegend: showLegend,
		name: legendName
	}];
}

// heatmap_2d: 2D scalar field visualization (z = f(x,y) as heatmap)
export function buildHeatmap2DTraces(layer: LayerSpec): any[] {
	// Extract expression
	const expr = typeof layer.expression === 'string'
		? layer.expression
		: normalizeExpressions(layer)[0];

	if (!expr) {
		console.error('[GraphBuilder] heatmap_2d requires expression');
		return [];
	}

	// Compile expression
	let f;
	try {
		f = compile(expr);
	} catch (e) {
		console.error('[GraphBuilder] Failed to compile heatmap_2d expression:', expr, e);
		return [{
			x: [], y: [], z: [],
			type: 'heatmap',
			name: 'Error'
		}];
	}

	// Extract domain (default to [-5, 5])
	// Support both domain: {x: [min, max], y: [min, max]} and x_axis/y_axis format
	const layerAny = layer as unknown as Record<string, unknown>;
	const xAxis = layerAny.x_axis as { min?: number; max?: number } | undefined;
	const yAxis = layerAny.y_axis as { min?: number; max?: number } | undefined;

	let x0 = -5, x1 = 5, y0 = -5, y1 = 5;

	if (xAxis && typeof xAxis.min === 'number' && typeof xAxis.max === 'number') {
		x0 = xAxis.min;
		x1 = xAxis.max;
	} else {
		const domain = layer.domain as Domain3D | undefined;
		[x0, x1] = getDomain3D(domain, 'x', [-5, 5]);
	}

	if (yAxis && typeof yAxis.min === 'number' && typeof yAxis.max === 'number') {
		y0 = yAxis.min;
		y1 = yAxis.max;
	} else {
		const domain = layer.domain as Domain3D | undefined;
		[y0, y1] = getDomain3D(domain, 'y', [-5, 5]);
	}

	// Extract sampling (default to 100x100 for good quality)
	const sampling = layer.sampling as Sampling3D | number | undefined;
	const xSampling = getSampling3D(sampling, 'x', 100);
	const ySampling = getSampling3D(sampling, 'y', 100);

	// Generate grid
	const x: number[] = [];
	const y: number[] = [];
	const z: number[][] = [];

	for (let i = 0; i < xSampling; i++) {
		x.push(x0 + ((x1 - x0) * i) / (xSampling - 1));
	}
	for (let j = 0; j < ySampling; j++) {
		y.push(y0 + ((y1 - y0) * j) / (ySampling - 1));
	}

	// Evaluate f(x,y) on grid
	for (let j = 0; j < ySampling; j++) {
		const row: number[] = [];
		for (let i = 0; i < xSampling; i++) {
			try {
				row.push(f.evaluate({ x: x[i], y: y[j] }));
			} catch {
				row.push(NaN);
			}
		}
		z.push(row);
	}

	// Access showColorbar from layer (reuse layerAny from above)
	const showColorbar = (layerAny.style as Record<string, unknown> | undefined)?.showColorbar ?? true;

	return [{
		x,
		y,
		z,
		type: 'heatmap',
		colorscale: layer.style?.colorMap || 'Viridis',
		opacity: layer.style?.opacity ?? 1.0,
		showscale: showColorbar,
		colorbar: showColorbar ? {
			title: expr.length > 15 ? 'z' : expr,
			thickness: 15,
			len: 0.7
		} : undefined,
		name: expr.length > 20 ? expr.slice(0, 20) + '...' : expr
	}];
}

// contour_2d: Contour plot of f(x,y) = constant
export function buildContour2DTraces(layer: LayerSpec): any[] {
	// Extract expression
	const expr = typeof layer.expression === 'string'
		? layer.expression
		: normalizeExpressions(layer)[0];

	if (!expr) {
		console.error('[GraphBuilder] contour_2d requires expression');
		return [];
	}

	// Compile expression
	let f;
	try {
		f = compile(expr);
	} catch (e) {
		console.error('[GraphBuilder] Failed to compile contour_2d expression:', expr, e);
		return [{
			x: [], y: [], z: [],
			type: 'contour',
			name: 'Error'
		}];
	}

	// Extract domain (default to [-5, 5])
	// Support both domain: {x: [min, max], y: [min, max]} and x_axis/y_axis format
	const layerAny = layer as unknown as Record<string, unknown>;
	const xAxis = layerAny.x_axis as { min?: number; max?: number } | undefined;
	const yAxis = layerAny.y_axis as { min?: number; max?: number } | undefined;

	let x0 = -5, x1 = 5, y0 = -5, y1 = 5;

	if (xAxis && typeof xAxis.min === 'number' && typeof xAxis.max === 'number') {
		x0 = xAxis.min;
		x1 = xAxis.max;
	} else {
		const domain = layer.domain as Domain3D | undefined;
		[x0, x1] = getDomain3D(domain, 'x', [-5, 5]);
	}

	if (yAxis && typeof yAxis.min === 'number' && typeof yAxis.max === 'number') {
		y0 = yAxis.min;
		y1 = yAxis.max;
	} else {
		const domain = layer.domain as Domain3D | undefined;
		[y0, y1] = getDomain3D(domain, 'y', [-5, 5]);
	}

	// Extract sampling (default to 100x100)
	const sampling = layer.sampling as Sampling3D | number | undefined;
	const xSampling = getSampling3D(sampling, 'x', 100);
	const ySampling = getSampling3D(sampling, 'y', 100);

	// Generate grid
	const x: number[] = [];
	const y: number[] = [];
	const z: number[][] = [];

	for (let i = 0; i < xSampling; i++) {
		x.push(x0 + ((x1 - x0) * i) / (xSampling - 1));
	}
	for (let j = 0; j < ySampling; j++) {
		y.push(y0 + ((y1 - y0) * j) / (ySampling - 1));
	}

	// Evaluate f(x,y) on grid
	for (let j = 0; j < ySampling; j++) {
		const row: number[] = [];
		for (let i = 0; i < xSampling; i++) {
			try {
				row.push(f.evaluate({ x: x[i], y: y[j] }));
			} catch {
				row.push(NaN);
			}
		}
		z.push(row);
	}

	// Contour-specific options (reuse layerAny from above)
	const styleObj = layerAny.style as Record<string, unknown> | undefined;
	const ncontours = (styleObj?.ncontours as number | undefined) || 15;
	const showColorbar = styleObj?.showColorbar ?? true;

	return [{
		x,
		y,
		z,
		type: 'contour',
		colorscale: layer.style?.colorMap || 'Viridis',
		opacity: layer.style?.opacity ?? 0.9,
		ncontours: ncontours,
		showscale: showColorbar,
		colorbar: showColorbar ? {
			title: expr.length > 15 ? 'z' : expr,
			thickness: 15,
			len: 0.7
		} : undefined,
		contours: {
			coloring: 'heatmap',
			showlabels: true,
			labelfont: {
				size: 10,
				color: 'white'
			}
		},
		name: expr.length > 20 ? expr.slice(0, 20) + '...' : expr
	}];
}

// implicit_2d: Implicit curve F(x,y) = 0
export function buildImplicit2DTraces(layer: LayerSpec): any[] {
	// Extract expression
	const expr = typeof layer.expression === 'string'
		? layer.expression
		: normalizeExpressions(layer)[0];

	if (!expr) {
		console.error('[GraphBuilder] implicit_2d requires expression');
		return [];
	}

	// Compile expression
	let f;
	try {
		f = compile(expr);
	} catch (e) {
		console.error('[GraphBuilder] Failed to compile implicit_2d expression:', expr, e);
		return [{
			x: [], y: [], z: [],
			type: 'contour',
			name: 'Error'
		}];
	}

	// Extract domain (default to [-5, 5])
	// Support both domain: {x: [min, max], y: [min, max]} and x_axis/y_axis format
	const layerAny = layer as unknown as Record<string, unknown>;
	const xAxis = layerAny.x_axis as { min?: number; max?: number } | undefined;
	const yAxis = layerAny.y_axis as { min?: number; max?: number } | undefined;

	let x0 = -5, x1 = 5, y0 = -5, y1 = 5;

	if (xAxis && typeof xAxis.min === 'number' && typeof xAxis.max === 'number') {
		x0 = xAxis.min;
		x1 = xAxis.max;
	} else {
		const domain = layer.domain as Domain3D | undefined;
		[x0, x1] = getDomain3D(domain, 'x', [-5, 5]);
	}

	if (yAxis && typeof yAxis.min === 'number' && typeof yAxis.max === 'number') {
		y0 = yAxis.min;
		y1 = yAxis.max;
	} else {
		const domain = layer.domain as Domain3D | undefined;
		[y0, y1] = getDomain3D(domain, 'y', [-5, 5]);
	}

	// Higher sampling for smooth implicit curves (150x150)
	const sampling = layer.sampling as Sampling3D | number | undefined;
	const xSampling = getSampling3D(sampling, 'x', 150);
	const ySampling = getSampling3D(sampling, 'y', 150);

	// Generate grid
	const x: number[] = [];
	const y: number[] = [];
	const z: number[][] = [];

	for (let i = 0; i < xSampling; i++) {
		x.push(x0 + ((x1 - x0) * i) / (xSampling - 1));
	}
	for (let j = 0; j < ySampling; j++) {
		y.push(y0 + ((y1 - y0) * j) / (ySampling - 1));
	}

	// Evaluate f(x,y) on grid
	for (let j = 0; j < ySampling; j++) {
		const row: number[] = [];
		for (let i = 0; i < xSampling; i++) {
			try {
				row.push(f.evaluate({ x: x[i], y: y[j] }));
			} catch {
				row.push(NaN);
			}
		}
		z.push(row);
	}

	// Extract color
	const color = Array.isArray(layer.style?.color)
		? layer.style.color[0]
		: layer.style?.color || '#1f77b4';

	return [{
		x,
		y,
		z,
		type: 'contour',
		// Key: only show the zero level
		contours: {
			type: 'constraint',
			operation: '=',
			value: 0,
			coloring: 'lines'
		},
		line: {
			width: layer.style?.lineWidth ?? 3,
			color: color
		},
		opacity: layer.style?.opacity ?? 1.0,
		showscale: false,  // No colorbar for implicit curves
		name: expr.length > 20 ? expr.slice(0, 20) + '...' : expr
	}];
}

// ========== 3D Graph Builders ==========

// function_3d: z = f(x, y) 표면
export function buildFunction3DTraces(layer: LayerSpec) {
	// Handle x_axis/y_axis/z_axis format (alternative format support)
	const xAxis = (layer as unknown as Record<string, unknown>).x_axis;
	const yAxis = (layer as unknown as Record<string, unknown>).y_axis;
	const zAxis = (layer as unknown as Record<string, unknown>).z_axis;

	let domain = layer.domain as Domain3D | undefined;

	// Check if using axis format
	if (xAxis && yAxis && typeof layer.expression === 'string') {
		console.log('[GraphBuilder] Found x_axis/y_axis/z_axis format for function_3d');

		const domainObj: Domain3D = {};

		// Extract x domain from x_axis
		if (xAxis && typeof xAxis === 'object' && xAxis !== null) {
			const xAxisObj = xAxis as { min?: number; max?: number; label?: string };
			if (typeof xAxisObj.min === 'number' && typeof xAxisObj.max === 'number') {
				domainObj.x = [xAxisObj.min, xAxisObj.max];
			}
		}

		// Extract y domain from y_axis
		if (yAxis && typeof yAxis === 'object' && yAxis !== null) {
			const yAxisObj = yAxis as { min?: number; max?: number; label?: string };
			if (typeof yAxisObj.min === 'number' && typeof yAxisObj.max === 'number') {
				domainObj.y = [yAxisObj.min, yAxisObj.max];
			}
		}

		// Extract z range (for layout, not used in trace building but good to preserve)
		if (zAxis && typeof zAxis === 'object' && zAxis !== null) {
			const zAxisObj = zAxis as { min?: number; max?: number; label?: string };
			if (typeof zAxisObj.min === 'number' && typeof zAxisObj.max === 'number') {
				domainObj.z = [zAxisObj.min, zAxisObj.max];
			}
		}

		domain = domainObj;
	}

	// expression이 문자열인 경우만 사용, 객체면 normalizeExpressions 사용
	let expr: string;
	if (typeof layer.expression === 'string') {
		expr = layer.expression;
	} else if (layer.expressions) {
		expr = normalizeExpressions(layer)[0] || 'x^2 + y^2';
	} else {
		expr = 'x^2 + y^2';
	}
	const f = compile(expr);
	const [x0, x1] = getDomain3D(domain, 'x', [-2, 2]);
	const [y0, y1] = getDomain3D(domain, 'y', [-2, 2]);

	const sampling = layer.sampling as Sampling3D | number | undefined;
	const xSampling = getSampling3D(sampling, 'x', 40);
	const ySampling = getSampling3D(sampling, 'y', 40);

	const xVals: number[] = [];
	const yVals: number[] = [];
	const zVals: number[][] = [];

	for (let i = 0; i < xSampling; i++) {
		xVals.push(x0 + ((x1 - x0) * i) / (xSampling - 1));
	}
	for (let j = 0; j < ySampling; j++) {
		yVals.push(y0 + ((y1 - y0) * j) / (ySampling - 1));
	}

	for (let j = 0; j < ySampling; j++) {
		const row: number[] = [];
		for (let i = 0; i < xSampling; i++) {
			try {
				row.push(f.evaluate({ x: xVals[i], y: yVals[j] }));
			} catch {
				row.push(NaN);
			}
		}
		zVals.push(row);
	}

	return [{
		x: xVals,
		y: yVals,
		z: zVals,
		type: 'surface',
		colorscale: layer.style?.colorMap || 'Viridis',
		opacity: layer.style?.opacity ?? 0.9,
		showscale: false,
		name: expr.length > 20 ? expr.slice(0, 20) + '...' : expr
	}];
}

// vector_field_3d: 3D vector field with arrows
export function buildVectorField3DTraces(layer: LayerSpec) {
	if (!layer.field?.dx || !layer.field?.dy || !layer.field?.dz) {
		console.error('[GraphBuilder] vector_field_3d requires field.dx, field.dy, field.dz');
		return [];
	}

	const fDx = compile(layer.field.dx);
	const fDy = compile(layer.field.dy);
	const fDz = compile(layer.field.dz);

	// Domain parsing
	const domain = layer.domain as any;
	let xmin = -5, xmax = 5, ymin = -5, ymax = 5, zmin = -5, zmax = 5;
	if (domain) {
		if (domain.x && Array.isArray(domain.x)) {
			const xArr = domain.x;
			xmin = typeof xArr[0] === 'string' ? compile(xArr[0]).evaluate({}) : xArr[0];
			xmax = typeof xArr[1] === 'string' ? compile(xArr[1]).evaluate({}) : xArr[1];
		}
		if (domain.y && Array.isArray(domain.y)) {
			const yArr = domain.y;
			ymin = typeof yArr[0] === 'string' ? compile(yArr[0]).evaluate({}) : yArr[0];
			ymax = typeof yArr[1] === 'string' ? compile(yArr[1]).evaluate({}) : yArr[1];
		}
		if (domain.z && Array.isArray(domain.z)) {
			const zArr = domain.z;
			zmin = typeof zArr[0] === 'string' ? compile(zArr[0]).evaluate({}) : zArr[0];
			zmax = typeof zArr[1] === 'string' ? compile(zArr[1]).evaluate({}) : zArr[1];
		}
	}

	// Sampling parsing
	const sampling = layer.sampling as any;
	let Nx = 10, Ny = 10, Nz = 10;
	if (sampling) {
		if (typeof sampling.x === 'number') Nx = sampling.x;
		if (typeof sampling.y === 'number') Ny = sampling.y;
		if (typeof sampling.z === 'number') Nz = sampling.z;
	}

	const stepX = (xmax - xmin) / (Nx - 1);
	const stepY = (ymax - ymin) / (Ny - 1);
	const stepZ = (zmax - zmin) / (Nz - 1);
	const cellSize = Math.min(stepX, stepY, stepZ);
	const scale = layer.style?.scale ?? 1.0;

	// Domain 크기 계산
	const domainSizeX = xmax - xmin;
	const domainSizeY = ymax - ymin;
	const domainSizeZ = zmax - zmin;
	const maxDomainSize = Math.max(domainSizeX, domainSizeY, domainSizeZ);

	// 적응형 스케일 팩터: 큰 domain에서는 자동으로 스케일 감소
	const adaptiveScaleFactor = maxDomainSize > 100 ? 100 / maxDomainSize : 1.0;

	// Pre-compute magnitudes for statistics
	const magnitudes: number[] = [];
	for (let i = 0; i < Nx; i++) {
		for (let j = 0; j < Ny; j++) {
			for (let k = 0; k < Nz; k++) {
				const x = xmin + i * stepX;
				const y = ymin + j * stepY;
				const z = zmin + k * stepZ;

				// Compute spherical coordinates for compatibility
				const r = Math.sqrt(x * x + y * y + z * z);
				const theta = r > 0 ? Math.acos(z / r) : 0;
				const phi = Math.atan2(y, x);

				try {
					const dx = fDx.evaluate({ x, y, z, r, theta, phi });
					const dy = fDy.evaluate({ x, y, z, r, theta, phi });
					const dz = fDz.evaluate({ x, y, z, r, theta, phi });
					const mag = Math.sqrt(dx * dx + dy * dy + dz * dz);
					magnitudes.push(mag);
				} catch {
					magnitudes.push(0);
				}
			}
		}
	}

	// Median magnitude
	const sortedMags = [...magnitudes].sort((a, b) => a - b);
	const medianMag = sortedMags[Math.floor(sortedMags.length / 2)] || 1;
	const c = medianMag * 0.5;

	const color = layer.style?.color || 'darkblue';
	const opacity = layer.style?.opacity ?? 0.8;

	// Plotly cone trace for 3D vectors
	const x: number[] = [];
	const y: number[] = [];
	const z: number[] = [];
	const u: number[] = [];
	const v: number[] = [];
	const w: number[] = [];

	for (let i = 0; i < Nx; i++) {
		for (let j = 0; j < Ny; j++) {
			for (let k = 0; k < Nz; k++) {
				const xPos = xmin + i * stepX;
				const yPos = ymin + j * stepY;
				const zPos = zmin + k * stepZ;

				// Compute spherical coordinates for compatibility
				const r = Math.sqrt(xPos * xPos + yPos * yPos + zPos * zPos);
				const theta = r > 0 ? Math.acos(zPos / r) : 0;
				const phi = Math.atan2(yPos, xPos);

				try {
					const dx = fDx.evaluate({ x: xPos, y: yPos, z: zPos, r, theta, phi });
					const dy = fDy.evaluate({ x: xPos, y: yPos, z: zPos, r, theta, phi });
					const dz = fDz.evaluate({ x: xPos, y: yPos, z: zPos, r, theta, phi });
					const mag = Math.sqrt(dx * dx + dy * dy + dz * dz);

					// Skip very small vectors
					if (mag < 0.05 * medianMag) continue;

					// Saturating scaling with adaptive factor
					const gMag = mag / (mag + c);
					let len = scale * cellSize * gMag * adaptiveScaleFactor;

					// 최대 길이 제한: domain 크기의 10%를 넘지 않도록
					const maxLen = maxDomainSize * 0.1;
					len = Math.min(len, maxLen);

					const eps = 1e-9;
					const ux = dx / (mag + eps);
					const uy = dy / (mag + eps);
					const uz = dz / (mag + eps);

					x.push(xPos);
					y.push(yPos);
					z.push(zPos);
					u.push(ux * len);
					v.push(uy * len);
					w.push(uz * len);
				} catch {
					// Skip invalid points
				}
			}
		}
	}

	return [{
		type: 'cone',
		x, y, z,
		u, v, w,
		colorscale: [[0, color], [1, color]],
		sizemode: 'scaled',
		sizeref: maxDomainSize * 0.02,
		opacity: opacity,
		showscale: false,
		hoverinfo: 'skip'
	}];
}

// parametric_3d: x = f(u,v), y = g(u,v), z = h(u,v) 또는 x = f(t), y = g(t), z = h(t)
export function buildParametric3DTraces(layer: LayerSpec) {
	console.log('[GraphBuilder] buildParametric3DTraces called with:', {
		expressions: layer.expressions,
		domain: layer.domain,
		sampling: layer.sampling
	});

	// Handle x_expression/y_expression/z_expression format (alternative format support)
	const xExpr = (layer as unknown as Record<string, unknown>).x_expression;
	const yExpr = (layer as unknown as Record<string, unknown>).y_expression;
	const zExpr = (layer as unknown as Record<string, unknown>).z_expression;
	const tAxis = (layer as unknown as Record<string, unknown>).t_axis;

	let expressions: string[];
	let domain = layer.domain as Domain3D | undefined;

	if (typeof xExpr === 'string' && typeof yExpr === 'string' && typeof zExpr === 'string') {
		console.log('[GraphBuilder] Found x_expression/y_expression/z_expression format');
		// Convert to expressions array
		expressions = [xExpr, yExpr, zExpr];

		// Handle t_axis format: { min: 0, max: 2*PI }
		if (tAxis && typeof tAxis === 'object' && tAxis !== null) {
			const tAxisObj = tAxis as { min?: number; max?: number; label?: string };
			if (typeof tAxisObj.min === 'number' && typeof tAxisObj.max === 'number') {
				domain = {
					t: [tAxisObj.min, tAxisObj.max]
				} as Domain3D;
			}
		}
	} else {
		expressions = normalizeExpressions(layer);
	}

	const colors = normalizeColors(layer);

	if (expressions.length < 3) {
		console.error('[GraphBuilder] parametric_3d requires 3 expressions');
		return [];
	}

	let fX, fY, fZ;
	try {
		fX = compile(expressions[0]);
		fY = compile(expressions[1]);
		fZ = compile(expressions[2]);
		console.log('[GraphBuilder] parametric_3d expressions compiled successfully');
	} catch (e) {
		console.error('[GraphBuilder] Failed to compile parametric_3d expressions:', e);
		return [];
	}

	// t 도메인이 있으면 곡선 (scatter3d), u/v 도메인이 있으면 표면 (surface)
	const hasTDomain = domain && 't' in domain;
	const hasUVDomain = domain && ('u' in domain || 'v' in domain);

	if (hasTDomain || !hasUVDomain) {
		// 3D 곡선 (t 파라미터)
		const [t0, t1] = getDomain3D(domain, 't', [0, Math.PI * 2]);
		const sampling = getSampling3D(layer.sampling as Sampling3D, 't', 100);

		const x: number[] = [];
		const y: number[] = [];
		const z: number[] = [];

		for (let i = 0; i < sampling; i++) {
			const t = t0 + ((t1 - t0) * i) / (sampling - 1);
			try {
				x.push(fX.evaluate({ t }));
				y.push(fY.evaluate({ t }));
				z.push(fZ.evaluate({ t }));
			} catch {
				x.push(NaN);
				y.push(NaN);
				z.push(NaN);
			}
		}

		return [{
			x, y, z,
			type: 'scatter3d',
			mode: 'lines',
			line: {
				color: colors[0] || 'red',
				width: layer.style?.lineWidth ?? 3
			},
			opacity: layer.style?.opacity,
			name: `(${expressions[0]}, ${expressions[1]}, ${expressions[2]})`.slice(0, 20)
		}];
	} else {
		// 3D 표면 (u, v 파라미터)
		const [u0, u1] = getDomain3D(domain, 'u', [0, Math.PI * 2]);
		const [v0, v1] = getDomain3D(domain, 'v', [0, Math.PI]);
		const uSampling = getSampling3D(layer.sampling as Sampling3D, 'u', 60);
		const vSampling = getSampling3D(layer.sampling as Sampling3D, 'v', 30);

		const xVals: number[][] = [];
		const yVals: number[][] = [];
		const zVals: number[][] = [];

		for (let j = 0; j < vSampling; j++) {
			const xRow: number[] = [];
			const yRow: number[] = [];
			const zRow: number[] = [];
			const v = v0 + ((v1 - v0) * j) / (vSampling - 1);

			for (let i = 0; i < uSampling; i++) {
				const u = u0 + ((u1 - u0) * i) / (uSampling - 1);
				try {
					xRow.push(fX.evaluate({ u, v }));
					yRow.push(fY.evaluate({ u, v }));
					zRow.push(fZ.evaluate({ u, v }));
				} catch {
					xRow.push(NaN);
					yRow.push(NaN);
					zRow.push(NaN);
				}
			}
			xVals.push(xRow);
			yVals.push(yRow);
			zVals.push(zRow);
		}

		return [{
			x: xVals,
			y: yVals,
			z: zVals,
			type: 'surface',
			colorscale: layer.style?.colorMap || 'Plasma',
			opacity: layer.style?.opacity ?? 0.9,
			showscale: false
		}];
	}
}

// scatter_3d: 3D 산점도 (data: [[x, y, z], ...] 또는 points: [[x, y, z], ...])
export function buildScatter3DTraces(layer: LayerSpec, showLegend = false, legendName?: string) {
	const colors = normalizeColors(layer);

	// Support both 'data' and 'points' field names
	const layerAny = layer as unknown as Record<string, unknown>;
	const data = (layer.data || (layerAny.points as [number, number, number][]) || []) as [number, number, number][];

	if (data.length === 0) {
		console.error('[GraphBuilder] scatter_3d requires data or points array');
		return [];
	}

	const x = data.map((point) => point[0]);
	const y = data.map((point) => point[1]);
	const z = data.map((point) => point[2]);

	// Determine mode: default to 'lines' for vector paths and curves
	// Can be overridden via style.mode ('markers', 'lines', 'lines+markers')
	const layerStyle = layer.style as Record<string, unknown> | undefined;
	const mode = (layerStyle?.mode as string | undefined) || 'lines';

	// Build trace with conditional properties
	const trace: Record<string, unknown> = {
		x, y, z,
		type: 'scatter3d',
		mode: mode,
		name: legendName || 'scatter',
		showlegend: showLegend
	};

	// Add marker properties only for markers mode
	if (mode.includes('markers')) {
		trace.marker = {
			symbol: layer.style?.marker === 'sphere' ? 'circle' : (layer.style?.marker || 'circle'),
			size: layer.style?.size ?? 5,
			color: colors[0] || 'blue',
			opacity: layer.style?.opacity ?? 0.9
		};
	}

	// Add line properties only for lines mode
	if (mode.includes('lines')) {
		trace.line = {
			color: colors[0] || 'blue',
			width: layer.style?.lineWidth ?? 2
		};
	}

	return [trace];
}

// point_3d: 단일 3D 점 (position: [x, y, z], label 지원)
export function buildPoint3DTraces(layer: GraphSpecLayer, showLegend = false) {
	const colors = normalizeColors(layer);
	const position = (layer as any).position as [number, number, number] | undefined;
	const label = (layer as any).label || '';

	if (!position || position.length !== 3) {
		console.error('[GraphBuilder] point_3d requires position array [x, y, z]');
		return [];
	}

	return [{
		x: [position[0]],
		y: [position[1]],
		z: [position[2]],
		type: 'scatter3d',
		mode: label ? 'markers+text' : 'markers',
		marker: {
			symbol: layer.style?.marker === 'sphere' ? 'circle' : (layer.style?.marker || 'circle'),
			size: layer.style?.size ?? 8,
			color: colors[0] || 'red',
			opacity: layer.style?.opacity ?? 1
		},
		text: label ? [label] : undefined,
		textposition: 'top center',
		textfont: { size: 12 },
		name: label || 'point',
		showlegend: showLegend
	}];
}

// ========== Composite Builders ==========

// 3D 레이어 trace 빌드
export function buildLayer3DTraces(layer: LayerSpec, layerIndex: number, totalLayers: number): any[] {
	const layerType = layer.type;
	const showLegend = totalLayers > 1;
	const legendName = `Layer ${layerIndex + 1}`;

	switch (layerType) {
		case 'function_3d':
			return buildFunction3DTraces(layer);
		case 'parametric_3d':
			return buildParametric3DTraces(layer);
		case 'scatter_3d':
			return buildScatter3DTraces(layer, showLegend, legendName);
		case 'point_3d':
			return buildPoint3DTraces(layer, showLegend);
		case 'vector_field_3d':
			return buildVectorField3DTraces(layer);
		default:
			return [];
	}
}

// composite_3d: 여러 3D 레이어 합성
export function buildComposite3DTraces(spec: GraphSpec): any[] {
	// Support both 'layers' and 'graphs' field names
	const specAny = spec as unknown as Record<string, unknown>;
	const layers = spec.layers || (specAny.graphs as LayerSpec[]) || [];
	if (layers.length === 0) {
		console.error('[GraphBuilder] composite_3d requires layers or graphs array');
		return [];
	}

	const allTraces: any[] = [];
	layers.forEach((layer: LayerSpec, index: number) => {
		const traces = buildLayer3DTraces(layer, index, layers.length);
		allTraces.push(...traces);
	});
	return allTraces;
}

// 단일 2D 레이어에 대한 trace 빌드
export function buildLayerTraces(layer: LayerSpec, layerIndex: number, totalLayers: number): any[] {
	// type이 없으면 data/coordinates 유무로 타입 추론
	const layerAny = layer as any;
	const hasCoordinates = !!layerAny.coordinates;
	const layerType = layer.type || (hasCoordinates ? 'point_2d' : (layerAny.data ? 'scatter_2d' : 'function_2d'));
	const showLegend = totalLayers > 1;
	const legendName = `Layer ${layerIndex + 1}`;

	switch (layerType) {
		case 'parametric_2d':
		case 'function_parametric_2d':
			return buildParametric2DTraces(layer);
		case 'phase_plane':
			return buildPhasePlaneTraces(layer);
		case 'scatter_2d':
			return buildScatter2DTraces(layer, showLegend, legendName);
		case 'line_2d':
			return buildLine2DTraces(layer, showLegend, legendName);
		case 'histogram_2d':
			return buildHistogram2DTraces(layer, showLegend, legendName);
		case 'vector_2d':
			return buildVector2DTraces(layer, showLegend, legendName);
		case 'point_2d':
			return buildPoint2DTraces(layer, showLegend, legendName);
		case 'pie_2d':
			return buildPie2DTraces(layer, showLegend, legendName);
		case 'bar_2d':
			return buildBar2DTraces(layer, showLegend, legendName);
		case 'heatmap_2d':
			return buildHeatmap2DTraces(layer);
		case 'contour_2d':
			return buildContour2DTraces(layer);
		case 'implicit_2d':
			return buildImplicit2DTraces(layer);
		case 'function_2d':
		default:
			return buildFunction2DTraces(layer);
	}
}

// composite_2d: 여러 2D 레이어 합성
export function buildComposite2DTraces(spec: GraphSpec): any[] {
	// Support both 'layers' and 'graphs' field names
	const specAny = spec as unknown as Record<string, unknown>;
	const layers = spec.layers || (specAny.graphs as LayerSpec[]) || [];
	if (layers.length === 0) {
		console.error('[GraphBuilder] composite_2d requires layers or graphs array');
		return [];
	}

	console.log('[GraphBuilder] Building composite_2d with', layers.length, 'layers');

	const allTraces: any[] = [];
	layers.forEach((layer: LayerSpec, index: number) => {
		console.log(`[GraphBuilder] Processing layer ${index}:`, layer.type);
		const traces = buildLayerTraces(layer, index, layers.length);
		console.log(`[GraphBuilder] Layer ${index} produced ${traces.length} traces`);
		allTraces.push(...traces);
	});

	console.log('[GraphBuilder] Total traces for composite_2d:', allTraces.length);
	return allTraces;
}

// ========== Main Builder ==========

export function buildTraces(spec: GraphSpec): any[] {
	console.log('[GraphBuilder] buildTraces called with type:', spec.type);

	switch (spec.type) {
		// 2D graphs
		case 'composite_2d':
		case 'multi_scatter_2d':
		case 'cartesian': // cartesian = composite_2d
			return buildComposite2DTraces(spec);
		case 'parametric_2d':
		case 'function_parametric_2d':
			return buildParametric2DTraces(spec);
		case 'phase_plane':
			return buildPhasePlaneTraces(spec);
		case 'scatter_2d':
			return buildScatter2DTraces(spec);
		case 'line_2d':
			return buildLine2DTraces(spec);
		case 'histogram_2d':
			return buildHistogram2DTraces(spec);
		case 'vector_2d':
			return buildVector2DTraces(spec);
		case 'pie_2d':
			return buildPie2DTraces(spec);
		case 'bar_2d':
			return buildBar2DTraces(spec);
		case 'heatmap_2d':
			return buildHeatmap2DTraces(spec);
		case 'contour_2d':
			return buildContour2DTraces(spec);
		case 'implicit_2d':
			return buildImplicit2DTraces(spec);
		// 3D graphs
		case 'function_3d':
			return buildFunction3DTraces(spec);
		case 'parametric_3d':
			return buildParametric3DTraces(spec);
		case 'scatter_3d':
			return buildScatter3DTraces(spec);
		case 'composite_3d':
			return buildComposite3DTraces(spec);
		case 'vector_field_3d':
			return buildVectorField3DTraces(spec);
		case 'function_2d':
		default:
			return buildFunction2DTraces(spec);
	}
}
