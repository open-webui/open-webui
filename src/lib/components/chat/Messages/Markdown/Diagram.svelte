<script lang="ts">
	/**
	 * Diagram Renderer for diagram_spec
	 *
	 * Rendering Philosophy: "구조를 한눈에 이해하게 한다"
	 * - Balanced/hierarchical layout (NOT strict directional)
	 * - Subtle edges (relationship, not control flow)
	 * - Shapes for visual grouping/importance
	 * - Exploratory interaction focused
	 */
	import { onMount, getContext } from 'svelte';
	import DiagramPreviewModal from './DiagramPreviewModal.svelte';
	import ArrowsPointingOut from '$lib/components/icons/ArrowsPointingOut.svelte';

	const i18n = getContext('i18n');

	export let spec: any;

	let svgContainer: HTMLDivElement;
	let showModal = false;

	function isDarkMode(): boolean {
		return document.documentElement.classList.contains('dark');
	}

	// Node colors - for VISUAL GROUPING (not grammar)
	const getNodeColors = (shape: string, dark: boolean) => {
		// Softer, more balanced colors for structural diagrams
		const colors = {
			ellipse: {
				fill: dark ? '#312e81' : '#eef2ff',
				stroke: dark ? '#6366f1' : '#818cf8'
			},
			rectangle: {
				fill: dark ? '#1e3a5f' : '#f0f9ff',
				stroke: dark ? '#0ea5e9' : '#38bdf8'
			},
			rounded_rectangle: {
				fill: dark ? '#134e4a' : '#f0fdfa',
				stroke: dark ? '#14b8a6' : '#2dd4bf'
			},
			diamond: {
				fill: dark ? '#4c1d95' : '#faf5ff',
				stroke: dark ? '#a855f7' : '#c084fc'
			}
		};
		return colors[shape as keyof typeof colors] || colors.rectangle;
	};

	const renderNodeShape = (node: any, x: number, y: number, width: number, height: number, dark: boolean) => {
		const shape = node.shape || 'rectangle';
		const color = getNodeColors(shape, dark);

		switch (shape) {
			case 'ellipse':
				return `<ellipse cx="${x + width/2}" cy="${y + height/2}" rx="${width/2}" ry="${height/2}"
					fill="${color.fill}" stroke="${color.stroke}" stroke-width="1.5"/>`;
			case 'diamond':
				const cx = x + width/2;
				const cy = y + height/2;
				return `<polygon points="${cx},${y} ${x + width},${cy} ${cx},${y + height} ${x},${cy}"
					fill="${color.fill}" stroke="${color.stroke}" stroke-width="1.5"/>`;
			case 'rounded_rectangle':
				return `<rect x="${x}" y="${y}" width="${width}" height="${height}" rx="12" ry="12"
					fill="${color.fill}" stroke="${color.stroke}" stroke-width="1.5"/>`;
			case 'rectangle':
			default:
				return `<rect x="${x}" y="${y}" width="${width}" height="${height}" rx="3" ry="3"
					fill="${color.fill}" stroke="${color.stroke}" stroke-width="1.5"/>`;
		}
	};

	// Balanced hierarchical layout - emphasizes STRUCTURE not flow
	const calculateBalancedLayout = (nodes: any[], edges: any[]) => {
		const nodeWidth = 75;
		const nodeHeight = 32;
		const horizontalGap = 45;
		const verticalGap = 40;

		// Build graph
		const adjacency: Record<string, Set<string>> = {};
		const connections: Record<string, number> = {};

		nodes.forEach(n => {
			adjacency[n.id] = new Set();
			connections[n.id] = 0;
		});

		edges.forEach(e => {
			if (adjacency[e.from]) adjacency[e.from].add(e.to);
			if (adjacency[e.to]) adjacency[e.to].add(e.from); // Bidirectional for structure
			connections[e.from] = (connections[e.from] || 0) + 1;
			connections[e.to] = (connections[e.to] || 0) + 1;
		});

		// Sort by connection count (most connected = center)
		const sortedNodes = [...nodes].sort((a, b) =>
			(connections[b.id] || 0) - (connections[a.id] || 0)
		);

		// Place nodes in a balanced way (not strictly hierarchical)
		const positions: Record<string, { x: number; y: number }> = {};
		const placed = new Set<string>();

		// Center the most connected node
		if (sortedNodes.length > 0) {
			const center = sortedNodes[0];
			positions[center.id] = { x: 75, y: 75 };
			placed.add(center.id);
		}

		// Place connected nodes around
		let ring = 1;
		while (placed.size < nodes.length) {
			const toPlace = sortedNodes.filter(n => !placed.has(n.id));
			const nodesInRing = toPlace.slice(0, Math.max(4, ring * 3));

			nodesInRing.forEach((node, idx) => {
				const angle = (idx / nodesInRing.length) * 2 * Math.PI - Math.PI / 2;
				const radius = ring * (nodeWidth + horizontalGap);

				positions[node.id] = {
					x: 75 + Math.cos(angle) * radius,
					y: 75 + Math.sin(angle) * radius * 0.7 // Slight vertical compression
				};
				placed.add(node.id);
			});
			ring++;
		}

		// Normalize positions to start from 0
		let minX = Infinity, minY = Infinity;
		Object.values(positions).forEach((pos: any) => {
			minX = Math.min(minX, pos.x);
			minY = Math.min(minY, pos.y);
		});
		Object.values(positions).forEach((pos: any) => {
			pos.x -= minX - 15;
			pos.y -= minY - 15;
		});

		return { positions, nodeWidth, nodeHeight };
	};

	// Subtle arrow for relationships (not control flow)
	const getArrowMarker = (dark: boolean, id: string) => {
		const color = dark ? 'rgba(148, 163, 184, 0.6)' : 'rgba(100, 116, 139, 0.6)';
		return `<marker id="${id}" markerWidth="6" markerHeight="4" refX="5" refY="2" orient="auto">
			<polygon points="0 0, 6 2, 0 4" fill="${color}"/>
		</marker>`;
	};

	const calculateEdgePath = (from: { x: number; y: number }, to: { x: number; y: number },
		nodeWidth: number, nodeHeight: number) => {

		const fromCenterX = from.x + nodeWidth / 2;
		const fromCenterY = from.y + nodeHeight / 2;
		const toCenterX = to.x + nodeWidth / 2;
		const toCenterY = to.y + nodeHeight / 2;

		const dx = toCenterX - fromCenterX;
		const dy = toCenterY - fromCenterY;
		const dist = Math.sqrt(dx * dx + dy * dy);

		if (dist === 0) return '';

		// Simple straight line with slight curve for aesthetics
		const startX = fromCenterX + (dx / dist) * (nodeWidth / 2);
		const startY = fromCenterY + (dy / dist) * (nodeHeight / 2);
		const endX = toCenterX - (dx / dist) * (nodeWidth / 2);
		const endY = toCenterY - (dy / dist) * (nodeHeight / 2);

		// Subtle curve
		const midX = (startX + endX) / 2;
		const midY = (startY + endY) / 2;
		const perpX = -dy / dist * 10;
		const perpY = dx / dist * 10;

		return `M ${startX} ${startY} Q ${midX + perpX} ${midY + perpY}, ${endX} ${endY}`;
	};

	$: svgContent = (() => {
		if (!spec || !spec.nodes) return '';

		const dark = isDarkMode();
		const nodes = spec.nodes || [];
		const edges = spec.edges || [];

		const { positions, nodeWidth, nodeHeight } = calculateBalancedLayout(nodes, edges);

		let maxX = 0, maxY = 0;
		Object.values(positions).forEach((pos: any) => {
			maxX = Math.max(maxX, pos.x + nodeWidth);
			maxY = Math.max(maxY, pos.y + nodeHeight);
		});

		const svgWidth = Math.max(maxX + 20, 180);
		const svgHeight = Math.max(maxY + 20, 180);
		const textColor = dark ? '#e2e8f0' : '#334155';
		const edgeColor = dark ? 'rgba(148, 163, 184, 0.5)' : 'rgba(100, 116, 139, 0.5)';

		let svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${svgWidth} ${svgHeight}" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">`;
		svg += '<defs>' + getArrowMarker(dark, 'diagram-arrow-thumb') + '</defs>';

		// Render edges - SUBTLE, relationship-focused
		edges.forEach((edge: any) => {
			const fromPos = positions[edge.from];
			const toPos = positions[edge.to];

			if (fromPos && toPos) {
				const path = calculateEdgePath(fromPos, toPos, nodeWidth, nodeHeight);
				const strokeStyle = edge.style === 'dashed' ? 'stroke-dasharray: 6,4' : edge.style === 'dotted' ? 'stroke-dasharray: 2,2' : '';

				// Thinner, more subtle edges
				svg += `<path d="${path}" fill="none" stroke="${edgeColor}" stroke-width="1.5"
					marker-end="url(#diagram-arrow-thumb)" style="${strokeStyle}"/>`;
			}
		});

		// Render nodes
		nodes.forEach((node: any) => {
			const pos = positions[node.id];
			if (pos) {
				svg += renderNodeShape(node, pos.x, pos.y, nodeWidth, nodeHeight, dark);

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

<!-- Thumbnail: emphasizes structural overview -->
<div class="relative w-48 h-48 group mb-2 rounded-lg border border-gray-100 dark:border-gray-800 overflow-hidden bg-gradient-to-br from-gray-50 to-white dark:from-gray-900 dark:to-gray-800">
	<div class="w-48 h-48 flex items-center justify-center p-3">
		<div bind:this={svgContainer} class="w-full h-full">
			{@html svgContent}
		</div>
	</div>

	<!-- Softer gradient overlay -->
	<div class="absolute bottom-0 left-0 right-0 h-10 bg-gradient-to-t from-white dark:from-gray-900 to-transparent pointer-events-none" />

	<!-- Button -->
	<button
		class="absolute bottom-2 left-1/2 -translate-x-1/2 flex items-center gap-1 text-[11px] text-gray-600 dark:text-gray-400 bg-white/90 dark:bg-gray-800/90 px-2.5 py-1 rounded-full backdrop-blur-sm hover:bg-white dark:hover:bg-gray-700 transition z-10 shadow-sm"
		on:click={() => (showModal = true)}
	>
		<ArrowsPointingOut className="size-3" />
		<span>{$i18n.t('확대')}</span>
	</button>
</div>

<DiagramPreviewModal bind:show={showModal} {spec} />
