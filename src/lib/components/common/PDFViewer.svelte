<script lang="ts">
	import { getContext, onMount, onDestroy, tick } from 'svelte';
	import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.mjs?url';
	import panzoom, { type PanZoom } from 'panzoom';
	import { clampDocumentTargetPage } from '$lib/utils/documentPreview';
	import Spinner from './Spinner.svelte';
	import { readPdfComments } from '$lib/utils/comments/pdf';
	import { mapWordComments, type PdfTextRun } from '$lib/utils/comments/pdfAnchors';
	import { findTextRange, highlightRange, commentPin } from '$lib/utils/comments/highlights';
	import type { FileComment, CommentResult } from '$lib/utils/comments/types';

	const i18n: any = getContext('i18n');

	export let url: string | null = null;
	export let data: ArrayBuffer | Uint8Array | null = null;
	export let className = 'w-full h-[70vh]';
	export let targetPage: number | null = null;
	export let singlePage = false;
	export let itemLabel = 'Page';
	export let onPageChange: ((page: number) => void) | null = null;
	export let onComments: ((result: CommentResult) => void) | null = null;
	export let onCommentsError: (() => void) | null = null;
	export let onCommentSelect: ((comment: FileComment) => void) | null = null;
	export let selectedComment: FileComment | null = null;
	export let sourceComments: FileComment[] | null = null;
	export let onAnchors: ((ids: string[]) => void) | null = null;
	let mappedSource: FileComment[] | null = null;
	let mappedDoc: PdfDocument | null = null;
	let textRuns: Promise<PdfTextRun[]> | null = null;
	const mapSourceComments = async () => {
		if (!sourceComments || !pdfDoc || (mappedSource === sourceComments && mappedDoc === pdfDoc))
			return;
		const doc = pdfDoc;
		const source = sourceComments;
		mappedDoc = doc;
		mappedSource = source;
		if (!textRuns)
			textRuns = (async () => {
				const runs: PdfTextRun[] = [];
				for (let number = 1; number <= doc.numPages; number++) {
					const page = await doc.getPage(number);
					const content = await page.getTextContent();
					for (const item of content.items)
						if ('str' in item) {
							const [a, b, c, d, x, y] = item.transform;
							const height = item.height || Math.hypot(c, d);
							runs.push({ text: item.str, page: number, rect: [x, y, x + item.width, y + height] });
						}
				}
				return runs;
			})();
		try {
			const word = source.some((c) => c.location?.kind === 'word');
			const mapped = word ? mapWordComments(source, await textRuns) : [];
			if (!word)
				for (const c of source) {
					const loc = c.location;
					if (
						loc?.kind !== 'slide' ||
						loc.hidden ||
						!loc.pdfPage ||
						loc.pdfPage > doc.numPages ||
						loc.x === undefined ||
						loc.y === undefined ||
						!loc.width ||
						!loc.height
					)
						continue;
					const page = await doc.getPage(loc.pdfPage);
					const [left, bottom, right, top] = page.view;
					const x = left + (loc.x / loc.width) * (right - left);
					const y = top - (loc.y / loc.height) * (top - bottom);
					mapped.push({
						...c,
						location: { kind: 'pdf', page: loc.pdfPage, rect: [x, y - 18, x + 18, y] }
					});
				}
			if (mappedDoc !== doc || mappedSource !== source || pdfDoc !== doc) return;
			comments = mapped;
			onAnchors?.(comments.map((c) => c.id));
			void renderCommentMarkers();
		} catch {
			if (pdfDoc === doc) onAnchors?.([]);
		}
	};
	let comments: FileComment[] = [];
	let markerToken = 0;
	let resizeObserver: ResizeObserver | null = null;
	let lastWidth = 0;
	let lastHeight = 0;
	let resizeTimer: ReturnType<typeof setTimeout>;
	const renderCommentMarkers = async () => {
		const token = ++markerToken;
		if (!sceneElement || !pdfDoc || (!onComments && !sourceComments)) return;
		const doc = pdfDoc;
		for (const wrapper of Array.from(
			sceneElement.querySelectorAll<HTMLElement>('.pdf-page-wrapper')
		)) {
			wrapper.querySelector('.file-comment-layer')?.remove();
			const pageNumber = Number(wrapper.dataset.pageNumber);
			const page = await doc.getPage(pageNumber);
			if (token !== markerToken) return;
			const unit = page.getViewport({ scale: 1 });
			const viewport = page.getViewport({ scale: parseFloat(wrapper.style.width) / unit.width });
			const layer = document.createElement('div');
			layer.className = 'file-comment-layer';
			Object.assign(layer.style, {
				position: 'absolute',
				inset: '0',
				pointerEvents: 'none',
				zIndex: '4'
			});
			for (const comment of comments.filter(
				(c) => c.location?.kind === 'pdf' && c.location.page === pageNumber && !c.parentId
			)) {
				const loc = comment.location;
				if (loc?.kind !== 'pdf' || loc.rect.length !== 4 || !loc.rect.every(Number.isFinite))
					continue;
				const rect = viewport.convertToViewportRectangle(loc.rect);
				const left = Math.min(rect[0], rect[2]);
				const top = Math.min(rect[1], rect[3]);
				const source = sourceComments?.find((c) => c.id === comment.id);
				if (source?.location?.kind === 'word' && source.location.quote) {
					const range = findTextRange(sceneElement, source.location.quote);
					if (
						range &&
						highlightRange(
							wrapper,
							layer,
							range,
							comment.id,
							`${$i18n.t('Comment')}: ${comment.author || $i18n.t('Unknown author')}`
						)
					)
						continue;
				}
				const regions = loc.quads?.length
					? Array.from({ length: Math.floor(loc.quads.length / 8) }, (_, i) => {
							const q = loc.quads!.slice(i * 8, i * 8 + 8);
							return [
								Math.min(q[0], q[2], q[4], q[6]),
								Math.min(q[1], q[3], q[5], q[7]),
								Math.max(q[0], q[2], q[4], q[6]),
								Math.max(q[1], q[3], q[5], q[7])
							];
						})
					: [];
				for (const region of regions) {
					const r = viewport.convertToViewportRectangle(region);
					const target = document.createElement('button');
					target.type = 'button';
					target.dataset.fileCommentId = comment.id;
					target.dataset.commentHighlight = comment.id;
					target.setAttribute(
						'aria-label',
						`${$i18n.t('Comment')}: ${comment.author || $i18n.t('Unknown author')}`
					);
					Object.assign(target.style, {
						position: 'absolute',
						left: `${Math.min(r[0], r[2])}px`,
						top: `${Math.min(r[1], r[3])}px`,
						width: `${Math.abs(r[2] - r[0])}px`,
						height: `${Math.abs(r[3] - r[1])}px`,
						pointerEvents: 'none',
						background: 'transparent',
						border: '0',
						borderBottom: '1px solid rgba(180,130,30,.6)',
						cursor: 'help'
					});
					layer.appendChild(target);
				}
				if (regions.length) continue;
				const button = commentPin(
					comment.id,
					`${$i18n.t('Comment')}: ${comment.author || $i18n.t('Unknown author')}`
				);
				button.dataset.commentId = comment.id;
				button.style.left = `${Math.max(0, Math.min(viewport.width - 20, left - 22))}px`;
				button.style.top = `${Math.max(0, Math.min(viewport.height - 20, top))}px`;
				button.onclick = () => onCommentSelect?.(comment);
				layer.appendChild(button);
			}
			const selected = selectedComment?.location;
			if (selected?.kind === 'pdf' && selected.page === pageNumber) {
				const regions: number[][] = [];
				if (selected.quads?.length)
					for (let i = 0; i + 7 < selected.quads.length; i += 8) {
						const q = selected.quads.slice(i, i + 8);
						regions.push([
							Math.min(q[0], q[2], q[4], q[6]),
							Math.min(q[1], q[3], q[5], q[7]),
							Math.max(q[0], q[2], q[4], q[6]),
							Math.max(q[1], q[3], q[5], q[7])
						]);
					}
				else regions.push(selected.rect);
				for (const region of regions) {
					if (region.length !== 4 || !region.every(Number.isFinite)) continue;
					const r = viewport.convertToViewportRectangle(region);
					const highlight = document.createElement('div');
					highlight.dataset.selectedAnnotation = selectedComment!.id;
					Object.assign(highlight.style, {
						position: 'absolute',
						left: `${Math.min(r[0], r[2])}px`,
						top: `${Math.min(r[1], r[3])}px`,
						width: `${Math.max(3, Math.abs(r[2] - r[0]))}px`,
						height: `${Math.max(3, Math.abs(r[3] - r[1]))}px`,
						outline: '2px solid #2563eb',
						background: 'rgba(250,204,21,.15)'
					});
					layer.appendChild(highlight);
				}
			}
			wrapper.appendChild(layer);
		}
	};

	type PdfDocument = import('pdfjs-dist').PDFDocumentProxy;
	type PdfTextLayer = InstanceType<typeof import('pdfjs-dist').TextLayer>;

	let outerContainer: HTMLDivElement;
	let sceneElement: HTMLDivElement;
	let loading = true;
	let error = '';
	let pdfDoc: PdfDocument | null = null;
	let pzInstance: PanZoom | null = null;
	let zoomLevel = 1;
	let rerenderTimer: ReturnType<typeof setTimeout> | null = null;
	let lastRenderedZoom = 1;
	let pageCount = 0;
	let renderedPage = 0;
	let activePage = 1;
	let loadToken = 0;
	let renderToken = 0;
	let scrollFrame: number | null = null;
	let mounted = false;
	let loadedSource: ArrayBuffer | Uint8Array | string | null = null;
	let wheelDelta = 0;
	let lastWheelNavigationAt = 0;
	const wheelNavigationThreshold = 80;
	const wheelNavigationCooldown = 450;
	const pageShortcutKeys = ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'];

	$: selectedPage = singlePage ? (clampDocumentTargetPage(targetPage, pageCount) ?? 1) : activePage;

	// Keep a reference to TextLayer instances so we can update/cancel them
	let textLayerInstances: PdfTextLayer[] = [];

	const copyPdfData = (pdfData: ArrayBuffer | Uint8Array) =>
		pdfData instanceof Uint8Array ? pdfData.slice() : pdfData.slice(0);

	const cancelTextLayers = () => {
		for (const tl of textLayerInstances) {
			try {
				tl.cancel();
			} catch {
				// Text layers can already be resolved or canceled during rerenders.
			}
		}
		textLayerInstances = [];
	};

	const initPanzoom = () => {
		if (pzInstance) {
			pzInstance.dispose();
		}
		if (sceneElement) {
			pzInstance = panzoom(sceneElement, {
				bounds: true,
				boundsPadding: 0.1,
				zoomSpeed: 0.065,
				beforeWheel: (e) => {
					// Only zoom on pinch (ctrlKey / metaKey); let normal scroll pass through
					if (!e.ctrlKey && !e.metaKey) {
						return true; // returning true cancels the panzoom wheel handling
					}
					return false;
				},
				beforeMouseDown: (e) => {
					// Only allow drag-to-pan when zoomed in (not at default scale)
					if ((e?.target as HTMLElement | null)?.closest?.('.textLayer, .file-comment-layer')) {
						return true;
					}
					const transform = pzInstance?.getTransform();
					if (transform && Math.abs(transform.scale - 1) < 0.01) {
						return true; // cancel panzoom mouse handling at 1x — allow text selection / normal interaction
					}
					return false;
				}
			});
			pzInstance.on('zoom', () => {
				zoomLevel = pzInstance?.getTransform()?.scale ?? 1;
				// Debounced re-render at new resolution so text stays crisp
				if (rerenderTimer) clearTimeout(rerenderTimer);
				rerenderTimer = setTimeout(() => {
					if (Math.abs(zoomLevel - lastRenderedZoom) > 0.05) {
						rerenderPages(zoomLevel);
					}
				}, 300);
			});
		}
	};

	const zoomIn = () => {
		if (!pzInstance || !outerContainer) return;
		const cx = outerContainer.clientWidth / 2;
		const cy = outerContainer.clientHeight / 2;
		pzInstance.zoomTo(cx, cy, 1.25); // +25%
		zoomLevel = pzInstance.getTransform().scale;
	};

	const zoomOut = () => {
		if (!pzInstance || !outerContainer) return;
		const cx = outerContainer.clientWidth / 2;
		const cy = outerContainer.clientHeight / 2;
		pzInstance.zoomTo(cx, cy, 0.8); // -20% (inverse of 1.25)
		zoomLevel = pzInstance.getTransform().scale;
	};

	export const resetView = () => {
		if (pzInstance) {
			pzInstance.moveTo(0, 0);
			pzInstance.zoomAbs(0, 0, 1);
			zoomLevel = 1;
			rerenderPages(1);
		}
	};

	export const scrollToPage = async (page: number | null) => {
		targetPage = page;
		if (singlePage) {
			if (targetPage) onPageChange?.(targetPage);
		} else {
			await scrollToTargetPage();
		}
	};

	const selectPage = async (page: number) => {
		if (!pdfDoc) return;
		const nextPage = clampDocumentTargetPage(page, pdfDoc.numPages);
		if (!nextPage || nextPage === selectedPage) return;

		targetPage = nextPage;
		activePage = nextPage;
		onPageChange?.(nextPage);
		if (!singlePage) await scrollToTargetPage();
	};

	const scrollToTargetPage = async () => {
		if (!outerContainer || !sceneElement || !pdfDoc) return;
		const page = clampDocumentTargetPage(targetPage, pdfDoc.numPages);
		if (!page) return;

		if (singlePage) return;

		await tick();
		const pageWrapper = sceneElement.querySelectorAll('.pdf-page-wrapper')[page - 1] as
			| HTMLElement
			| undefined;
		pageWrapper?.scrollIntoView({ block: 'start' });
		activePage = page;
		onPageChange?.(page);
	};

	const syncVisiblePage = () => {
		scrollFrame = null;
		if (singlePage || !outerContainer || !sceneElement || !pdfDoc) return;

		const marker = outerContainer.getBoundingClientRect().top + outerContainer.clientHeight * 0.35;
		let bestPage = activePage;
		let bestDistance = Number.POSITIVE_INFINITY;

		for (const wrapper of sceneElement.querySelectorAll('.pdf-page-wrapper')) {
			const el = wrapper as HTMLElement;
			const page = Number(el.dataset.pageNumber);
			if (!page) continue;

			const rect = el.getBoundingClientRect();
			const distance =
				marker < rect.top ? rect.top - marker : marker > rect.bottom ? marker - rect.bottom : 0;
			if (distance < bestDistance) {
				bestDistance = distance;
				bestPage = page;
			}
		}

		if (bestPage !== activePage) {
			activePage = bestPage;
			onPageChange?.(bestPage);
		}
	};

	const handleScroll = () => {
		if (singlePage || scrollFrame !== null) return;
		scrollFrame = requestAnimationFrame(syncVisiblePage);
	};

	// Re-render existing canvases at a new zoom level (preserves panzoom transform)
	const rerenderPages = async (forZoom: number) => {
		if (!pdfDoc || !sceneElement) return;
		const pdfjs = await import('pdfjs-dist');
		const dpr = window.devicePixelRatio || 1;

		const pageWrappers = sceneElement.querySelectorAll('.pdf-page-wrapper');

		cancelTextLayers();

		for (let i = 0; i < pageWrappers.length; i++) {
			const page = await pdfDoc.getPage(singlePage ? selectedPage : i + 1);
			const viewport = page.getViewport({ scale: 1 });
			const cssScale = getCssScale(viewport);
			const renderScale = cssScale * forZoom * dpr;
			const scaledViewport = page.getViewport({ scale: renderScale });
			const cssViewport = page.getViewport({ scale: cssScale });

			const wrapper = pageWrappers[i] as HTMLElement;
			// Update the CSS custom property so textLayer dimensions resolve correctly
			wrapper.style.setProperty('--scale-factor', String(cssViewport.scale));

			const canvas = wrapper.querySelector('canvas')!;
			canvas.width = scaledViewport.width;
			canvas.height = scaledViewport.height;

			const ctx = canvas.getContext('2d');
			if (ctx) {
				await page.render({ canvas, canvasContext: ctx, viewport: scaledViewport }).promise;
			}

			// Rebuild text layer
			const textLayerDiv = wrapper.querySelector('.textLayer') as HTMLElement;
			if (textLayerDiv) {
				textLayerDiv.innerHTML = '';

				const textContent = await page.getTextContent();
				const textLayer = new pdfjs.TextLayer({
					textContentSource: textContent,
					container: textLayerDiv,
					viewport: cssViewport
				});
				await textLayer.render();
				textLayerInstances.push(textLayer);
			}
		}
		lastRenderedZoom = forZoom;
	};

	const getCssScale = (viewport: { width: number; height: number }) => {
		if (!singlePage) return (outerContainer?.clientWidth || 800) / viewport.width;

		const availableWidth = Math.max(320, (outerContainer?.clientWidth || 800) - 64);
		const availableHeight = Math.max(220, (outerContainer?.clientHeight || 600) - 64);
		return Math.min(1, availableWidth / viewport.width, availableHeight / viewport.height);
	};

	const renderAllPages = async () => {
		if (!pdfDoc || !sceneElement) return;
		const token = ++renderToken;

		cancelTextLayers();

		const pdfjs = await import('pdfjs-dist');
		const dpr = window.devicePixelRatio || 1;
		const wrappers: HTMLElement[] = [];
		const firstPage = singlePage ? selectedPage : 1;
		const lastPage = singlePage ? selectedPage : pdfDoc.numPages;

		for (let i = firstPage; i <= lastPage; i++) {
			const page = await pdfDoc.getPage(i);
			if (token !== renderToken) return;
			const viewport = page.getViewport({ scale: 1 });

			// Scale to fit container width
			const cssScale = getCssScale(viewport);
			const renderScale = cssScale * dpr;
			const scaledViewport = page.getViewport({ scale: renderScale });
			const cssViewport = page.getViewport({ scale: cssScale });

			// Create page wrapper (positioned container for canvas + text layer)
			const wrapper = document.createElement('div');
			wrapper.className = 'pdf-page-wrapper';
			wrapper.dataset.pageNumber = String(i);
			wrapper.style.position = 'relative';
			wrapper.style.width = `${Math.round(cssScale * viewport.width)}px`;
			wrapper.style.height = `${Math.round(cssScale * viewport.height)}px`;
			wrapper.style.display = 'block';
			// pdfjs TextLayer uses --total-scale-factor (= --scale-factor * --user-unit)
			// to position/size text spans. We must set --scale-factor so the calc resolves.
			wrapper.style.setProperty('--scale-factor', String(cssViewport.scale));

			if (i > 1) {
				wrapper.style.marginTop = '4px';
			}

			// Create canvas
			const canvas = document.createElement('canvas');
			canvas.width = scaledViewport.width;
			canvas.height = scaledViewport.height;
			// CSS size stays at the CSS-pixel dimensions for layout
			canvas.style.width = `${Math.round(cssScale * viewport.width)}px`;
			canvas.style.height = `${Math.round(cssScale * viewport.height)}px`;
			canvas.style.display = 'block';
			wrapper.appendChild(canvas);

			const ctx = canvas.getContext('2d');
			if (!ctx) continue;

			await page.render({
				canvas,
				canvasContext: ctx,
				viewport: scaledViewport
			}).promise;
			if (token !== renderToken) return;

			// Create text layer overlay — pdfjs setLayerDimensions handles its sizing
			const textLayerDiv = document.createElement('div');
			textLayerDiv.className = 'textLayer';
			wrapper.appendChild(textLayerDiv);

			const textContent = await page.getTextContent();
			const textLayer = new pdfjs.TextLayer({
				textContentSource: textContent,
				container: textLayerDiv,
				viewport: cssViewport
			});
			await textLayer.render();
			if (token !== renderToken) return;
			textLayerInstances.push(textLayer);

			wrappers.push(wrapper);
		}

		sceneElement.replaceChildren(...wrappers);
		void renderCommentMarkers();
		lastRenderedZoom = 1;
		renderedPage = singlePage ? selectedPage : 0;
		initPanzoom();
		await scrollToTargetPage();
		syncVisiblePage();
	};

	const handleWheel = (e: WheelEvent) => {
		if (!singlePage) return;
		if (e.ctrlKey || e.metaKey) return;

		const transform = pzInstance?.getTransform();
		if (transform && Math.abs(transform.scale - 1) >= 0.01) {
			e.preventDefault();
			pzInstance?.moveBy(-e.deltaX, -e.deltaY, false);
			zoomLevel = pzInstance?.getTransform()?.scale ?? 1;
			return;
		}

		e.preventDefault();
		if (pageCount <= 1) return;

		const multiplier = e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? outerContainer.clientHeight : 1;
		const dominantDelta = Math.abs(e.deltaY) >= Math.abs(e.deltaX) ? e.deltaY : e.deltaX;
		wheelDelta += dominantDelta * multiplier;

		const now = Date.now();
		if (Math.abs(wheelDelta) < wheelNavigationThreshold) return;
		if (now - lastWheelNavigationAt < wheelNavigationCooldown) {
			wheelDelta = 0;
			return;
		}

		lastWheelNavigationAt = now;
		void selectPage(selectedPage + (wheelDelta > 0 ? 1 : -1));
		wheelDelta = 0;
	};

	const handleKeyDown = (e: KeyboardEvent) => {
		if (
			!singlePage ||
			e.defaultPrevented ||
			e.altKey ||
			e.ctrlKey ||
			e.metaKey ||
			pageCount <= 1 ||
			!pageShortcutKeys.includes(e.key)
		) {
			return;
		}

		e.preventDefault();
		void selectPage(selectedPage + (e.key === 'ArrowUp' || e.key === 'ArrowLeft' ? -1 : 1));
	};

	const focusViewer = () => {
		if (!outerContainer?.contains(document.activeElement)) outerContainer?.focus();
	};

	const loadPdf = async () => {
		if (!url && !data) return;

		const source = data ?? url;
		if (source === loadedSource) return;
		const token = ++loadToken;
		loadedSource = source;
		loading = true;
		error = '';
		renderedPage = 0;
		pageCount = 0;
		pzInstance?.dispose();
		cancelTextLayers();
		pdfDoc?.destroy();
		pdfDoc = null;
		textRuns = null;
		mappedDoc = null;
		mappedSource = null;
		comments = [];

		try {
			const pdfjs = await import('pdfjs-dist');
			pdfjs.GlobalWorkerOptions.workerSrc = pdfWorkerUrl;

			let pdfData: ArrayBuffer | Uint8Array;
			if (data) {
				pdfData = copyPdfData(data);
			} else {
				// Fetch with credentials so auth cookies are sent
				const res = await fetch(url!, { credentials: 'include' });
				if (!res.ok) throw new Error(`HTTP ${res.status}`);
				pdfData = await res.arrayBuffer();
			}
			pdfDoc = await pdfjs.getDocument({ data: pdfData }).promise;
			if (token !== loadToken) return;
			pageCount = pdfDoc.numPages;
			if (onComments) {
				const doc = pdfDoc;
				void readPdfComments(doc, () => token !== loadToken)
					.then((result) => {
						if (token !== loadToken) return;
						comments = result.comments;
						onComments?.(result);
						onAnchors?.(comments.filter((c) => !c.parentId).map((c) => c.id));
						void renderCommentMarkers();
					})
					.catch(() => {
						if (token === loadToken) onCommentsError?.();
					});
			}
			activePage = clampDocumentTargetPage(targetPage, pageCount) ?? 1;
			targetPage = clampDocumentTargetPage(targetPage, pageCount) ?? 1;
			await renderAllPages();
		} catch (e) {
			if (token === loadToken) {
				console.error('PDF render error:', e);
				error = 'Failed to load PDF.';
				onCommentsError?.();
			}
		} finally {
			if (token === loadToken) loading = false;
		}
	};

	onMount(() => {
		mounted = true;
		resizeObserver = new ResizeObserver(([entry]) => {
			const { width, height } = entry.contentRect;
			if (width <= 0 || height <= 0 || (width === lastWidth && height === lastHeight)) return;
			lastWidth = width;
			lastHeight = height;
			clearTimeout(resizeTimer);
			resizeTimer = setTimeout(() => {
				if (!loading && pdfDoc) void renderAllPages();
			}, 100);
		});
		resizeObserver.observe(outerContainer.parentElement!);
	});

	$: if (mounted && (data || url)) {
		void loadPdf();
	}

	$: if (!loading && pdfDoc && singlePage && targetPage && selectedPage !== renderedPage) {
		void renderAllPages();
	}

	$: if (!loading && pdfDoc && !singlePage && targetPage) {
		void scrollToTargetPage();
	}

	$: if (sourceComments && pdfDoc) void mapSourceComments();

	$: if (selectedComment && !loading) void renderCommentMarkers();

	onDestroy(() => {
		markerToken++;
		resizeObserver?.disconnect();
		clearTimeout(resizeTimer);
		loadToken++;
		renderToken++;
		if (scrollFrame !== null) cancelAnimationFrame(scrollFrame);
		if (rerenderTimer) clearTimeout(rerenderTimer);
		pzInstance?.dispose();
		cancelTextLayers();
		if (pdfDoc) {
			pdfDoc.destroy();
			pdfDoc = null;
		}
	});
