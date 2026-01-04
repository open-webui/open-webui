<script lang="ts">
	import { getContext, onMount, onDestroy } from 'svelte';
	import { compile } from 'mathjs';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import type { GraphSpec } from '$lib/utils/marked/graph-spec-extension';

	// Import shared graph builder utilities
	import {
		buildTraces,
		is3DGraph
	} from '$lib/utils/graph-builder';

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

	function getLayout() {
		// 그래프는 항상 라이트 모드로 표시
		const textColor = '#1f2937';
		const gridColor = 'rgba(0,0,0,0.1)';

		const baseLayout = {
			margin: { t: 40, r: 40, b: 60, l: 70 },
			showlegend: true,
			legend: { x: 1, xanchor: 'right', y: 1, font: { color: textColor } },
			paper_bgcolor: 'transparent',
			plot_bgcolor: 'transparent',
			font: { color: textColor }
		};

		if (is3DGraph(spec.type)) {
			// Build 3D axis configs with optional range
			const xaxis3d: any = { title: { text: spec.axis?.xLabel || 'X' }, showgrid: true, gridcolor: gridColor, tickfont: { color: textColor } };
			const yaxis3d: any = { title: { text: spec.axis?.yLabel || 'Y' }, showgrid: true, gridcolor: gridColor, tickfont: { color: textColor } };
			const zaxis3d: any = { title: { text: spec.axis?.zLabel || 'Z' }, showgrid: true, gridcolor: gridColor, tickfont: { color: textColor } };

			// Apply axis ranges if provided
			if (spec.axis?.xRange) {
				const xRange = spec.axis.xRange as any[];
				xaxis3d.range = [
					typeof xRange[0] === 'string' ? compile(xRange[0]).evaluate({}) : xRange[0],
					typeof xRange[1] === 'string' ? compile(xRange[1]).evaluate({}) : xRange[1]
				];
			}
			if (spec.axis?.yRange) {
				const yRange = spec.axis.yRange as any[];
				yaxis3d.range = [
					typeof yRange[0] === 'string' ? compile(yRange[0]).evaluate({}) : yRange[0],
					typeof yRange[1] === 'string' ? compile(yRange[1]).evaluate({}) : yRange[1]
				];
			}
			if (spec.axis?.zRange) {
				const zRange = spec.axis.zRange as any[];
				zaxis3d.range = [
					typeof zRange[0] === 'string' ? compile(zRange[0]).evaluate({}) : zRange[0],
					typeof zRange[1] === 'string' ? compile(zRange[1]).evaluate({}) : zRange[1]
				];
			}

			return {
				...baseLayout,
				scene: {
					xaxis: xaxis3d,
					yaxis: yaxis3d,
					zaxis: zaxis3d,
					bgcolor: 'transparent',
					camera: { eye: { x: 1.5, y: 1.5, z: 1.2 } }
				}
			};
		}

		// 2D layout with optional xRange/yRange
		const xaxis: any = {
			title: { text: spec.axis?.xLabel || 'x' },
			showgrid: true,
			gridcolor: gridColor,
			tickfont: { color: textColor }
		};
		const yaxis: any = {
			title: { text: spec.axis?.yLabel || 'y' },
			showgrid: true,
			gridcolor: gridColor,
			tickfont: { color: textColor }
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

		// Equal aspect ratio for phase_plane
		if (spec.type === 'phase_plane') {
			yaxis.scaleanchor = 'x';
			yaxis.scaleratio = 1;
		}

		// Build annotations if provided
		const annotations: any[] = [];
		if (spec.annotations && Array.isArray(spec.annotations)) {
			spec.annotations.forEach((ann: any) => {
				if (ann.type === 'label' && ann.position && ann.text) {
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
							size: ann.style?.fontSize || 12,
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
			xaxis,
			yaxis,
			annotations: annotations.length > 0 ? annotations : undefined
		};
	}

	async function initPlot() {
		if (!container || !show || plotInitialized) return;

		const plotlyModule = await import('plotly.js-dist-min');
		Plotly = plotlyModule.default;

		const data = buildTraces(spec);
		const layout = getLayout();

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
			<!-- Graph container - 항상 라이트 모드 배경 -->
			<div class="flex-1 {showJsonCode ? 'w-1/2' : 'w-full'}">
				<div class="h-[60vh] border border-gray-200 rounded-lg overflow-hidden bg-white">
					<div bind:this={container} class="w-full h-full" />
				</div>

				<!-- Meta data (title and caption) -->
				{#if spec.meta}
					<div class="mt-4 px-1">
						{#if spec.meta.title}
							<div class="font-semibold text-gray-900 dark:text-gray-100 mb-2">{spec.meta.title}</div>
						{/if}
						{#if spec.meta.caption}
							<div class="text-gray-600 dark:text-gray-400 text-sm leading-relaxed">{spec.meta.caption}</div>
						{/if}
					</div>
				{/if}
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
