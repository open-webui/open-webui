<script lang="ts">
	import { getContext, onMount, onDestroy } from 'svelte';
	import { compile } from 'mathjs';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import type { GraphSpec, GraphSpecLayer, Domain3D, Sampling3D } from '$lib/utils/marked/graph-spec-extension';

	const i18n = getContext('i18n');

	export let show = false;
	export let spec: GraphSpec;

	let container: HTMLDivElement;
	let Plotly: any;
	let plotInitialized = false;
	let showJsonCode = false;
	let jsonCopied = false;

	// Copy JSON to clipboard
	const copyJsonToClipboard = async () => {
		try {
			await navigator.clipboard.writeText(JSON.stringify(spec, null, 2));
			jsonCopied = true;
			setTimeout(() => { jsonCopied = false; }, 2000);
		} catch (err) {
			console.error('Failed to copy:', err);
		}
	};

	// 다크모드 감지
	function isDarkMode(): boolean {
		return document.documentElement.classList.contains('dark');
	}

	type LayerSpec = GraphSpec | GraphSpecLayer;

	function normalizeExpressions(layer: LayerSpec): string[] {
		// expression (singular) 체크
		if (layer.expression) {
			return [layer.expression];
		}
		// expressions (plural) 체크
		if (!layer.expressions) return [];
		return Array.isArray(layer.expressions) ? layer.expressions : [layer.expressions];
	}

	function normalizeColors(layer: LayerSpec): string[] {
		if (!layer.style?.color) return [];
		return Array.isArray(layer.style.color) ? layer.style.color : [layer.style.color];
	}

	function getLineDash(lineStyle?: string): string | undefined {
		switch (lineStyle) {
			case 'dashed': return 'dash';
			case 'dotted': return 'dot';
			default: return undefined;
		}
	}

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
		if (Array.isArray(domain)) return domain as [number, number];
		if (domain.x && Array.isArray(domain.x)) return domain.x as [number, number];
		return defaultVal;
	}

	// ========== 2D Builders ==========
	function buildFunction2DTraces(layer: LayerSpec) {
		const expressions = normalizeExpressions(layer);
		const colors = normalizeColors(layer);

		return expressions.map((expr, i) => {
			const f = compile(expr);
			const [x0, x1] = getDomain2D(layer.domain);
			const sampling = (layer.sampling as number) || 200;

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

			const legendName = expr.length > 30 ? expr.slice(0, 30) + '...' : expr;

			return {
				x, y,
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

	function buildParametric2DTraces(layer: LayerSpec) {
		const expressions = normalizeExpressions(layer);
		const colors = normalizeColors(layer);

		if (expressions.length < 2) return [];

		const fX = compile(expressions[0]);
		const fY = compile(expressions[1]);
		const [t0, t1] = (layer.domain as [number, number]) || [0, Math.PI * 2];
		const sampling = (layer.sampling as number) || 200;

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

		return [{
			x, y,
			type: 'scatter',
			mode: 'lines',
			line: {
				color: colors[0] || undefined,
				width: layer.style?.lineWidth ?? 2
			},
			showlegend: false
		}];
	}

	function buildScatter2DTraces(layer: LayerSpec) {
		const colors = normalizeColors(layer);
		const data = layer.data || [];

		if (data.length === 0) return [];

		const x = data.map((point) => point[0]);
		const y = data.map((point) => point[1]);

		return [{
			x, y,
			type: 'scatter',
			mode: 'markers',
			marker: {
				symbol: markerSymbolMap[layer.style?.marker || 'circle'] || 'circle',
				size: layer.style?.size ?? 8,
				color: colors[0] || '#1f77b4'
			},
			showlegend: false
		}];
	}

	function buildPhasePlaneTraces(layer: LayerSpec) {
		const expressions = normalizeExpressions(layer);
		const colors = normalizeColors(layer);

		if (expressions.length < 2) return [];

		const fDx = compile(expressions[0]);
		const fDy = compile(expressions[1]);
		const [min, max] = (layer.domain as [number, number]) || [-5, 5];
		const sampling = (layer.sampling as number) || 20;

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
				} catch {}
			}
		}
		return traces;
	}

	// ========== 3D Helpers ==========
	function getDomain3D(domain: Domain3D | undefined, key: 'x' | 'y' | 'u' | 'v' | 't', defaultVal: [number, number]): [number, number] {
		if (!domain || Array.isArray(domain)) return defaultVal;
		return domain[key] || defaultVal;
	}

	function getSampling3D(sampling: Sampling3D | number | undefined, key: 'x' | 'y' | 'u' | 'v' | 't', defaultVal: number): number {
		if (!sampling) return defaultVal;
		if (typeof sampling === 'number') return sampling;
		return sampling[key] || defaultVal;
	}

	// ========== 3D Builders ==========
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
			x: xVals, y: yVals, z: zVals,
			type: 'surface',
			colorscale: layer.style?.colorMap || 'Viridis',
			opacity: layer.style?.opacity ?? 0.9,
			showscale: false
		}];
	}

	function buildParametric3DTraces(layer: LayerSpec) {
		const expressions = normalizeExpressions(layer);
		const colors = normalizeColors(layer);

		if (expressions.length < 3) return [];

		const fX = compile(expressions[0]);
		const fY = compile(expressions[1]);
		const fZ = compile(expressions[2]);

		const domain = layer.domain as Domain3D | undefined;
		const hasTDomain = domain && 't' in domain;
		const hasUVDomain = domain && ('u' in domain || 'v' in domain);

		if (hasTDomain || !hasUVDomain) {
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
				line: { color: colors[0] || 'red', width: layer.style?.lineWidth ?? 3 }
			}];
		} else {
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
				x: xVals, y: yVals, z: zVals,
				type: 'surface',
				colorscale: layer.style?.colorMap || 'Plasma',
				opacity: layer.style?.opacity ?? 0.9,
				showscale: false
			}];
		}
	}

	function buildScatter3DTraces(layer: LayerSpec) {
		const colors = normalizeColors(layer);
		const data = (layer.data || []) as [number, number, number][];

		if (data.length === 0) return [];

		return [{
			x: data.map(p => p[0]),
			y: data.map(p => p[1]),
			z: data.map(p => p[2]),
			type: 'scatter3d',
			mode: 'markers',
			marker: {
				size: layer.style?.size ?? 5,
				color: colors[0] || 'blue'
			}
		}];
	}

	function buildLayer3DTraces(layer: LayerSpec): any[] {
		switch (layer.type) {
			case 'function_3d': return buildFunction3DTraces(layer);
			case 'parametric_3d': return buildParametric3DTraces(layer);
			case 'scatter_3d': return buildScatter3DTraces(layer);
			default: return [];
		}
	}

	function buildLayerTraces(layer: LayerSpec): any[] {
		const layerType = layer.type || (layer.data ? 'scatter_2d' : 'function_2d');
		switch (layerType) {
			case 'parametric_2d': return buildParametric2DTraces(layer);
			case 'phase_plane': return buildPhasePlaneTraces(layer);
			case 'scatter_2d': return buildScatter2DTraces(layer);
			case 'function_2d': default: return buildFunction2DTraces(layer);
		}
	}

	function buildCompositeTraces(spec: GraphSpec, is3D: boolean): any[] {
		const layers = spec.layers || [];
		const allTraces: any[] = [];
		layers.forEach((layer) => {
			const traces = is3D ? buildLayer3DTraces(layer) : buildLayerTraces(layer);
			allTraces.push(...traces);
		});
		return allTraces;
	}

	function is3DGraph(type: string): boolean {
		return ['function_3d', 'parametric_3d', 'scatter_3d', 'composite_3d'].includes(type);
	}

	function buildTraces(spec: GraphSpec) {
		const is3D = is3DGraph(spec.type);
		switch (spec.type) {
			case 'composite_2d':
			case 'multi_scatter_2d':
				return buildCompositeTraces(spec, false);
			case 'composite_3d':
				return buildCompositeTraces(spec, true);
			case 'parametric_2d': return buildParametric2DTraces(spec);
			case 'phase_plane': return buildPhasePlaneTraces(spec);
			case 'scatter_2d': return buildScatter2DTraces(spec);
			case 'function_3d': return buildFunction3DTraces(spec);
			case 'parametric_3d': return buildParametric3DTraces(spec);
			case 'scatter_3d': return buildScatter3DTraces(spec);
			case 'function_2d':
			default: return buildFunction2DTraces(spec);
		}
	}

	function getLayout(dark: boolean) {
		const textColor = dark ? '#FDFEFE' : '#1f2937';
		const gridColor = dark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)';

		const baseLayout = {
			margin: { t: 40, r: 40, b: 60, l: 70 },
			showlegend: true,
			legend: { x: 1, xanchor: 'right', y: 1, font: { color: textColor } },
			paper_bgcolor: 'transparent',
			plot_bgcolor: 'transparent',
			font: { color: textColor }
		};

		if (is3DGraph(spec.type)) {
			return {
				...baseLayout,
				scene: {
					xaxis: { title: { text: spec.axis?.xLabel || 'X' }, showgrid: true, gridcolor: gridColor, tickfont: { color: textColor } },
					yaxis: { title: { text: spec.axis?.yLabel || 'Y' }, showgrid: true, gridcolor: gridColor, tickfont: { color: textColor } },
					zaxis: { title: { text: spec.axis?.zLabel || 'Z' }, showgrid: true, gridcolor: gridColor, tickfont: { color: textColor } },
					bgcolor: 'transparent',
					camera: { eye: { x: 1.5, y: 1.5, z: 1.2 } }
				}
			};
		}

		return {
			...baseLayout,
			xaxis: { title: { text: spec.axis?.xLabel || 'x' }, showgrid: true, gridcolor: gridColor, tickfont: { color: textColor } },
			yaxis: { title: { text: spec.axis?.yLabel || 'y' }, showgrid: true, gridcolor: gridColor, tickfont: { color: textColor } }
		};
	}

	async function initPlot() {
		if (!container || !show || plotInitialized) return;

		const plotlyModule = await import('plotly.js-dist-min');
		Plotly = plotlyModule.default;

		const data = buildTraces(spec);
		const dark = isDarkMode();
		const layout = getLayout(dark);

		const config = {
			responsive: true,
			displayModeBar: true,
			displaylogo: false,
			modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d', 'hoverClosestCartesian', 'hoverCompareCartesian'],
			toImageButtonOptions: {
				format: 'png',
				filename: 'graph_export',
				height: 800,
				width: 1200,
				scale: 2
			}
		};

		Plotly.newPlot(container, data, layout, config);
		plotInitialized = true;
	}

	$: if (show && container) {
		initPlot();
	}

	$: if (!show) {
		plotInitialized = false;
		if (Plotly && container) {
			Plotly.purge(container);
		}
	}

	// Resize plot when JSON view is toggled
	$: {
		// Explicitly track showJsonCode changes
		const _ = showJsonCode;
		if (plotInitialized && Plotly && container) {
			setTimeout(() => {
				Plotly.Plots.resize(container);
			}, 100);
		}
	}