</script>

<div class="relative {className}">
	{#if loading}
		<div class="absolute inset-0 flex items-center justify-center">
			<Spinner className="size-5" />
		</div>
	{:else if error}
		<div class="absolute inset-0 flex items-center justify-center text-sm text-red-500">
			{error}
		</div>
	{/if}

	<div
		class={singlePage
			? 'overflow-hidden h-full flex items-center justify-center overscroll-contain'
			: 'overflow-y-auto h-full'}
		bind:this={outerContainer}
		role="application"
		aria-label={`${itemLabel} viewer`}
		tabindex="0"
		on:scroll={handleScroll}
		on:wheel|nonpassive={handleWheel}
		on:dblclick|capture|stopPropagation={() => {}}
		on:pointerdown={focusViewer}
		on:keydown={handleKeyDown}
	>
		<div bind:this={sceneElement} class={singlePage ? '' : 'w-full'}></div>
	</div>

	{#if !error && pdfDoc}
		<div
			class="absolute bottom-3 left-1/2 -translate-x-1/2 z-10 flex items-center gap-0.5 rounded-lg bg-white/90 dark:bg-gray-850/90 backdrop-blur-sm shadow-lg border border-gray-200/60 dark:border-gray-700/60 px-1 py-0.5"
		>
			{#if singlePage}
				<button
					type="button"
					class="shrink-0 min-w-7 h-7 inline-flex items-center justify-center p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500 dark:text-gray-400 disabled:opacity-30"
					disabled={selectedPage === 1}
					on:click={() => selectPage(selectedPage - 1)}
					aria-label={`Previous ${itemLabel.toLowerCase()}`}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="size-3.5"
					>
						<path
							fill-rule="evenodd"
							d="M11.78 5.22a.75.75 0 0 1 0 1.06L8.06 10l3.72 3.72a.75.75 0 1 1-1.06 1.06l-4.25-4.25a.75.75 0 0 1 0-1.06l4.25-4.25a.75.75 0 0 1 1.06 0Z"
							clip-rule="evenodd"
						/>
					</svg>
				</button>
				<span
					class="shrink-0 min-w-12 text-center text-[0.6875rem] text-gray-500 dark:text-gray-400 tabular-nums"
					>{selectedPage} / {pageCount}</span
				>
				<button
					type="button"
					class="shrink-0 min-w-7 h-7 inline-flex items-center justify-center p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500 dark:text-gray-400 disabled:opacity-30"
					disabled={selectedPage === pageCount}
					on:click={() => selectPage(selectedPage + 1)}
					aria-label={`Next ${itemLabel.toLowerCase()}`}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="size-3.5"
					>
						<path
							fill-rule="evenodd"
							d="M8.22 5.22a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06l-4.25 4.25a.75.75 0 0 1-1.06-1.06L11.94 10 8.22 6.28a.75.75 0 0 1 0-1.06Z"
							clip-rule="evenodd"
						/>
					</svg>
				</button>
			{/if}
			<!-- Pinch covers in/out on coarse pointers; reset has no gesture, so it stays -->
			<button
				type="button"
				class="shrink-0 min-w-7 h-7 inline-flex items-center justify-center p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500 dark:text-gray-400 pointer-coarse:hidden"
				on:click={zoomOut}
				aria-label={$i18n.t('Zoom out')}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="size-3.5"
				>
					<path
						fill-rule="evenodd"
						d="M4 10a.75.75 0 0 1 .75-.75h10.5a.75.75 0 0 1 0 1.5H4.75A.75.75 0 0 1 4 10Z"
						clip-rule="evenodd"
					/>
				</svg>
			</button>
			<button
				type="button"
				class="shrink-0 min-w-12 h-7 px-1.5 py-1 text-center text-[0.6875rem] font-normal text-gray-500 dark:text-gray-400 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition tabular-nums"
				on:click={resetView}
				aria-label={$i18n.t('Reset zoom')}
			>
				{Math.round(zoomLevel * 100)}%
			</button>
			<button
				type="button"
				class="shrink-0 min-w-7 h-7 inline-flex items-center justify-center p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500 dark:text-gray-400 pointer-coarse:hidden"
				on:click={zoomIn}
				aria-label={$i18n.t('Zoom in')}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="size-3.5"
				>
					<path
						d="M10.75 4.75a.75.75 0 0 0-1.5 0v4.5h-4.5a.75.75 0 0 0 0 1.5h4.5v4.5a.75.75 0 0 0 1.5 0v-4.5h4.5a.75.75 0 0 0 0-1.5h-4.5v-4.5Z"
					/>
				</svg>
			</button>
		</div>
	{/if}
</div>

<style>
	/*
	 * Minimal textLayer styles extracted from pdfjs-dist/web/pdf_viewer.css.
	 * These ensure the invisible text spans are positioned exactly over the
	 * rendered canvas so that browser-native Ctrl+F search and text selection
	 * work correctly.
	 */
	:global(.textLayer) {
		position: absolute;
		text-align: initial;
		inset: 0;
		overflow: clip;
		opacity: 1;
		line-height: 1;
		-webkit-text-size-adjust: none;
		-moz-text-size-adjust: none;
		text-size-adjust: none;
		forced-color-adjust: none;
		transform-origin: 0 0;
		caret-color: CanvasText;
		z-index: 0;
	}

	:global(.textLayer :is(span, br)) {
		color: transparent;
		position: absolute;
		white-space: pre;
		cursor: text;
		transform-origin: 0% 0%;
	}

	:global(.textLayer) {
		/* --total-scale-factor is derived from --scale-factor (set on the wrapper)
		   and --user-unit (defaults to 1). This mirrors the official pdf_viewer.css. */
		--user-unit: 1;
		--total-scale-factor: calc(var(--scale-factor) * var(--user-unit));
		--min-font-size: 1;
		--text-scale-factor: calc(var(--total-scale-factor) * var(--min-font-size));
		--min-font-size-inv: calc(1 / var(--min-font-size));
	}

	:global(.textLayer > :not(.markedContent)),
	:global(.textLayer .markedContent span:not(.markedContent)) {
		z-index: 1;
		--font-height: 0;
		font-size: calc(var(--text-scale-factor) * var(--font-height));
		--scale-x: 1;
		--rotate: 0deg;
		transform: rotate(var(--rotate)) scaleX(var(--scale-x)) scale(var(--min-font-size-inv));
	}

	:global(.textLayer .markedContent) {
		display: contents;
	}

	:global(.textLayer span[role='img']) {
		-webkit-user-select: none;
		-moz-user-select: none;
		user-select: none;
		cursor: default;
	}

	/* Selection highlight color */
	:global(.textLayer ::-moz-selection) {
		background: rgba(0, 0, 255, 0.25);
	}

	:global(.textLayer ::selection) {
		background: rgba(0, 0, 255, 0.25);
	}

	:global(.textLayer br::-moz-selection) {
		background: transparent;
	}

	:global(.textLayer br::selection) {
		background: transparent;
	}

	:global(.textLayer .endOfContent) {
		display: block;
		position: absolute;
		inset: 100% 0 0;
		z-index: 0;
		cursor: default;
		-webkit-user-select: none;
		-moz-user-select: none;
		user-select: none;
	}

	:global(.textLayer.selecting .endOfContent) {
		top: 0;
	}

	/* pdfjs leaves its text-measuring canvas in <body> at 300x150 for PDFs without text */
	:global(.hiddenCanvasElement) {
		display: none;
	}
</style>
