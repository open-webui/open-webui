<script lang="ts">
	/**
	 * Diagram Preview Modal
	 *
	 * Full view for diagram_spec with:
	 * - Balanced structural layout
	 * - Subtle relationship edges
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
	let hoveredNode: string | null = null;

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
		if (e.button === 0) { // Left click
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

	// Softer color palette for structural diagrams
	const getNodeColors = (shape: string, dark: boolean, hovered: boolean = false) => {
		const colors = {
			ellipse: {
				fill: dark ? (hovered ? '#3730a3' : '#312e81') : (hovered ? '#e0e7ff' : '#eef2ff'),
				stroke: dark ? '#818cf8' : '#6366f1',
				text: dark ? '#c7d2fe' : '#3730a3'
			},
			rectangle: {
				fill: dark ? (hovered ? '#0c4a6e' : '#1e3a5f') : (hovered ? '#e0f2fe' : '#f0f9ff'),
				stroke: dark ? '#38bdf8' : '#0ea5e9',
				text: dark ? '#bae6fd' : '#0c4a6e'
			},
			rounded_rectangle: {
				fill: dark ? (hovered ? '#115e59' : '#134e4a') : (hovered ? '#ccfbf1' : '#f0fdfa'),
				stroke: dark ? '#2dd4bf' : '#14b8a6',
				text: dark ? '#99f6e4' : '#115e59'
			},
			diamond: {
				fill: dark ? (hovered ? '#5b21b6' : '#4c1d95') : (hovered ? '#f3e8ff' : '#faf5ff'),
				stroke: dark ? '#c084fc' : '#a855f7',
				text: dark ? '#e9d5ff' : '#5b21b6'
			}
		};
		return colors[shape as keyof typeof colors] || colors.rectangle;
	};

	const renderNodeShape = (node: any, x: number, y: number, width: number, height: number, dark: boolean, hovered: boolean) => {
		const shape = node.shape || 'rectangle';
		const color = getNodeColors(shape, dark, hovered);
		const strokeWidth = hovered ? 2.5 : 2;

		switch (shape) {
			case 'ellipse':
				return `<ellipse cx="${x + width/2}" cy="${y + height/2}" rx="${width/2}" ry="${height/2}"
					fill="${color.fill}" stroke="${color.stroke}" stroke-width="${strokeWidth}" class="transition-all duration-200"/>`;
			case 'diamond':
				const cx = x + width/2;
				const cy = y + height/2;
				return `<polygon points="${cx},${y} ${x + width},${cy} ${cx},${y + height} ${x},${cy}"
					fill="${color.fill}" stroke="${color.stroke}" stroke-width="${strokeWidth}" class="transition-all duration-200"/>`;
			case 'rounded_rectangle':
				return `<rect x="${x}" y="${y}" width="${width}" height="${height}" rx="14" ry="14"
					fill="${color.fill}" stroke="${color.stroke}" stroke-width="${strokeWidth}" class="transition-all duration-200"/>`;
			case 'rectangle':
			default:
				return `<rect x="${x}" y="${y}" width="${width}" height="${height}" rx="4" ry="4"
					fill="${color.fill}" stroke="${color.stroke}" stroke-width="${strokeWidth}" class="transition-all duration-200"/>`;
		}
	};

	// Force-directed inspired balanced layout
	const calculateBalancedLayout = (nodes: any[], edges: any[]) => {
		const nodeWidth = 110;
		const nodeHeight = 42;
		const horizontalGap = 120;
		const verticalGap = 100;

		const adjacency: Record<string, Set<string>> = {};
		const connections: Record<string, number> = {};

		nodes.forEach(n => {
			adjacency[n.id] = new Set();
			connections[n.id] = 0;
		});

		edges.forEach(e => {
			if (adjacency[e.from]) adjacency[e.from].add(e.to);
			if (adjacency[e.to]) adjacency[e.to].add(e.from);
			connections[e.from] = (connections[e.from] || 0) + 1;
			connections[e.to] = (connections[e.to] || 0) + 1;
		});

		const sortedNodes = [...nodes].sort((a, b) =>
			(connections[b.id] || 0) - (connections[a.id] || 0)
		);

		const positions: Record<string, { x: number; y: number }> = {};
		const placed = new Set<string>();

		// Center position
		const centerX = 300;
		const centerY = 200;

		if (sortedNodes.length > 0) {
			positions[sortedNodes[0].id] = { x: centerX - nodeWidth/2, y: centerY - nodeHeight/2 };
			placed.add(sortedNodes[0].id);
		}

		// Place in expanding rings
		let ring = 1;
		while (placed.size < nodes.length) {
			const toPlace = sortedNodes.filter(n => !placed.has(n.id));
			const nodesInRing = toPlace.slice(0, Math.max(5, ring * 4));

			nodesInRing.forEach((node, idx) => {
				const angle = (idx / nodesInRing.length) * 2 * Math.PI - Math.PI / 2;
				const radius = ring * (nodeWidth * 0.7 + horizontalGap);

				positions[node.id] = {
					x: centerX + Math.cos(angle) * radius - nodeWidth/2,
					y: centerY + Math.sin(angle) * radius * 0.8 - nodeHeight/2
				};
				placed.add(node.id);
			});
			ring++;
		}

		// Normalize
		let minX = Infinity, minY = Infinity;
		Object.values(positions).forEach((pos: any) => {
			minX = Math.min(minX, pos.x);
			minY = Math.min(minY, pos.y);
		});
		Object.values(positions).forEach((pos: any) => {
			pos.x -= minX - 60;
			pos.y -= minY - 60;
		});

		return { positions, nodeWidth, nodeHeight };
	};

	const getArrowMarker = (dark: boolean, id: string) => {
		const color = dark ? 'rgba(148, 163, 184, 0.7)' : 'rgba(100, 116, 139, 0.7)';
		return `<marker id="${id}" markerWidth="8" markerHeight="5" refX="7" refY="2.5" orient="auto">
			<polygon points="0 0, 8 2.5, 0 5" fill="${color}"/>
		</marker>`;
	};

	const calculateEdgePath = (from: { x: number; y: number }, to: { x: number; y: number },
		nodeWidth: number, nodeHeight: number, isHighlighted: boolean) => {

		const fromCenterX = from.x + nodeWidth / 2;
		const fromCenterY = from.y + nodeHeight / 2;
		const toCenterX = to.x + nodeWidth / 2;
		const toCenterY = to.y + nodeHeight / 2;

		const dx = toCenterX - fromCenterX;
		const dy = toCenterY - fromCenterY;
		const dist = Math.sqrt(dx * dx + dy * dy);

		if (dist === 0) return { path: '', midX: 0, midY: 0 };

		const startX = fromCenterX + (dx / dist) * (nodeWidth / 2.2);
		const startY = fromCenterY + (dy / dist) * (nodeHeight / 2.2);
		const endX = toCenterX - (dx / dist) * (nodeWidth / 2.2);
		const endY = toCenterY - (dy / dist) * (nodeHeight / 2.2);

		// Subtle curve
		const midX = (startX + endX) / 2;
		const midY = (startY + endY) / 2;
		const curveFactor = isHighlighted ? 15 : 8;
		const perpX = -dy / dist * curveFactor;
		const perpY = dx / dist * curveFactor;

		return {
			path: `M ${startX} ${startY} Q ${midX + perpX} ${midY + perpY}, ${endX} ${endY}`,
			midX: midX + perpX/2,
			midY: midY + perpY/2
		};
	};

	// Generate SVG with zoom-aware text sizing
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

		const svgWidth = Math.max(maxX + 80, 500);
		const svgHeight = Math.max(maxY + 80, 400);
		const edgeColor = dark ? 'rgba(148, 163, 184, 0.5)' : 'rgba(100, 116, 139, 0.5)';
		const labelBg = dark ? 'rgba(30, 41, 59, 0.9)' : 'rgba(255, 255, 255, 0.9)';

		// Base font sizes
		const baseLabelFontSize = 13;
		const baseEdgeFontSize = 11;

		// Calculate inverse scale for text to maintain readable size
		const textScale = 1 / zoom;
		const labelFontSize = baseLabelFontSize * textScale;
		const edgeFontSize = baseEdgeFontSize * textScale;

		let svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${svgWidth} ${svgHeight}" width="100%" height="100%">`;
		svg += '<defs>' + getArrowMarker(dark, 'diagram-arrow-full') + '</defs>';

		// Render edges - subtle relationship lines
		edges.forEach((edge: any) => {
			const fromPos = positions[edge.from];
			const toPos = positions[edge.to];

			if (fromPos && toPos) {
				const { path, midX, midY } = calculateEdgePath(fromPos, toPos, nodeWidth, nodeHeight, false);
				const strokeStyle = edge.style === 'dashed' ? 'stroke-dasharray: 8,5' : edge.style === 'dotted' ? 'stroke-dasharray: 3,3' : '';

				svg += `<path d="${path}" fill="none" stroke="${edgeColor}" stroke-width="${1.5 / zoom}"
					marker-end="url(#diagram-arrow-full)" style="${strokeStyle}"/>`;

				// Edge label (optional, for relationships)
				if (edge.label) {
					const labelWidth = Math.max(edge.label.length * 6.5, 30) * textScale;
					const labelHeight = 20 * textScale;
					svg += `<rect x="${midX - labelWidth/2}" y="${midY - labelHeight/2}" width="${labelWidth}" height="${labelHeight}"
						fill="${labelBg}" rx="${4 * textScale}" stroke="${edgeColor}" stroke-width="${0.5 / zoom}"/>`;
					svg += `<text x="${midX}" y="${midY + edgeFontSize * 0.35}" text-anchor="middle"
						fill="${dark ? '#94a3b8' : '#64748b'}" font-size="${edgeFontSize}" font-family="system-ui">${edge.label}</text>`;
				}
			}
		});

		// Render nodes
		nodes.forEach((node: any) => {
			const pos = positions[node.id];
			if (pos) {
				const shape = node.shape || 'rectangle';
				const color = getNodeColors(shape, dark, false);

				svg += renderNodeShape(node, pos.x, pos.y, nodeWidth, nodeHeight, dark, false);

				// Node label with inverse zoom scaling
				const label = node.label || node.id;
				const lines = label.split('\\n');
				const lineHeight = 18 * textScale;
				const centerX = pos.x + nodeWidth/2;
				const centerY = pos.y + nodeHeight/2;
				const startY = centerY - (lines.length - 1) * lineHeight / 2;

				// Zoom에 따라 표시 가능한 글자 수 조절 (블럭이 확대되면 더 많은 글자 표시)
				const baseMaxChars = 14;
				const maxChars = Math.floor(baseMaxChars * zoom);

				lines.forEach((line: string, idx: number) => {
					const displayLine = line.length > maxChars + 2 ? line.slice(0, maxChars) + '..' : line;
					svg += `<text x="${centerX}" y="${startY + idx * lineHeight}"
						text-anchor="middle" dominant-baseline="middle"
						fill="${color.text}" font-size="${labelFontSize}" font-weight="500" font-family="system-ui">${displayLine}</text>`;
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
					{$i18n.t('Diagram')}
				</h3>
				<!-- Shape legend for visual understanding -->
				<div class="flex items-center gap-4 text-xs">
					<div class="flex items-center gap-1.5">
						<div class="w-4 h-3 rounded-full bg-indigo-100 dark:bg-indigo-900 border border-indigo-400"></div>
						<span class="text-gray-500 dark:text-gray-400">Ellipse</span>
					</div>
					<div class="flex items-center gap-1.5">
						<div class="w-4 h-3 rounded bg-sky-100 dark:bg-sky-900 border border-sky-400"></div>
						<span class="text-gray-500 dark:text-gray-400">Rectangle</span>
					</div>
					<div class="flex items-center gap-1.5">
						<div class="w-4 h-3 rounded-lg bg-teal-100 dark:bg-teal-900 border border-teal-400"></div>
						<span class="text-gray-500 dark:text-gray-400">Rounded</span>
					</div>
					<div class="flex items-center gap-1.5">
						<div class="w-3 h-3 rotate-45 bg-purple-100 dark:bg-purple-900 border border-purple-400"></div>
						<span class="text-gray-500 dark:text-gray-400">Diamond</span>
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
				class="flex-1 {showJsonCode ? 'w-1/2' : 'w-full'} h-[60vh] border border-gray-100 dark:border-gray-800 rounded-lg overflow-hidden bg-gradient-to-br from-gray-50 to-white dark:from-gray-900 dark:to-gray-800 relative"
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
				<div class="flex-1 w-1/2 h-[60vh] flex flex-col border border-gray-100 dark:border-gray-800 rounded-lg overflow-hidden">
					<div class="flex justify-between items-center px-4 py-2 border-b border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50">
						<span class="text-caption text-gray-600 dark:text-gray-400">diagram_spec.json</span>
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
