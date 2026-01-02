<script lang="ts">
	/**
	 * Scene Renderer
	 *
	 * Renders spatial scenes with entities, relations, and annotations.
	 * Supports SVG entities, motion indicators, distance markers, labels, and LaTeX formulas.
	 */
	import { getContext, onMount } from 'svelte';
	import ScenePreviewModal from './ScenePreviewModal.svelte';
	import ArrowsPointingOut from '$lib/components/icons/ArrowsPointingOut.svelte';
	import type { renderToString as katexRenderToString } from 'katex';

	const i18n = getContext('i18n');

	export let spec: any;

	let showModal = false;
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

	function isDarkMode(): boolean {
		return document.documentElement.classList.contains('dark');
	}

	// Calculate entity positions based on relations
	const calculateEntityPositions = (entities: any[], relations: any[], width: number, height: number) => {
		const positions: Record<string, { x: number; y: number }> = {};
		const entityCount = entities.length;

		// Default horizontal distribution
		entities.forEach((entity, idx) => {
			if (entity.position) {
				positions[entity.id] = entity.position;
			} else {
				// Distribute entities horizontally
				const spacing = width / (entityCount + 1);
				positions[entity.id] = {
					x: spacing * (idx + 1),
					y: height / 2
				};
			}
		});

		return positions;
	};

	// Render entity based on appearance
	const renderEntity = (entity: any, x: number, y: number, scale: number = 0.4) => {
		const appearance = entity.appearance;

		if (appearance?.type === 'svg' && appearance.svg) {
			// Parse viewBox to get dimensions
			const viewBox = appearance.viewBox?.split(' ').map(Number) || [0, 0, 100, 50];
			const w = viewBox[2] * scale;
			const h = viewBox[3] * scale;

			return `<g transform="translate(${x - w/2}, ${y - h/2})">
				<g transform="scale(${scale})">
					${appearance.svg}
				</g>
			</g>`;
		}

		// Default rectangle representation
		const w = 40 * scale;
		const h = 25 * scale;
		return `<rect x="${x - w/2}" y="${y - h/2}" width="${w}" height="${h}"
			fill="#3b82f6" rx="3" opacity="0.8"/>`;
	};

	// Render motion arrow
	const renderMotionArrow = (entity: any, x: number, y: number, direction: string, dark: boolean) => {
		const arrowLength = 25;
		const color = dark ? '#22c55e' : '#16a34a';

		let dx = 0, dy = 0;
		switch (direction) {
			case 'right': dx = arrowLength; break;
			case 'left': dx = -arrowLength; break;
			case 'up': dy = -arrowLength; break;
			case 'down': dy = arrowLength; break;
		}

		const startX = x + (dx > 0 ? 20 : dx < 0 ? -20 : 0);
		const startY = y + (dy > 0 ? 15 : dy < 0 ? -15 : 0);
		const endX = startX + dx;
		const endY = startY + dy;

		return `<line x1="${startX}" y1="${startY}" x2="${endX}" y2="${endY}"
			stroke="${color}" stroke-width="2" marker-end="url(#motion-arrow)"/>`;
	};

	// Render distance indicator
	const renderDistance = (fromPos: any, toPos: any, value: string, dark: boolean) => {
		const midX = (fromPos.x + toPos.x) / 2;
		const y = Math.max(fromPos.y, toPos.y) + 25;
		const textColor = dark ? '#e2e8f0' : '#334155';

		return `<g>
			<line x1="${fromPos.x}" y1="${y - 5}" x2="${fromPos.x}" y2="${y + 5}" stroke="${textColor}" stroke-width="1"/>
			<line x1="${fromPos.x}" y1="${y}" x2="${toPos.x}" y2="${y}" stroke="${textColor}" stroke-width="1" stroke-dasharray="4,2"/>
			<line x1="${toPos.x}" y1="${y - 5}" x2="${toPos.x}" y2="${y + 5}" stroke="${textColor}" stroke-width="1"/>
			<text x="${midX}" y="${y + 12}" text-anchor="middle" fill="${textColor}" font-size="8" font-family="system-ui">${value}</text>
		</g>`;
	};

	// Render annotation with LaTeX support for thumbnails
	const renderAnnotation = (ann: any, x: number, y: number, dark: boolean) => {
		const textColor = dark ? '#e2e8f0' : '#334155';
		const bgColor = dark ? 'rgba(30, 41, 59, 0.95)' : 'rgba(255, 255, 255, 0.95)';
		const borderColor = dark ? '#475569' : '#cbd5e1';

		// For formula type, use KaTeX rendering with foreignObject
		if ((ann.type === 'formula' || ann.type === 'math') && katexRender) {
			try {
				const katexHtml = katexRender(ann.text, {
					displayMode: false,
					throwOnError: false,
					output: 'html'
				});

				const width = Math.max(ann.text.length * 5 + 12, 30);
				const height = 16;

				return `<g class="annotation-formula">
					<rect x="${x - width/2}" y="${y - height/2}" width="${width}" height="${height}"
						fill="${bgColor}" stroke="${borderColor}" stroke-width="0.5" rx="3"/>
					<foreignObject x="${x - width/2 + 2}" y="${y - height/2 + 1}" width="${width - 4}" height="${height - 2}">
						<div xmlns="http://www.w3.org/1999/xhtml"
							style="display: flex; align-items: center; justify-content: center; height: 100%;
								font-size: 8px; color: ${textColor}; transform: scale(0.85); transform-origin: center;">
							${katexHtml}
						</div>
					</foreignObject>
				</g>`;
			} catch (e) {
				// Fallback to plain text
			}
		}

		// Default text rendering
		return `<text x="${x}" y="${y}" text-anchor="middle" fill="${textColor}" font-size="7" font-family="system-ui">${ann.text}</text>`;
	};

	// Depend on katexLoaded to trigger re-render
	$: svgContent = (() => {
		const _ = katexLoaded;
		if (!spec || !spec.entities) return '';

		const dark = isDarkMode();
		const width = 180;
		const height = 120;

		const entities = spec.entities || [];
		const relations = spec.relations || [];
		const annotations = spec.annotations || [];

		const positions = calculateEntityPositions(entities, relations, width, height);

		const textColor = dark ? '#e2e8f0' : '#334155';
		const bgColor = dark ? '#1e293b' : '#f8fafc';
		const arrowColor = dark ? '#22c55e' : '#16a34a';

		let svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="100%" height="100%">`;

		// Definitions
		svg += `<defs>
			<marker id="motion-arrow" markerWidth="6" markerHeight="4" refX="5" refY="2" orient="auto">
				<polygon points="0 0, 6 2, 0 4" fill="${arrowColor}"/>
			</marker>
		</defs>`;

		// Background
		svg += `<rect width="${width}" height="${height}" fill="${bgColor}" rx="4"/>`;

		// Render relations (distance lines, etc.)
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
				svg += renderEntity(entity, pos.x, pos.y, 0.35);
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

		// Render annotations (simplified for thumbnail, supports LaTeX formulas)
		annotations.slice(0, 3).forEach((ann: any) => {
			const pos = positions[ann.attachTo];
			if (pos) {
				let labelX = pos.x + (ann.offset?.x ? ann.offset.x * 0.4 : 0);
				let labelY = pos.y - 20 + (ann.offset?.y ? ann.offset.y * 0.4 : 0);

				if (ann.position === 'bottom') labelY = pos.y + 25;
				if (ann.position === 'left') { labelX = pos.x - 30; labelY = pos.y; }
				if (ann.position === 'right') { labelX = pos.x + 30; labelY = pos.y; }

				svg += renderAnnotation(ann, labelX, labelY, dark);
			}
		});

		svg += '</svg>';
		return svg;
	})();
</script>

<div class="relative w-48 h-32 group mb-2 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden bg-gradient-to-br from-slate-50 to-gray-100 dark:from-slate-900 dark:to-gray-800">
	<div class="w-full h-full flex items-center justify-center p-1">
		{@html svgContent}
	</div>

	<div class="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-white dark:from-gray-900 to-transparent pointer-events-none" />

	<button
		class="absolute bottom-1.5 left-1/2 -translate-x-1/2 flex items-center gap-1 text-[10px] text-gray-600 dark:text-gray-400 bg-white/90 dark:bg-gray-800/90 px-2 py-0.5 rounded-full backdrop-blur-sm hover:bg-white dark:hover:bg-gray-700 transition z-10 shadow-sm"
		on:click={() => (showModal = true)}
	>
		<ArrowsPointingOut className="size-2.5" />
		<span>{$i18n.t('확대')}</span>
	</button>
</div>

<ScenePreviewModal bind:show={showModal} {spec} />
