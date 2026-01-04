<script lang="ts">
	import { onMount, onDestroy, getContext } from 'svelte';
	import { compile } from 'mathjs';
	import type { GraphSpec } from '$lib/utils/marked/graph-spec-extension';
	import GraphPreviewModal from './GraphPreviewModal.svelte';
	import ArrowsPointingOut from '$lib/components/icons/ArrowsPointingOut.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	// Import shared graph builder utilities
	import {
		normalizeExpressions,
		buildTraces,
		is3DGraph,
		isTypeSupported,
		validateTraces
	} from '$lib/utils/graph-builder';

	const i18n = getContext('i18n');

	export let spec: GraphSpec;

	let container: HTMLDivElement;
	let Plotly: any;
	let showModal = false;
	let renderError: string | null = null;
	let showErrorJsonModal = false;

	// 다크모드 감지
	function isDarkMode(): boolean {
		return document.documentElement.classList.contains('dark');
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
		const xaxis: any = {
			title: '', // 썸네일에서는 축 제목 숨김
			showgrid: spec.axis?.grid ?? true,
			gridcolor: gridColor,
			zeroline: true,
			zerolinecolor: gridColor,
			tickfont: { color: textColor, size: 9 }
		};
		const yaxis: any = {
			title: '',
			showgrid: spec.axis?.grid ?? true,
			gridcolor: gridColor,
			zeroline: true,
			zerolinecolor: gridColor,
			tickfont: { color: textColor, size: 9 },
			scaleanchor: spec.type === 'phase_plane' ? 'x' : undefined,
			scaleratio: spec.type === 'phase_plane' ? 1 : undefined
		};

		// Apply xRange and yRange if provided
		if (spec.axis?.xRange) {
			const xRange = spec.axis.xRange as any[];
			xaxis.range = [
				typeof xRange[0] === 'string' ? compile(xRange[0]).evaluate({}) : xRange[0],
				typeof xRange[1] === 'string' ? compile(xRange[1]).evaluate({}) : xRange[1]
			];
		}
		if (spec.axis?.yRange) {
			const yRange = spec.axis.yRange as any[];
			yaxis.range = [
				typeof yRange[0] === 'string' ? compile(yRange[0]).evaluate({}) : yRange[0],
				typeof yRange[1] === 'string' ? compile(yRange[1]).evaluate({}) : yRange[1]
			];
		}

		// Build annotations if provided
		const annotations: any[] = [];
		if (spec.annotations && Array.isArray(spec.annotations)) {
			spec.annotations.forEach((ann: any) => {
				if (ann.type === 'label' && ann.position && ann.text) {
					// Anchor 매핑
					const anchorMap: Record<string, { xanchor: string; yanchor: string }> = {
						'top-left': { xanchor: 'left', yanchor: 'top' },
						'top-right': { xanchor: 'right', yanchor: 'top' },
						'bottom-left': { xanchor: 'left', yanchor: 'bottom' },
						'bottom-right': { xanchor: 'right', yanchor: 'bottom' },
						'center': { xanchor: 'center', yanchor: 'middle' }
					};
					const anchor = anchorMap[ann.style?.anchor || 'bottom-left'] || anchorMap['bottom-left'];

					annotations.push({
						x: ann.position.x,
						y: ann.position.y,
						text: ann.text,
						showarrow: false,
						font: {
							size: Math.max(6, (ann.style?.fontSize || 12) * 0.5), // 썸네일용 작은 폰트
							color: ann.style?.color || textColor
						},
						xanchor: anchor.xanchor,
						yanchor: anchor.yanchor,
						opacity: ann.style?.opacity ?? 1
					});
				}
			});
		}

		return {
			...baseLayout,
			width: 192, // 썸네일 크기 (w-48 = 192px)
			height: 192,
			margin: { t: 10, r: 10, b: 25, l: 30 }, // 2D용 작은 마진
			xaxis,
			yaxis,
			annotations: annotations.length > 0 ? annotations : undefined
		};
	}

	onMount(async () => {
		// 디버깅: graph spec 출력
		console.log('[FunctionGraph] Received spec:', JSON.stringify(spec, null, 2));

		try {
			// Check if graph type is supported
			if (!isTypeSupported(spec.type)) {
				renderError = `지원하지 않는 그래프 타입: ${spec.type}`;
				console.error('[FunctionGraph] Unsupported type:', spec.type);
				return;
			}

			// Dynamically import Plotly to avoid SSR issues
			const plotlyModule = await import('plotly.js-dist-min');
			Plotly = plotlyModule.default;

			const data = buildTraces(spec);
			console.log('[FunctionGraph] Built traces:', data);

			// Validate traces for NaN/Infinity issues
			const validation = validateTraces(data);
			if (!validation.valid) {
				renderError = validation.error || '그래프 렌더링 오류';
				console.error('[FunctionGraph] Validation failed:', validation.error);
				return;
			}

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
				if (Plotly && container && !renderError) {
					Plotly.relayout(container, getLayout(newDark));
				}
			});

			observer.observe(document.documentElement, {
				attributes: true,
				attributeFilter: ['class']
			});
		} catch (e) {
			const errorMessage = e instanceof Error ? e.message : String(e);
			renderError = `그래프 렌더링 실패: ${errorMessage}`;
			console.error('[FunctionGraph] Render error:', e);
		}
	});

	onDestroy(() => {
		if (Plotly && container) {
			Plotly.purge(container);
		}
	});