</script>

<style>
	/* Custom Plotly modebar styling */
	:global(.modebar) {
		background: transparent !important;
		top: 12px !important;
		right: 12px !important;
	}
	:global(.modebar-group) {
		background: rgba(255, 255, 255, 0.95) !important;
		backdrop-filter: blur(12px);
		-webkit-backdrop-filter: blur(12px);
		border-radius: 10px !important;
		padding: 6px !important;
		margin-left: 6px !important;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.05) !important;
		border: 1px solid rgba(0, 0, 0, 0.05) !important;
	}
	:global(.dark .modebar-group) {
		background: rgba(31, 41, 55, 0.95) !important;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3), 0 1px 3px rgba(0, 0, 0, 0.2) !important;
		border: 1px solid rgba(255, 255, 255, 0.05) !important;
	}
	:global(.modebar-btn) {
		padding: 6px !important;
		border-radius: 6px !important;
		margin: 1px !important;
		transition: all 0.15s ease !important;
	}
	:global(.modebar-btn:hover) {
		background: rgba(59, 130, 246, 0.1) !important;
	}
	:global(.dark .modebar-btn:hover) {
		background: rgba(59, 130, 246, 0.2) !important;
	}
	:global(.modebar-btn svg) {
		width: 18px !important;
		height: 18px !important;
		transition: transform 0.15s ease !important;
	}
	:global(.modebar-btn:hover svg) {
		transform: scale(1.1) !important;
	}
	:global(.modebar-btn path) {
		fill: #6b7280 !important;
		transition: fill 0.15s ease !important;
	}
	:global(.dark .modebar-btn path) {
		fill: #9ca3af !important;
	}
	:global(.modebar-btn:hover path) {
		fill: #3b82f6 !important;
	}
	:global(.modebar-btn.active path) {
		fill: #2563eb !important;
	}
	:global(.modebar-btn.active) {
		background: rgba(59, 130, 246, 0.15) !important;
	}
