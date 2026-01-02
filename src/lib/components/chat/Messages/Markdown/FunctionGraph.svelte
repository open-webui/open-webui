<script lang="ts">
	import { onMount, onDestroy, getContext } from 'svelte';
	import { compile } from 'mathjs';
	import type { GraphSpec, GraphSpecLayer, Domain3D, Sampling3D } from '$lib/utils/marked/graph-spec-extension';
	import GraphPreviewModal from './GraphPreviewModal.svelte';
	import ArrowsPointingOut from '$lib/components/icons/ArrowsPointingOut.svelte';

	const i18n = getContext('i18n');

	export let spec: GraphSpec;

	let container: HTMLDivElement;
	let Plotly: any;
	let showModal = false;

	// 다크모드 감지
	function isDarkMode(): boolean {
		return document.documentElement.classList.contains('dark');
	}

	type LayerSpec = GraphSpec | GraphSpecLayer;

	// expressions를 배열로 정규화 (expression 또는 expressions 지원)
	function normalizeExpressions(layer: LayerSpec): string[] {
		// expression (singular) 체크
		if (layer.expression) {
			return [layer.expression];
		}
		// expressions (plural) 체크
		if (!layer.expressions) return [];
		return Array.isArray(layer.expressions) ? layer.expressions : [layer.expressions];
	}

	// colors를 배열로 정규화
	function normalizeColors(layer: LayerSpec): string[] {
		if (!layer.style?.color) return [];
		return Array.isArray(layer.style.color) ? layer.style.color : [layer.style.color];
	}

	// lineStyle을 Plotly dash 형식으로 변환
	function getLineDash(lineStyle?: string): string | undefined {
		switch (lineStyle) {
			case 'dashed': return 'dash';
			case 'dotted': return 'dot';
			default: return undefined;
		}
	}

	// marker 스타일 매핑
	const markerSymbolMap: Record<string, string> = {
		circle: 'circle',
		square: 'square',
		triangle: 'triangle-up',
		diamond: 'diamond',
		cross: 'cross'
	};

	// 2D 도메인 추출 헬퍼 (배열 또는 객체 형식 지원)
	function getDomain2D(domain: any, defaultVal: [number, number] = [-10, 10]): [number, number] {
		if (!domain) return defaultVal;
		// 배열 형식: [-2, 2]
		if (Array.isArray(domain)) return domain as [number, number];
		// 객체 형식: { x: [-2, 2] }
		if (domain.x && Array.isArray(domain.x)) return domain.x as [number, number];
		return defaultVal;
	}

	// function_2d: y = f(x)
	function buildFunction2DTraces(layer: LayerSpec) {
		const expressions = normalizeExpressions(layer);
		const colors = normalizeColors(layer);

		return expressions.map((expr, i) => {
			const f = compile(expr);
			const [x0, x1] = getDomain2D(layer.domain);
			const sampling = typeof layer.sampling === 'number' ? layer.sampling : 200;

			const x: number[] = [];
			const y: number[] = [];

			for (let j = 0; j < sampling; j++) {
				const xv = x0 + ((x1 - x0) * j) / (sampling - 1);
				x.push(xv);
				try {
					y.push(f.evaluate({ x: xv }));
				} catch {
					y.push(NaN);
				}
			}

			const legendName = expr.length > 20 ? expr.slice(0, 20) + '...' : expr;

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
	function buildParametric2DTraces(layer: LayerSpec) {
		const expressions = normalizeExpressions(layer);
		const colors = normalizeColors(layer);

		if (expressions.length < 2) {
			console.error('[FunctionGraph] parametric_2d requires 2 expressions');
			return [];
		}

		const fX = compile(expressions[0]);
		const fY = compile(expressions[1]);
		const [t0, t1] = layer.domain || [0, Math.PI * 2];
		const sampling = layer.sampling || 200;

		const x: number[] = [];
		const y: number[] = [];

		for (let j = 0; j < sampling; j++) {
			const t = t0 + ((t1 - t0) * j) / (sampling - 1);
			try {
				x.push(fX.evaluate({ t }));
				y.push(fY.evaluate({ t }));
			} catch {
				x.push(NaN);
				y.push(NaN);
			}
		}

		const name = `(${expressions[0]}, ${expressions[1]})`;
		const legendName = name.length > 20 ? name.slice(0, 20) + '...' : name;

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
	function buildPhasePlaneTraces(layer: LayerSpec) {
		const expressions = normalizeExpressions(layer);
		const colors = normalizeColors(layer);

		if (expressions.length < 2) {
			console.error('[FunctionGraph] phase_plane requires 2 expressions');
			return [];
		}

		const fDx = compile(expressions[0]);
		const fDy = compile(expressions[1]);
		const [min, max] = layer.domain || [-5, 5];
		const sampling = layer.sampling || 20;

		const x: number[] = [];
		const y: number[] = [];
		const u: number[] = [];
		const v: number[] = [];

		const step = (max - min) / (sampling - 1);

		for (let i = 0; i < sampling; i++) {
			for (let j = 0; j < sampling; j++) {
				const xv = min + i * step;
				const yv = min + j * step;
				x.push(xv);
				y.push(yv);
				try {
					const dx = fDx.evaluate({ x: xv, y: yv });
					const dy = fDy.evaluate({ x: xv, y: yv });
					// 정규화하여 화살표 크기 일정하게
					const mag = Math.sqrt(dx * dx + dy * dy);
					if (mag > 0) {
						u.push(dx / mag);
						v.push(dy / mag);
					} else {
						u.push(0);
						v.push(0);
					}
				} catch {
					u.push(0);
					v.push(0);
				}
			}
		}

		// Plotly의 cone 또는 quiver 대신 annotation arrows 사용
		// 간단히 scatter로 시작점과 끝점을 표현
		const traces: any[] = [];
		const arrowScale = step * 0.4;

		for (let i = 0; i < x.length; i++) {
			traces.push({
				x: [x[i], x[i] + u[i] * arrowScale],
				y: [y[i], y[i] + v[i] * arrowScale],
				type: 'scatter',
				mode: 'lines',
				line: {
					color: colors[0] || '#666',
					width: layer.style?.lineWidth ?? 1
				},
				opacity: layer.style?.opacity,
				showlegend: false,
				hoverinfo: 'skip'
			});
		}

		return traces;
	}

	// scatter_2d: 산점도 (data: [[x, y], ...])
	function buildScatter2DTraces(layer: LayerSpec, showLegend = false, legendName?: string) {
		const colors = normalizeColors(layer);
		const data = layer.data || [];

		if (data.length === 0) {
			console.error('[FunctionGraph] scatter_2d requires data array');
			return [];
		}

		const x = data.map((point) => point[0]);
		const y = data.map((point) => point[1]);
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

	// ========== 3D Graph Builders ==========

	// 3D 도메인 헬퍼
	function getDomain3D(domain: Domain3D | undefined, key: 'x' | 'y' | 'u' | 'v' | 't', defaultVal: [number, number]): [number, number] {
		if (!domain || Array.isArray(domain)) return defaultVal;
		return domain[key] || defaultVal;
	}

	// 3D 샘플링 헬퍼
	function getSampling3D(sampling: Sampling3D | number | undefined, key: 'x' | 'y' | 'u' | 'v' | 't', defaultVal: number): number {
		if (!sampling) return defaultVal;
		if (typeof sampling === 'number') return sampling;
		return sampling[key] || defaultVal;
	}

	// function_3d: z = f(x, y) 표면
	function buildFunction3DTraces(layer: LayerSpec) {
		const expr = layer.expression || (layer.expressions ? normalizeExpressions(layer)[0] : 'x^2 + y^2');
		const f = compile(expr);

		const domain = layer.domain as Domain3D | undefined;
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

	// parametric_3d: x = f(u,v), y = g(u,v), z = h(u,v) 또는 x = f(t), y = g(t), z = h(t)
	function buildParametric3DTraces(layer: LayerSpec) {
		const expressions = normalizeExpressions(layer);
		const colors = normalizeColors(layer);

		if (expressions.length < 3) {
			console.error('[FunctionGraph] parametric_3d requires 3 expressions');
			return [];
		}

		const fX = compile(expressions[0]);
		const fY = compile(expressions[1]);
		const fZ = compile(expressions[2]);

		const domain = layer.domain as Domain3D | undefined;

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

	// scatter_3d: 3D 산점도 (data: [[x, y, z], ...])
	function buildScatter3DTraces(layer: LayerSpec, showLegend = false, legendName?: string) {
		const colors = normalizeColors(layer);
		const data = (layer.data || []) as [number, number, number][];

		if (data.length === 0) {
			console.error('[FunctionGraph] scatter_3d requires data array');
			return [];
		}

		const x = data.map((point) => point[0]);
		const y = data.map((point) => point[1]);
		const z = data.map((point) => point[2]);

		return [{
			x, y, z,
			type: 'scatter3d',
			mode: 'markers',
			marker: {
				symbol: layer.style?.marker === 'sphere' ? 'circle' : (layer.style?.marker || 'circle'),
				size: layer.style?.size ?? 5,
				color: colors[0] || 'blue',
				opacity: layer.style?.opacity ?? 0.9
			},
			name: legendName || 'scatter',
			showlegend: showLegend
		}];
	}

	// 3D 레이어 trace 빌드
	function buildLayer3DTraces(layer: LayerSpec, layerIndex: number, totalLayers: number): any[] {
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
			default:
				return [];
		}
	}

	// composite_3d: 여러 3D 레이어 합성
	function buildComposite3DTraces(spec: GraphSpec): any[] {
		const layers = spec.layers || [];
		if (layers.length === 0) {
			console.error('[FunctionGraph] composite_3d requires layers array');
			return [];
		}

		const allTraces: any[] = [];
		layers.forEach((layer, index) => {
			const traces = buildLayer3DTraces(layer, index, layers.length);
			allTraces.push(...traces);
		});
		return allTraces;
	}

	// 3D 그래프인지 확인
	function is3DGraph(type: string): boolean {
		return ['function_3d', 'parametric_3d', 'scatter_3d', 'composite_3d'].includes(type);
	}

	// ========== End 3D Graph Builders ==========

	// 단일 레이어에 대한 trace 빌드
	function buildLayerTraces(layer: LayerSpec, layerIndex: number, totalLayers: number): any[] {
		// type이 없으면 data 유무로 타입 추론
		const layerType = layer.type || (layer.data ? 'scatter_2d' : 'function_2d');
		const showLegend = totalLayers > 1;
		const legendName = `Layer ${layerIndex + 1}`;

		switch (layerType) {
			case 'parametric_2d':
				return buildParametric2DTraces(layer);
			case 'phase_plane':
				return buildPhasePlaneTraces(layer);
			case 'scatter_2d':
				return buildScatter2DTraces(layer, showLegend, legendName);
			case 'function_2d':
			default:
				return buildFunction2DTraces(layer);
		}
	}

	// composite_2d: 여러 레이어를 합성
	function buildComposite2DTraces(spec: GraphSpec): any[] {
		const layers = spec.layers || [];
		if (layers.length === 0) {
			console.error('[FunctionGraph] composite_2d requires layers array');
			return [];
		}

		const allTraces: any[] = [];
		layers.forEach((layer, index) => {
			const traces = buildLayerTraces(layer, index, layers.length);
			allTraces.push(...traces);
		});
		return allTraces;
	}

	function buildTraces(spec: GraphSpec) {
		switch (spec.type) {
			// 2D graphs
			case 'composite_2d':
			case 'multi_scatter_2d':
				return buildComposite2DTraces(spec);
			case 'parametric_2d':
				return buildParametric2DTraces(spec);
			case 'phase_plane':
				return buildPhasePlaneTraces(spec);
			case 'scatter_2d':
				return buildScatter2DTraces(spec);
			// 3D graphs
			case 'function_3d':
				return buildFunction3DTraces(spec);
			case 'parametric_3d':
				return buildParametric3DTraces(spec);
			case 'scatter_3d':
				return buildScatter3DTraces(spec);
			case 'composite_3d':
				return buildComposite3DTraces(spec);
			case 'function_2d':
			default:
				return buildFunction2DTraces(spec);
		}
	}

	function getLayout(dark: boolean) {
		const textColor = dark ? '#FDFEFE' : '#1f2937';
		const gridColor = dark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)';
		const expressions = normalizeExpressions(spec);

		// 범례 표시 여부 결정
		const shouldShowLegend = expressions.length > 1 ||
			(spec.layers && spec.layers.length > 1) ||
			spec.type === 'composite_2d' ||
			spec.type === 'multi_scatter_2d' ||
			spec.type === 'composite_3d';

		const baseLayout = {
			margin: { t: 20, r: 20, b: 40, l: 50 }, // 썸네일용 작은 마진
			showlegend: false, // 썸네일에서는 범례 숨김
			legend: {
				x: 1,
				xanchor: 'right',
				y: 1,
				font: { color: textColor },
				bgcolor: 'rgba(0,0,0,0)'
			},
			paper_bgcolor: 'transparent',
			plot_bgcolor: 'transparent',
			font: {
				color: textColor
			}
		};

		// 3D 그래프용 레이아웃 (썸네일용 작은 마진과 명시적 크기)
		if (is3DGraph(spec.type)) {
			return {
				...baseLayout,
				width: 192, // 썸네일 크기 (w-48 = 192px)
				height: 192,
				margin: { t: 5, r: 5, b: 5, l: 5 }, // 3D용 더 작은 마진
				scene: {
					xaxis: {
						title: '', // 썸네일에서는 축 제목 숨김
						showgrid: spec.axis?.grid ?? true,
						gridcolor: gridColor,
						tickfont: { color: textColor, size: 8 },
						backgroundcolor: 'transparent',
						showticklabels: false // 썸네일에서는 눈금 숨김
					},
					yaxis: {
						title: '',
						showgrid: spec.axis?.grid ?? true,
						gridcolor: gridColor,
						tickfont: { color: textColor, size: 8 },
						backgroundcolor: 'transparent',
						showticklabels: false
					},
					zaxis: {
						title: '',
						showgrid: spec.axis?.grid ?? true,
						gridcolor: gridColor,
						tickfont: { color: textColor, size: 8 },
						backgroundcolor: 'transparent',
						showticklabels: false
					},
					bgcolor: 'transparent',
					camera: {
						eye: { x: 1.8, y: 1.8, z: 1.5 } // 좀 더 넓은 시야
					},
					aspectmode: 'cube' // 정사각형 비율
				}
			};
		}

		// 2D 그래프용 레이아웃
		return {
			...baseLayout,
			width: 192, // 썸네일 크기 (w-48 = 192px)
			height: 192,
			margin: { t: 10, r: 10, b: 25, l: 30 }, // 2D용 작은 마진
			xaxis: {
				title: '', // 썸네일에서는 축 제목 숨김
				showgrid: spec.axis?.grid ?? true,
				gridcolor: gridColor,
				zeroline: true,
				zerolinecolor: gridColor,
				tickfont: { color: textColor, size: 9 }
			},
			yaxis: {
				title: '',
				showgrid: spec.axis?.grid ?? true,
				gridcolor: gridColor,
				zeroline: true,
				zerolinecolor: gridColor,
				tickfont: { color: textColor, size: 9 },
				scaleanchor: spec.type === 'phase_plane' ? 'x' : undefined,
				scaleratio: spec.type === 'phase_plane' ? 1 : undefined
			}
		};
	}

	onMount(async () => {
		// 디버깅: graph spec 출력
		console.log('[FunctionGraph] Received spec:', JSON.stringify(spec, null, 2));

		// Dynamically import Plotly to avoid SSR issues
		const plotlyModule = await import('plotly.js-dist-min');
		Plotly = plotlyModule.default;

		const data = buildTraces(spec);
		console.log('[FunctionGraph] Built traces:', data);
		const dark = isDarkMode();
		const layout = getLayout(dark);

		// 3D 그래프는 staticPlot: true 시 WebGL 렌더링 문제가 있을 수 있음
		const is3D = is3DGraph(spec.type);
		const config = {
			responsive: !is3D, // 3D는 명시적 크기 사용
			displayModeBar: false, // 썸네일에서는 모드바 숨김
			displaylogo: false,
			staticPlot: !is3D, // 3D는 staticPlot을 끄고 상호작용 허용 (드래그로 회전 가능)
			scrollZoom: false // 썸네일에서는 줌 비활성화
		};

		Plotly.newPlot(container, data, layout, config);

		// 테마 변경 감지
		const observer = new MutationObserver(() => {
			const newDark = isDarkMode();
			Plotly.relayout(container, getLayout(newDark));
		});

		observer.observe(document.documentElement, {
			attributes: true,
			attributeFilter: ['class']
		});
	});

	onDestroy(() => {
		if (Plotly && container) {
			Plotly.purge(container);
		}
	});
</script>

<!-- Thumbnail container with modal trigger -->
<div class="relative w-48 h-48 group mb-2 rounded-lg border border-gray-100 dark:border-gray-850 overflow-hidden">
	<!-- Graph thumbnail (정사각형) -->
	<div class="w-48 h-48 bg-white dark:bg-gray-800">
		<div bind:this={container} class="w-full h-full" />
	</div>

	<!-- Gradient overlay -->
	<div
		class="absolute bottom-0 left-0 right-0 h-12 bg-gradient-to-t from-white dark:from-gray-900 to-transparent pointer-events-none"
	/>

	<!-- View full graph button -->
	<button
		class="absolute bottom-2 left-1/2 -translate-x-1/2 flex items-center gap-1 text-[11px] text-gray-700 dark:text-gray-300 bg-white/80 dark:bg-gray-900/80 px-2 py-1 rounded-full backdrop-blur-sm hover:bg-white dark:hover:bg-gray-800 transition z-10"
		on:click={() => (showModal = true)}
	>
		<ArrowsPointingOut className="size-3" />
		<span>{$i18n.t('확대')}</span>
	</button>
</div>

<!-- Graph preview modal -->
<GraphPreviewModal bind:show={showModal} {spec} />
