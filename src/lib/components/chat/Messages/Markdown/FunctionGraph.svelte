<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { compile } from 'mathjs';
	import type { GraphSpec, GraphSpecLayer } from '$lib/utils/marked/graph-spec-extension';

	export let spec: GraphSpec;

	let container: HTMLDivElement;
	let Plotly: any;

	// 다크모드 감지
	function isDarkMode(): boolean {
		return document.documentElement.classList.contains('dark');
	}

	type LayerSpec = GraphSpec | GraphSpecLayer;

	// expressions를 배열로 정규화
	function normalizeExpressions(layer: LayerSpec): string[] {
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

	// function_2d: y = f(x)
	function buildFunction2DTraces(layer: LayerSpec) {
		const expressions = normalizeExpressions(layer);
		const colors = normalizeColors(layer);

		return expressions.map((expr, i) => {
			const f = compile(expr);
			const [x0, x1] = layer.domain || [-10, 10];
			const sampling = layer.sampling || 200;

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
				showlegend: false
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
	function buildScatter2DTraces(layer: LayerSpec) {
		const colors = normalizeColors(layer);
		const data = layer.data || [];

		if (data.length === 0) {
			console.error('[FunctionGraph] scatter_2d requires data array');
			return [];
		}

		const x = data.map((point) => point[0]);
		const y = data.map((point) => point[1]);

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
			showlegend: false
		}];
	}

	// 단일 레이어에 대한 trace 빌드
	function buildLayerTraces(layer: LayerSpec): any[] {
		// type이 없으면 data 유무로 타입 추론
		const layerType = layer.type || (layer.data ? 'scatter_2d' : 'function_2d');

		switch (layerType) {
			case 'parametric_2d':
				return buildParametric2DTraces(layer);
			case 'phase_plane':
				return buildPhasePlaneTraces(layer);
			case 'scatter_2d':
				return buildScatter2DTraces(layer);
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
		for (const layer of layers) {
			const traces = buildLayerTraces(layer);
			allTraces.push(...traces);
		}
		return allTraces;
	}

	function buildTraces(spec: GraphSpec) {
		switch (spec.type) {
			case 'composite_2d':
			case 'multi_scatter_2d':
				return buildComposite2DTraces(spec);
			case 'parametric_2d':
				return buildParametric2DTraces(spec);
			case 'phase_plane':
				return buildPhasePlaneTraces(spec);
			case 'scatter_2d':
				return buildScatter2DTraces(spec);
			case 'function_2d':
			default:
				return buildFunction2DTraces(spec);
		}
	}

	function getLayout(dark: boolean) {
		const textColor = dark ? '#FDFEFE' : '#1f2937';
		const gridColor = dark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)';
		const expressions = normalizeExpressions(spec);

		return {
			xaxis: {
				title: { text: spec.axis?.xLabel || 'x', font: { color: textColor } },
				showgrid: spec.axis?.grid ?? true,
				gridcolor: gridColor,
				zeroline: true,
				zerolinecolor: gridColor,
				tickfont: { color: textColor }
			},
			yaxis: {
				title: { text: spec.axis?.yLabel || 'y', font: { color: textColor } },
				showgrid: spec.axis?.grid ?? true,
				gridcolor: gridColor,
				zeroline: true,
				zerolinecolor: gridColor,
				tickfont: { color: textColor },
				scaleanchor: spec.type === 'phase_plane' ? 'x' : undefined,
				scaleratio: spec.type === 'phase_plane' ? 1 : undefined
			},
			margin: { t: 30, r: 30, b: 50, l: 60 },
			showlegend: spec.type === 'function_2d' && expressions.length > 1,
			legend: {
				x: 1,
				xanchor: 'right',
				y: 1,
				font: { color: textColor }
			},
			paper_bgcolor: 'transparent',
			plot_bgcolor: 'transparent',
			font: {
				color: textColor
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

		const config = {
			responsive: true,
			displayModeBar: true,
			displaylogo: false,
			modeBarButtonsToRemove: ['lasso2d', 'select2d']
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

<div class="w-full rounded-xl bg-white dark:bg-gray-800 p-4 my-4 shadow-sm border border-gray-200 dark:border-gray-700">
	<div bind:this={container} class="w-full h-80" />
</div>