</script>

<!-- Thumbnail container with modal trigger -->
{#if renderError}
	<!-- Error state - clickable to show JSON -->
	<button
		class="relative w-48 mb-2 rounded-lg border border-red-200 dark:border-red-800 overflow-hidden bg-red-50 dark:bg-red-900/20 cursor-pointer hover:bg-red-100 dark:hover:bg-red-900/30 transition text-left"
		on:click={() => (showErrorJsonModal = true)}
	>
		<div class="w-48 h-48 flex flex-col items-center justify-center p-4 text-center">
			<svg class="size-8 text-red-400 dark:text-red-500 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
			</svg>
			<div class="text-xs text-red-600 dark:text-red-400 font-medium mb-1">
				{$i18n.t('그래프 렌더링 오류')}
			</div>
			<div class="text-[10px] text-red-500 dark:text-red-400/80 leading-tight">
				{renderError}
			</div>
			<div class="text-[9px] text-red-400 dark:text-red-500/60 mt-2">
				{$i18n.t('클릭하여 JSON 보기')}
			</div>
		</div>
	</button>
{:else}
	<div class="relative w-48 group mb-2 rounded-lg border border-gray-100 dark:border-gray-850 overflow-hidden">
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
{/if}

<!-- Meta data (title only) - hide when error -->
{#if !renderError && spec.meta?.title}
	<div class="mt-2 text-sm">
		<div class="font-semibold text-gray-900 dark:text-gray-100">{spec.meta.title}</div>
	</div>
{/if}

<!-- Graph preview modal - only when no error -->
{#if !renderError}
	<GraphPreviewModal bind:show={showModal} {spec} />
{/if}

<!-- Error JSON modal -->
<Modal bind:show={showErrorJsonModal} size="lg">
	<div class="px-6 py-5 w-full max-w-2xl bg-white dark:bg-gray-900 rounded-xl">
		<!-- Header -->
		<div class="flex justify-between items-center mb-4">
			<div>
				<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
					{$i18n.t('Graph Spec JSON')}
				</h3>
				<p class="text-sm text-red-500 dark:text-red-400 mt-1">
					{renderError}
				</p>
			</div>
			<button
				class="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
				on:click={() => (showErrorJsonModal = false)}
			>
				<XMark className="size-5 text-gray-500" />
			</button>
		</div>

		<!-- JSON Content -->
		<div class="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
			<div class="flex justify-between items-center px-3 py-2 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
				<span class="text-xs text-gray-500 dark:text-gray-400">graph_spec.json</span>
				<button
					class="text-xs px-2 py-1 rounded bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 transition"
					on:click={() => {
						navigator.clipboard.writeText(JSON.stringify(spec, null, 2));
					}}
				>
					{$i18n.t('복사')}
				</button>
			</div>
			<pre class="p-4 text-xs font-mono bg-gray-50 dark:bg-gray-900 text-gray-800 dark:text-gray-200 max-h-96 overflow-auto">{JSON.stringify(spec, null, 2)}</pre>
		</div>
	</div>
</Modal>
