<script lang="ts">
	/**
	 * Scene Preview Modal
	 *
	 * Full view for scene_spec with entities, relations, annotations.
	 * Supports LaTeX formula rendering via KaTeX in annotations.
	 * Includes JSON code toggle.
	 */
	import { getContext, onMount } from 'svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import type { renderToString as katexRenderToString } from 'katex';

	const i18n = getContext('i18n');

	export let show = false;
	export let spec: any;

	let showJsonCode = false;
	let jsonCopied = false;
	let katexRender: typeof katexRenderToString | null = null;
	let katexLoaded = false;

	// Load KaTeX for formula rendering
	onMount(async () => {
		try {
			const [katex] = await Promise.all([
				import('katex'),
				import('katex/contrib/mhchem'),
				import('katex/dist/katex.min.css')
			]);
			katexRender = katex.renderToString;
			katexLoaded = true;
		} catch (e) {
			console.error('Failed to load KaTeX:', e);
		}
	});

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

	// Calculate entity positions
	const calculateEntityPositions = (entities: any[], relations: any[], width: number, height: number) => {
		const positions: Record<string, { x: number; y: number }> = {};
		const entityCount = entities.length;

		entities.forEach((entity, idx) => {
			if (entity.position) {
				positions[entity.id] = {
					x: entity.position.x * (width / 100),
					y: entity.position.y * (height / 100)
				};
			} else {
				const spacing = width / (entityCount + 1);
				positions[entity.id] = {
					x: spacing * (idx + 1),
					y: height / 2
				};
			}
		});

		return positions;
	};

	// Render entity with full detail
	const renderEntity = (entity: any, x: number, y: number, scale: number = 1) => {
		const appearance = entity.appearance;

		if (appearance?.type === 'svg' && appearance.svg) {
			const viewBox = appearance.viewBox?.split(' ').map(Number) || [0, 0, 100, 50];
			const w = viewBox[2] * scale;
			const h = viewBox[3] * scale;

			return `<g transform="translate(${x - w/2}, ${y - h/2})" class="entity-group" data-id="${entity.id}">
				<g transform="scale(${scale})">
					${appearance.svg}
				</g>
			</g>`;
		}

		// Default shape based on kind
		const w = 80 * scale;
		const h = 50 * scale;
		let fill = '#3b82f6';

		switch (entity.kind) {
			case 'vehicle': fill = '#3b82f6'; break;
			case 'person': fill = '#22c55e'; break;
			case 'object': fill = '#f59e0b'; break;
			case 'point': fill = '#ef4444'; break;
		}

		return `<g class="entity-group" data-id="${entity.id}">
			<rect x="${x - w/2}" y="${y - h/2}" width="${w}" height="${h}"
				fill="${fill}" rx="6" opacity="0.9"/>
			<text x="${x}" y="${y + 4}" text-anchor="middle" fill="white" font-size="12" font-weight="600">${entity.label || entity.id}</text>
		</g>`;
	};

	// Render motion arrow with label
	const renderMotionArrow = (entity: any, x: number, y: number, direction: string, dark: boolean) => {
		const arrowLength = 60;
		const color = dark ? '#22c55e' : '#16a34a';

		let dx = 0, dy = 0;
		let rotation = 0;
		switch (direction) {
			case 'right': dx = arrowLength; rotation = 0; break;
			case 'left': dx = -arrowLength; rotation = 180; break;
			case 'up': dy = -arrowLength; rotation = -90; break;
			case 'down': dy = arrowLength; rotation = 90; break;
		}

		const startX = x + (dx > 0 ? 50 : dx < 0 ? -50 : 0);
		const startY = y + (dy > 0 ? 30 : dy < 0 ? -30 : 0);
		const endX = startX + dx;
		const endY = startY + dy;

		return `<g class="motion-indicator">
			<line x1="${startX}" y1="${startY}" x2="${endX}" y2="${endY}"
				stroke="${color}" stroke-width="3" marker-end="url(#motion-arrow-full)"/>
		</g>`;
	};

	// Render distance with measurement
	const renderDistance = (fromPos: any, toPos: any, value: string, dark: boolean) => {
		const midX = (fromPos.x + toPos.x) / 2;
		const y = Math.max(fromPos.y, toPos.y) + 60;
		const lineColor = dark ? '#64748b' : '#94a3b8';
		const textColor = dark ? '#e2e8f0' : '#334155';
		const bgColor = dark ? '#1e293b' : '#ffffff';

		return `<g class="distance-indicator">
			<line x1="${fromPos.x}" y1="${y - 8}" x2="${fromPos.x}" y2="${y + 8}" stroke="${lineColor}" stroke-width="2"/>
			<line x1="${fromPos.x}" y1="${y}" x2="${toPos.x}" y2="${y}" stroke="${lineColor}" stroke-width="2" stroke-dasharray="8,4"/>
			<line x1="${toPos.x}" y1="${y - 8}" x2="${toPos.x}" y2="${y + 8}" stroke="${lineColor}" stroke-width="2"/>
			<rect x="${midX - 40}" y="${y + 8}" width="80" height="24" fill="${bgColor}" rx="4" stroke="${lineColor}" stroke-width="1"/>
			<text x="${midX}" y="${y + 24}" text-anchor="middle" fill="${textColor}" font-size="13" font-weight="600" font-family="system-ui">${value}</text>
		</g>`;
	};

	// Render annotation - supports both label and formula types
	const renderAnnotation = (ann: any, entityPos: any, dark: boolean) => {
		const textColor = dark ? '#e2e8f0' : '#334155';
		const bgColor = dark ? 'rgba(30, 41, 59, 0.95)' : 'rgba(255, 255, 255, 0.98)';
		const borderColor = dark ? '#475569' : '#cbd5e1';

		let x = entityPos.x + (ann.offset?.x || 0);
		let y = entityPos.y + (ann.offset?.y || 0);

		switch (ann.position) {
			case 'top': y -= 45; break;
			case 'bottom': y += 45; break;
			case 'left': x -= 70; break;
			case 'right': x += 70; break;
		}

		// For formula type, use KaTeX rendering with foreignObject
		if ((ann.type === 'formula' || ann.type === 'math') && katexRender) {
			try {
				const katexHtml = katexRender(ann.text, {
					displayMode: false,
					throwOnError: false,
					output: 'html'
				});

				// Estimate width based on formula complexity
				const estimatedWidth = Math.max(ann.text.length * 10 + 24, 60);
				const height = 32;

				return `<g class="annotation annotation-formula" data-type="${ann.type}">
					<rect x="${x - estimatedWidth/2}" y="${y - height/2}" width="${estimatedWidth}" height="${height}"
						fill="${bgColor}" stroke="${borderColor}" stroke-width="1" rx="6"/>
					<foreignObject x="${x - estimatedWidth/2 + 4}" y="${y - height/2 + 2}" width="${estimatedWidth - 8}" height="${height - 4}">
						<div xmlns="http://www.w3.org/1999/xhtml"
							style="display: flex; align-items: center; justify-content: center; height: 100%;
								font-size: 14px; color: ${textColor}; font-family: 'KaTeX_Main', serif;">
							${katexHtml}
						</div>
					</foreignObject>
				</g>`;
			} catch (e) {
				// Fallback to plain text if KaTeX fails
				console.warn('KaTeX render failed:', e);
			}
		}

		// Default text rendering for label type or fallback
		const textWidth = ann.text.length * 7 + 16;

		return `<g class="annotation" data-type="${ann.type || 'label'}">
			<rect x="${x - textWidth/2}" y="${y - 12}" width="${textWidth}" height="24"
				fill="${bgColor}" stroke="${borderColor}" stroke-width="1" rx="4"/>
			<text x="${x}" y="${y + 4}" text-anchor="middle" fill="${textColor}"
				font-size="12" font-weight="500" font-family="system-ui">${ann.text}</text>
		</g>`;
	};

	// Re-render when katexLoaded changes
	$: svgContent = (() => {
		// Depend on katexLoaded to trigger re-render when KaTeX is ready
		const _ = katexLoaded;
		if (!spec || !spec.entities) return '';

		const dark = isDarkMode();
		const width = 700;
		const height = 400;

		const entities = spec.entities || [];
		const relations = spec.relations || [];
		const annotations = spec.annotations || [];

		const positions = calculateEntityPositions(entities, relations, width, height);

		const bgColor = dark ? '#0f172a' : '#f8fafc';
		const gridColor = dark ? 'rgba(100, 116, 139, 0.2)' : 'rgba(148, 163, 184, 0.3)';
		const arrowColor = dark ? '#22c55e' : '#16a34a';

		let svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="100%" height="100%">`;

		// Definitions
		svg += `<defs>
			<marker id="motion-arrow-full" markerWidth="10" markerHeight="7" refX="8" refY="3.5" orient="auto">
				<polygon points="0 0, 10 3.5, 0 7" fill="${arrowColor}"/>
			</marker>
			<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
				<path d="M 40 0 L 0 0 0 40" fill="none" stroke="${gridColor}" stroke-width="0.5"/>
			</pattern>
		</defs>`;

		// Background with grid
		svg += `<rect width="${width}" height="${height}" fill="${bgColor}"/>`;
		svg += `<rect width="${width}" height="${height}" fill="url(#grid)"/>`;

		// Render distance relations
		relations.forEach((rel: any) => {
			if (rel.type === 'distance' && rel.from && rel.to) {
				const fromPos = positions[rel.from];
				const toPos = positions[rel.to];
				if (fromPos && toPos) {
					svg += renderDistance(fromPos, toPos, rel.value || '', dark);
				}
			}
		});

		// Render entities
		entities.forEach((entity: any) => {
			const pos = positions[entity.id];
			if (pos) {
				svg += renderEntity(entity, pos.x, pos.y, 0.8);
			}
		});

		// Render motion arrows
		relations.forEach((rel: any) => {
			if (rel.type === 'motion' && rel.entity && rel.direction) {
				const pos = positions[rel.entity];
				if (pos) {
					svg += renderMotionArrow(rel, pos.x, pos.y, rel.direction, dark);
				}
			}
		});

		// Render annotations
		annotations.forEach((ann: any) => {
			const pos = positions[ann.attachTo];
			if (pos) {
				svg += renderAnnotation(ann, pos, dark);
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
					{$i18n.t('Scene View')}
				</h3>
				<!-- Legend -->
				<div class="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
					<div class="flex items-center gap-1.5">
						<svg class="w-4 h-2" viewBox="0 0 20 10">
							<line x1="0" y1="5" x2="15" y2="5" stroke="#22c55e" stroke-width="2"/>
							<polygon points="15,2 20,5 15,8" fill="#22c55e"/>
						</svg>
						<span>Motion</span>
					</div>
					<div class="flex items-center gap-1.5">
						<svg class="w-4 h-2" viewBox="0 0 20 10">
							<line x1="0" y1="5" x2="20" y2="5" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="4,2"/>
						</svg>
						<span>Distance</span>
					</div>
				</div>
			</div>
			<div class="flex items-center gap-2">
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
			<div class="flex-1 {showJsonCode ? 'w-1/2' : 'w-full'} h-[60vh] border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
				<div class="w-full h-full flex items-center justify-center p-4 bg-slate-50 dark:bg-slate-900">
					{@html svgContent}
				</div>
			</div>

			{#if showJsonCode}
				<div class="flex-1 w-1/2 h-[60vh] flex flex-col border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
					<div class="flex justify-between items-center px-4 py-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
						<span class="text-caption text-gray-600 dark:text-gray-400">scene_spec.json</span>
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
