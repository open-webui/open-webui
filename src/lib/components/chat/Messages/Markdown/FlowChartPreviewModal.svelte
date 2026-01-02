<script lang="ts">
	/**
	 * FlowChart Preview Modal
	 *
	 * Full view for flow_spec with:
	 * - Strict directional layout
	 * - Strong arrows with condition labels
	 * - Zoom in/out with fixed text size
	 * - Pan navigation
	 * - JSON code toggle
	 */
	import { getContext } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');

	export let show = false;
	export let spec: any;

	let showJsonCode = false;
	let jsonCopied = false;
	let hoveredEdge: string | null = null;

	// Zoom and pan state
	let zoom = 1;
	let panX = 0;
	let panY = 0;
	let isPanning = false;
	let startPanX = 0;
	let startPanY = 0;
	let svgContainer: HTMLDivElement;

	const MIN_ZOOM = 0.5;
	const MAX_ZOOM = 3;
	const ZOOM_STEP = 0.25;

	// Zoom controls
	const zoomIn = () => {
		zoom = Math.min(MAX_ZOOM, zoom + ZOOM_STEP);
	};

	const zoomOut = () => {
		zoom = Math.max(MIN_ZOOM, zoom - ZOOM_STEP);
	};

	const resetZoom = () => {
		zoom = 1;
		panX = 0;
		panY = 0;
	};

	// Mouse wheel zoom
	const handleWheel = (e: WheelEvent) => {
		e.preventDefault();
		const delta = e.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP;
		zoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoom + delta));
	};

	// Pan handlers
	const handleMouseDown = (e: MouseEvent) => {
		if (e.button === 0) {
			isPanning = true;
			startPanX = e.clientX - panX;
			startPanY = e.clientY - panY;
		}
	};

	const handleMouseMove = (e: MouseEvent) => {
		if (isPanning) {
			panX = e.clientX - startPanX;
			panY = e.clientY - startPanY;
		}
	};

	const handleMouseUp = () => {
		isPanning = false;
	};

	// Reset on modal close
	$: if (!show) {
		zoom = 1;
		panX = 0;
		panY = 0;
	}

	const copyJsonToClipboard = async () => {
		try {
			await navigator.clipboard.writeText(JSON.stringify(spec, null, 2));
			jsonCopied = true;
			setTimeout(() => { jsonCopied = false; }, 2000);
		} catch (err) {
			console.error('Failed to copy:', err);
		}
	};

	function isDarkMode(): boolean {
		return document.documentElement.classList.contains('dark');
	}

	// Node colors with grammatical meaning
	const getNodeColors = (shape: string, dark: boolean) => {
		const colors = {
			oval: {
				fill: dark ? '#166534' : '#dcfce7',
				stroke: dark ? '#22c55e' : '#16a34a',
				text: dark ? '#bbf7d0' : '#14532d'
			},
			rectangle: {
				fill: dark ? '#1e3a5f' : '#dbeafe',
				stroke: dark ? '#3b82f6' : '#2563eb',
				text: dark ? '#bfdbfe' : '#1e3a8a'
			},
			diamond: {
				fill: dark ? '#713f12' : '#fef3c7',
				stroke: dark ? '#f59e0b' : '#d97706',
				text: dark ? '#fde68a' : '#78350f'
			}
		};
		return colors[shape as keyof typeof colors] || colors.rectangle;
	};

	const renderNodeShape = (node: any, x: number, y: number, width: number, height: number, dark: boolean) => {
		const shape = node.shape || 'rectangle';
		const color = getNodeColors(shape, dark);

		switch (shape) {
			case 'oval':
				return `<ellipse cx="${x + width/2}" cy="${y + height/2}" rx="${width/2}" ry="${height/2}"
					fill="${color.fill}" stroke="${color.stroke}" stroke-width="2.5"/>`;
			case 'diamond':
				const cx = x + width/2;
				const cy = y + height/2;
				const hw = width * 0.55;
				const hh = height * 0.5;
				return `<polygon points="${cx},${cy - hh} ${cx + hw},${cy} ${cx},${cy + hh} ${cx - hw},${cy}"
					fill="${color.fill}" stroke="${color.stroke}" stroke-width="2.5"/>`;
			case 'rectangle':
			default:
				return `<rect x="${x}" y="${y}" width="${width}" height="${height}" rx="6" ry="6"
					fill="${color.fill}" stroke="${color.stroke}" stroke-width="2.5"/>`;
		}
	};

	// Strict directional layout with more space for labels
	const calculateDirectionalLayout = (nodes: any[], edges: any[], direction: string = 'TB') => {
		const nodeWidth = 120;
		const nodeHeight = 48;
		const horizontalGap = 130;
		const verticalGap = 110;

		const adjacency: Record<string, string[]> = {};
		const inDegree: Record<string, number> = {};
		const nodeMap: Record<string, any> = {};

		nodes.forEach(n => {
			adjacency[n.id] = [];
			inDegree[n.id] = 0;
			nodeMap[n.id] = n;
		});

		edges.forEach(e => {
			if (adjacency[e.from]) adjacency[e.from].push(e.to);
			if (inDegree[e.to] !== undefined) inDegree[e.to]++;
		});

		let startNodes = Object.keys(inDegree).filter(k => inDegree[k] === 0);
		if (startNodes.length === 0) startNodes = [nodes[0]?.id].filter(Boolean);

		startNodes.sort((a, b) => {
			const aIsOval = nodeMap[a]?.shape === 'oval' ? -1 : 0;
			const bIsOval = nodeMap[b]?.shape === 'oval' ? -1 : 0;
			return aIsOval - bIsOval;
		});

		const levels: string[][] = [];
		const visited = new Set<string>();
		let queue = [...startNodes];

		while (queue.length > 0) {
			const levelNodes: string[] = [];
			const nextQueue: string[] = [];

			for (const nodeId of queue) {
				if (!visited.has(nodeId)) {
					visited.add(nodeId);
					levelNodes.push(nodeId);
					adjacency[nodeId]?.forEach(child => {
						if (!visited.has(child)) nextQueue.push(child);
					});
				}
			}

			if (levelNodes.length > 0) levels.push(levelNodes);
			queue = nextQueue;
		}

		nodes.forEach(n => {
			if (!visited.has(n.id)) {
				if (levels.length === 0) levels.push([]);
				levels[levels.length - 1].push(n.id);
			}
		});

		const positions: Record<string, { x: number; y: number }> = {};
		const isHorizontal = direction === 'LR' || direction === 'RL';
		const isReversed = direction === 'BT' || direction === 'RL';

		levels.forEach((level, levelIdx) => {
			const actualLevelIdx = isReversed ? levels.length - 1 - levelIdx : levelIdx;

			level.forEach((nodeId, nodeIdx) => {
				const centerOffset = (level.length - 1) * (isHorizontal ? (nodeHeight + verticalGap/2) : (nodeWidth + horizontalGap/2)) / 2;

				if (isHorizontal) {
					positions[nodeId] = {
						x: actualLevelIdx * (nodeWidth + horizontalGap) + 60,
						y: nodeIdx * (nodeHeight + verticalGap/2) - centerOffset + 180
					};
				} else {
					positions[nodeId] = {
						x: nodeIdx * (nodeWidth + horizontalGap/2) - centerOffset + 250,
						y: actualLevelIdx * (nodeHeight + verticalGap) + 60
					};
				}
			});
		});

		return { positions, nodeWidth, nodeHeight };
	};

	const getArrowMarker = (dark: boolean, id: string) => {
		const color = dark ? '#94a3b8' : '#475569';
		return `<marker id="${id}" markerWidth="12" markerHeight="8" refX="10" refY="4" orient="auto">
			<polygon points="0 0, 12 4, 0 8" fill="${color}"/>
		</marker>`;
	};

	const calculateEdgePath = (from: { x: number; y: number }, to: { x: number; y: number },
		nodeWidth: number, nodeHeight: number, fromShape: string) => {

		const fromCenterX = from.x + nodeWidth / 2;
		const fromCenterY = from.y + nodeHeight / 2;
		const toCenterX = to.x + nodeWidth / 2;
		const toCenterY = to.y + nodeHeight / 2;

		const dx = toCenterX - fromCenterX;
		const dy = toCenterY - fromCenterY;

		let startX, startY, endX, endY;

		if (fromShape === 'diamond') {
			if (Math.abs(dx) > Math.abs(dy)) {
				startX = dx > 0 ? from.x + nodeWidth * 0.77 : from.x + nodeWidth * 0.23;
				startY = fromCenterY;
			} else {
				startX = fromCenterX;
				startY = dy > 0 ? from.y + nodeHeight : from.y;
			}
		} else {
			if (Math.abs(dx) > Math.abs(dy)) {
				startX = dx > 0 ? from.x + nodeWidth : from.x;
				startY = fromCenterY;
			} else {
				startX = fromCenterX;
				startY = dy > 0 ? from.y + nodeHeight : from.y;
			}
		}

		if (Math.abs(dx) > Math.abs(dy)) {
			endX = dx > 0 ? to.x : to.x + nodeWidth;
			endY = toCenterY;
		} else {
			endX = toCenterX;
			endY = dy > 0 ? to.y : to.y + nodeHeight;
		}

		const midX = (startX + endX) / 2;
		const midY = (startY + endY) / 2;

		if (Math.abs(dx) > Math.abs(dy)) {
			return { path: `M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}`, midX, midY };
		} else {
			return { path: `M ${startX} ${startY} C ${startX} ${midY}, ${endX} ${midY}, ${endX} ${endY}`, midX, midY };
		}
	};

	// Generate SVG with zoom-aware text sizing
	$: svgContent = (() => {
		if (!spec || !spec.nodes) return '';

		const dark = isDarkMode();
		const nodes = spec.nodes || [];
		const edges = spec.edges || [];
		const direction = spec.layout?.direction || 'TB';

		const { positions, nodeWidth, nodeHeight } = calculateDirectionalLayout(nodes, edges, direction);

		let maxX = 0, maxY = 0;
		Object.values(positions).forEach((pos: any) => {
			maxX = Math.max(maxX, pos.x + nodeWidth);
			maxY = Math.max(maxY, pos.y + nodeHeight);
		});

		const svgWidth = Math.max(maxX + 60, 500);
		const svgHeight = Math.max(maxY + 60, 400);
		const edgeColor = dark ? '#94a3b8' : '#475569';
		const labelBg = dark ? '#1e293b' : '#ffffff';

		// Base font sizes
		const baseLabelFontSize = 13;
		const baseEdgeFontSize = 12;

		// Calculate inverse scale for text to maintain readable size
		const textScale = 1 / zoom;
		const labelFontSize = baseLabelFontSize * textScale;
		const edgeFontSize = baseEdgeFontSize * textScale;

		let svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${svgWidth} ${svgHeight}" width="100%" height="100%">`;
		svg += '<defs>' + getArrowMarker(dark, 'flow-arrow-full') + '</defs>';

		// Render edges with condition labels
		edges.forEach((edge: any, idx: number) => {
			const fromPos = positions[edge.from];
			const toPos = positions[edge.to];
			const fromNode = nodes.find((n: any) => n.id === edge.from);

			if (fromPos && toPos) {
				const { path, midX, midY } = calculateEdgePath(fromPos, toPos, nodeWidth, nodeHeight, fromNode?.shape || 'rectangle');

				// Strong arrow with zoom-adjusted stroke
				svg += `<path d="${path}" fill="none" stroke="${edgeColor}" stroke-width="${2.5 / zoom}"
					marker-end="url(#flow-arrow-full)"/>`;

				// Condition/label on edge (IMPORTANT for flow understanding)
				if (edge.label || edge.condition) {
					const labelText = edge.label || edge.condition;
					const labelWidth = Math.max(labelText.length * 7, 40) * textScale;
					const labelHeight = 24 * textScale;

					svg += `<rect x="${midX - labelWidth/2}" y="${midY - labelHeight/2}" width="${labelWidth}" height="${labelHeight}"
						fill="${labelBg}" stroke="${edgeColor}" stroke-width="${1 / zoom}" rx="${4 * textScale}"/>`;
					svg += `<text x="${midX}" y="${midY + edgeFontSize * 0.35}" text-anchor="middle"
						fill="${edgeColor}" font-size="${edgeFontSize}" font-weight="600" font-family="system-ui">${labelText}</text>`;
				}
			}
		});

		// Render nodes
		nodes.forEach((node: any) => {
			const pos = positions[node.id];
			if (pos) {
				const shape = node.shape || 'rectangle';
				const color = getNodeColors(shape, dark);

				svg += renderNodeShape(node, pos.x, pos.y, nodeWidth, nodeHeight, dark);

				// Node label with zoom-aware sizing
				const label = node.label || node.id;
				const lines = label.split('\\n');
				const lineHeight = 18 * textScale;
				const centerX = pos.x + nodeWidth/2;
				const centerY = pos.y + nodeHeight/2;
				const startY = centerY - (lines.length - 1) * lineHeight / 2;

				// Zoom에 따라 표시 가능한 글자 수 조절
				const baseMaxChars = 12;
				const maxChars = Math.floor(baseMaxChars * zoom);

				lines.forEach((line: string, idx: number) => {
					const displayLine = line.length > maxChars + 2 ? line.slice(0, maxChars) + '..' : line;
					svg += `<text x="${centerX}" y="${startY + idx * lineHeight}"
						text-anchor="middle" dominant-baseline="middle"
						fill="${color.text}" font-size="${labelFontSize}" font-weight="600" font-family="system-ui">${displayLine}</text>`;
				});
			}
		});

		svg += '</svg>';
		return svg;
	})();