</style>

<Modal bind:show size="xl" className="bg-white dark:bg-gray-900 rounded-2xl">
	<div class="p-5">
		<!-- Header -->
		<div class="flex justify-between items-center mb-4">
			<h3 class="text-title-4 text-gray-900 dark:text-white">
				{$i18n.t('Graph View')}
			</h3>
			<div class="flex items-center gap-2">
				<!-- JSON toggle button -->
				<button
					class="flex items-center gap-1.5 px-3 py-1.5 text-caption rounded-lg transition
						{showJsonCode
							? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
							: 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'}"
					on:click={() => (showJsonCode = !showJsonCode)}
				>
					<svg class="size-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
					</svg>
					<span>JSON</span>
				</button>
				<button
					class="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
					on:click={() => (show = false)}
				>
					<XMark className="size-4" />
				</button>
			</div>
		</div>

		<!-- Content area -->
		<div class="flex gap-4 {showJsonCode ? 'flex-row' : 'flex-col'}">
			<!-- Graph container -->
			<div class="flex-1 {showJsonCode ? 'w-1/2' : 'w-full'} h-[60vh] border border-gray-100 dark:border-gray-800 rounded-lg overflow-hidden">
				<div bind:this={container} class="w-full h-full" />
			</div>

			<!-- JSON Code Viewer -->
			{#if showJsonCode}
				<div class="flex-1 w-1/2 h-[60vh] flex flex-col border border-gray-100 dark:border-gray-800 rounded-lg overflow-hidden">
					<!-- JSON Header -->
					<div class="flex justify-between items-center px-4 py-2 border-b border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50">
						<span class="text-caption text-gray-600 dark:text-gray-400">graph_spec.json</span>
						<button
							class="flex items-center gap-1.5 px-2 py-1 text-caption rounded transition
								{jsonCopied
									? 'text-green-600 dark:text-green-400'
									: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}"
							on:click={copyJsonToClipboard}
						>
							{#if jsonCopied}
								<svg class="size-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
								</svg>
								<span>Copied!</span>
							{:else}
								<svg class="size-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
								</svg>
								<span>Copy</span>
							{/if}
						</button>
					</div>
					<!-- JSON Content -->
					<pre class="flex-1 overflow-auto p-4 text-xs font-mono bg-gray-50 dark:bg-gray-900 text-gray-800 dark:text-gray-200">{JSON.stringify(spec, null, 2)}</pre>
				</div>
			{/if}
		</div>
	</div>
</Modal>
