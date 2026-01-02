<script lang="ts">
	/**
	 * FlowChart Renderer for flow_spec
	 *
	 * Rendering Philosophy: "순서를 따라가게 한다"
	 * - Strict directional layout (TB/LR/BT/RL)
	 * - Strong directional arrows with conditions
	 * - Node shapes have GRAMMAR meaning:
	 *   - oval = start/end
	 *   - rectangle = process
	 *   - diamond = decision
	 * - Execution trace focused
	 */
	import { onMount, getContext } from 'svelte';
	import FlowChartPreviewModal from './FlowChartPreviewModal.svelte';
	import ArrowsPointingOut from '$lib/components/icons/ArrowsPointingOut.svelte';

	const i18n = getContext('i18n');

	export let spec: any;

	let svgContainer: HTMLDivElement;
	let showModal = false;

	function isDarkMode(): boolean {
		return document.documentElement.classList.contains('dark');
	}

	// Node shape renderers - GRAMMATICAL meaning for flowcharts
	const renderNodeShape = (node: any, x: number, y: number, width: number, height: number, dark: boolean) => {
		const shape = node.shape || 'rectangle';

		// Color coding by semantic role
		const colors = {
			oval: { fill: dark ? '#166534' : '#dcfce7', stroke: dark ? '#22c55e' : '#16a34a' }, // Start/End - Green
			rectangle: { fill: dark ? '#1e3a5f' : '#dbeafe', stroke: dark ? '#3b82f6' : '#2563eb' }, // Process - Blue
			diamond: { fill: dark ? '#713f12' : '#fef3c7', stroke: dark ? '#f59e0b' : '#d97706' } // Decision - Amber
		};

		const color = colors[shape as keyof typeof colors] || colors.rectangle;

		switch (shape) {
			case 'oval':
				// Start/End nodes - ellipse shape
				return `<ellipse cx="${x + width/2}" cy="${y + height/2}" rx="${width/2}" ry="${height/2}"
					fill="${color.fill}" stroke="${color.stroke}" stroke-width="2"/>`;
			case 'diamond':
				// Decision nodes - diamond shape
				const cx = x + width/2;
				const cy = y + height/2;
				const hw = width * 0.6; // Wider diamond for readability
				const hh = height * 0.5;
				return `<polygon points="${cx},${cy - hh} ${cx + hw},${cy} ${cx},${cy + hh} ${cx - hw},${cy}"
					fill="${color.fill}" stroke="${color.stroke}" stroke-width="2"/>`;
			case 'rectangle':
			default:
				// Process nodes - rounded rectangle
				return `<rect x="${x}" y="${y}" width="${width}" height="${height}" rx="4" ry="4"
					fill="${color.fill}" stroke="${color.stroke}" stroke-width="2"/>`;
		}
	};

	// Strict directional layout - enforces reading order
	const calculateDirectionalLayout = (nodes: any[], edges: any[], direction: string = 'TB') => {
		const nodeWidth = 80;
		const nodeHeight = 36;
		const horizontalGap = 50;
		const verticalGap = 50;

		// Build graph structure
		const adjacency: Record<string, string[]> = {};
		const inDegree: Record<string, number> = {};
		const nodeMap: Record<string, any> = {};

		nodes.forEach(n => {
			adjacency[n.id] = [];
			inDegree[n.id] = 0;
			nodeMap[n.id] = n;
		});

		edges.forEach(e => {
			if (adjacency[e.from]) {
				adjacency[e.from].push(e.to);
			}
			if (inDegree[e.to] !== undefined) {
				inDegree[e.to]++;
			}
		});

		// Find start node (in-degree 0, prefer 'oval' shape)
		let startNodes = Object.keys(inDegree).filter(k => inDegree[k] === 0);
		if (startNodes.length === 0) startNodes = [nodes[0]?.id].filter(Boolean);

		// Prioritize oval (start) nodes
		startNodes.sort((a, b) => {
			const aIsOval = nodeMap[a]?.shape === 'oval' ? -1 : 0;
			const bIsOval = nodeMap[b]?.shape === 'oval' ? -1 : 0;
			return aIsOval - bIsOval;
		});

		// BFS to assign levels
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
						if (!visited.has(child)) {
							nextQueue.push(child);
						}
					});
				}
			}

			if (levelNodes.length > 0) {
				levels.push(levelNodes);
			}
			queue = nextQueue;
		}

		// Add unvisited nodes
		nodes.forEach(n => {
			if (!visited.has(n.id)) {
				if (levels.length === 0) levels.push([]);
				levels[levels.length - 1].push(n.id);
			}
		});

		// Calculate positions with strict directional flow
		const positions: Record<string, { x: number; y: number }> = {};
		const isHorizontal = direction === 'LR' || direction === 'RL';
		const isReversed = direction === 'BT' || direction === 'RL';

		levels.forEach((level, levelIdx) => {
			const actualLevelIdx = isReversed ? levels.length - 1 - levelIdx : levelIdx;

			level.forEach((nodeId, nodeIdx) => {
				const centerOffset = (level.length - 1) * (isHorizontal ? (nodeHeight + verticalGap/2) : (nodeWidth + horizontalGap/2)) / 2;

				if (isHorizontal) {
					positions[nodeId] = {
						x: actualLevelIdx * (nodeWidth + horizontalGap) + 20,
						y: nodeIdx * (nodeHeight + verticalGap/2) - centerOffset + 80
					};
				} else {
					positions[nodeId] = {
						x: nodeIdx * (nodeWidth + horizontalGap/2) - centerOffset + 80,
						y: actualLevelIdx * (nodeHeight + verticalGap) + 20
					};
				}
			});
		});

		return { positions, nodeWidth, nodeHeight };
	};

	// Strong directional arrow marker
	const getArrowMarker = (dark: boolean, id: string = 'flow-arrow') => {
		const color = dark ? '#94a3b8' : '#475569';
		return `<marker id="${id}" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
			<polygon points="0 0, 8 3, 0 6" fill="${color}"/>
		</marker>`;
	};

	// Calculate edge path with control flow semantics
	const calculateEdgePath = (from: { x: number; y: number }, to: { x: number; y: number },
		nodeWidth: number, nodeHeight: number, fromShape: string, toShape: string) => {

		const fromCenterX = from.x + nodeWidth / 2;
		const fromCenterY = from.y + nodeHeight / 2;
		const toCenterX = to.x + nodeWidth / 2;
		const toCenterY = to.y + nodeHeight / 2;

		const dx = toCenterX - fromCenterX;
		const dy = toCenterY - fromCenterY;

		let startX, startY, endX, endY;

		// Diamond nodes have different connection points
		if (fromShape === 'diamond') {
			// Exit from diamond sides based on direction
			if (Math.abs(dx) > Math.abs(dy)) {
				startX = dx > 0 ? from.x + nodeWidth * 0.8 : from.x + nodeWidth * 0.2;
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

		// Entry points
		if (Math.abs(dx) > Math.abs(dy)) {
			endX = dx > 0 ? to.x : to.x + nodeWidth;
			endY = toCenterY;
		} else {
			endX = toCenterX;
			endY = dy > 0 ? to.y : to.y + nodeHeight;
		}

		// Create smooth bezier curve
		const midX = (startX + endX) / 2;
		const midY = (startY + endY) / 2;

		if (Math.abs(dx) > Math.abs(dy)) {
			return `M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}`;
		} else {
			return `M ${startX} ${startY} C ${startX} ${midY}, ${endX} ${midY}, ${endX} ${endY}`;
		}
	};

	// Render SVG - execution flow focused
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

		const svgWidth = Math.max(maxX + 20, 180);
		const svgHeight = Math.max(maxY + 20, 180);
		const textColor = dark ? '#f1f5f9' : '#1e293b';
		const edgeColor = dark ? '#94a3b8' : '#475569';

		let svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${svgWidth} ${svgHeight}" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">`;
		svg += '<defs>' + getArrowMarker(dark, 'flow-arrow-thumb') + '</defs>';

		// Render edges with STRONG directional arrows
		edges.forEach((edge: any) => {
			const fromPos = positions[edge.from];
			const toPos = positions[edge.to];
			const fromNode = nodes.find((n: any) => n.id === edge.from);
			const toNode = nodes.find((n: any) => n.id === edge.to);

			if (fromPos && toPos) {
				const path = calculateEdgePath(fromPos, toPos, nodeWidth, nodeHeight,
					fromNode?.shape || 'rectangle', toNode?.shape || 'rectangle');

				// Strong, prominent arrows for control flow
				svg += `<path d="${path}" fill="none" stroke="${edgeColor}" stroke-width="2"
					marker-end="url(#flow-arrow-thumb)"/>`;
			}
		});

		// Render nodes with grammatical shapes
		nodes.forEach((node: any) => {
			const pos = positions[node.id];
			if (pos) {
				svg += renderNodeShape(node, pos.x, pos.y, nodeWidth, nodeHeight, dark);

				// Node label (truncated)
				const label = node.label || node.id;
				const displayLabel = label.length > 8 ? label.slice(0, 6) + '..' : label;

				svg += `<text x="${pos.x + nodeWidth/2}" y="${pos.y + nodeHeight/2 + 4}"
					text-anchor="middle" fill="${textColor}" font-size="9" font-weight="500"
					font-family="system-ui">${displayLabel}</text>`;
			}
		});

		svg += '</svg>';
		return svg;
	})();
</script>

<!-- Thumbnail: emphasizes sequential flow -->
<div class="relative w-48 h-48 group mb-2 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden bg-white dark:bg-gray-900">
	<div class="w-48 h-48 flex items-center justify-center p-2">
		<div bind:this={svgContainer} class="w-full h-full">
			{@html svgContent}
		</div>
	</div>

	<!-- Gradient overlay -->
	<div class="absolute bottom-0 left-0 right-0 h-12 bg-gradient-to-t from-white dark:from-gray-900 to-transparent pointer-events-none" />

	<!-- Button with flow icon -->
	<button
		class="absolute bottom-2 left-1/2 -translate-x-1/2 flex items-center gap-1 text-[11px] text-gray-700 dark:text-gray-300 bg-white/90 dark:bg-gray-800/90 px-2.5 py-1 rounded-full backdrop-blur-sm hover:bg-white dark:hover:bg-gray-700 transition z-10 shadow-sm"
		on:click={() => (showModal = true)}
	>
		<ArrowsPointingOut className="size-3" />
		<span>{$i18n.t('확대')}</span>
	</button>
</div>

<FlowChartPreviewModal bind:show={showModal} {spec} />