</script>

<Modal bind:show size="xl" className="bg-white dark:bg-gray-900 rounded-2xl">
	<div class="p-5">
		<!-- Header -->
		<div class="flex justify-between items-center mb-4">
			<div class="flex items-center gap-3">
				<h3 class="text-title-4 text-gray-900 dark:text-white">
					{$i18n.t('Flow Chart')}
				</h3>
				<!-- Legend -->
				<div class="flex items-center gap-4 text-xs">
					<div class="flex items-center gap-1.5">
						<div class="w-4 h-3 rounded-full bg-green-100 dark:bg-green-900 border border-green-500"></div>
						<span class="text-gray-500 dark:text-gray-400">Start/End</span>
					</div>
					<div class="flex items-center gap-1.5">
						<div class="w-4 h-3 rounded bg-blue-100 dark:bg-blue-900 border border-blue-500"></div>
						<span class="text-gray-500 dark:text-gray-400">Process</span>
					</div>
					<div class="flex items-center gap-1.5">
						<div class="w-3 h-3 rotate-45 bg-amber-100 dark:bg-amber-900 border border-amber-500"></div>
						<span class="text-gray-500 dark:text-gray-400">Decision</span>
					</div>
				</div>
			</div>
			<div class="flex items-center gap-2">
				<!-- Zoom controls -->
				<div class="flex items-center gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
					<button
						class="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition disabled:opacity-40"
						on:click={zoomOut}
						disabled={zoom <= MIN_ZOOM}
						title="Zoom Out"
					>
						<svg class="size-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4" />
						</svg>
					</button>
					<button
						class="px-2 py-1 text-xs font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition min-w-[48px]"
						on:click={resetZoom}
						title="Reset Zoom"
					>
						{Math.round(zoom * 100)}%
					</button>
					<button
						class="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition disabled:opacity-40"
						on:click={zoomIn}
						disabled={zoom >= MAX_ZOOM}
						title="Zoom In"
					>
						<svg class="size-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
						</svg>
					</button>
				</div>

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
				<button class="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition" on:click={() => (show = false)}>
					<XMark className="size-4" />
				</button>
			</div>
		</div>

		<!-- Content -->
		<div class="flex gap-4 {showJsonCode ? 'flex-row' : 'flex-col'}">
			<!-- svelte-ignore a11y-no-static-element-interactions -->
			<div
				class="flex-1 {showJsonCode ? 'w-1/2' : 'w-full'} h-[60vh] border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden bg-gray-50 dark:bg-gray-800/50 relative"
				bind:this={svgContainer}
				on:wheel={handleWheel}
				on:mousedown={handleMouseDown}
				on:mousemove={handleMouseMove}
				on:mouseup={handleMouseUp}
				on:mouseleave={handleMouseUp}
				style="cursor: {isPanning ? 'grabbing' : 'grab'};"
			>
				<div
					class="w-full h-full flex items-center justify-center p-6 origin-center"
					style="transform: scale({zoom}) translate({panX / zoom}px, {panY / zoom}px);"
				>
					{@html svgContent}
				</div>
				<!-- Zoom hint -->
				<div class="absolute bottom-2 left-2 text-[10px] text-gray-400 dark:text-gray-500 pointer-events-none">
					Scroll to zoom · Drag to pan
				</div>
			</div>

			{#if showJsonCode}
				<div class="flex-1 w-1/2 h-[60vh] flex flex-col border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
					<div class="flex justify-between items-center px-4 py-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
						<span class="text-caption text-gray-600 dark:text-gray-400">flow_spec.json</span>
						<button
							class="flex items-center gap-1.5 px-2 py-1 text-caption rounded transition
								{jsonCopied ? 'text-green-600 dark:text-green-400' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}"
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
					<pre class="flex-1 overflow-auto p-4 text-xs font-mono bg-gray-50 dark:bg-gray-900 text-gray-800 dark:text-gray-200">{JSON.stringify(spec, null, 2)}</pre>
				</div>
			{/if}
		</div>
	</div>
</Modal>
