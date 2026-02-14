<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { browser } from '$app/environment';

	export let markdown = '';
	export let className = '';

	let svgEl: SVGSVGElement | null = null;

	let mm: any = null;
	let Transformer: any;
	let Markmap: any;
	let loadCSS: any;
	let loadJS: any;
	let markmapModule: any;
	let transformer: any;

	let _lastRenderedMd = '';
	let _rendering = false;
	let _pending = false;
	let _destroyed = false;

	async function ensureLibs() {
		if (!browser) return;
		if (Transformer && Markmap && transformer) return;

		const lib = await import('markmap-lib');
		({ Transformer } = lib);

		const view = await import('markmap-view');
		({ Markmap, loadCSS, loadJS } = view);
		markmapModule = view;

		transformer = new Transformer(); // 默认内置插件（含 frontmatter 等）
	}

	function stripFences(text: string) {
		let t = (text ?? '').trim();
		t = t.replace(/^\s*```(?:markdown|md|markmap)?\s*\n/i, '');
		t = t.replace(/\n\s*```\s*$/i, '');
		return t.trim();
	}

	function sanitize(md: string) {
		// 防御性处理：避免有人把 <script> 混进 markdown（即使在代码块里也不该执行）
		return (md || '').replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, '');
	}

	async function render() {
		if (!browser || !svgEl) return;
		if (_rendering) {
			_pending = true;
			return;
		}

		_rendering = true;
		_pending = false;

		const mdRaw = markdown;
		_lastRenderedMd = mdRaw;

		try {
			await ensureLibs();
			if (_destroyed || !transformer || !Markmap || !svgEl) return;

			const md = sanitize(stripFences(mdRaw));

			// 1) transform
			const { root, features } = transformer.transform(md);

			// 2) assets（兼容 frontmatter / katex / prism 等扩展）
			const assets = transformer.getUsedAssets(features);
			if (assets?.styles?.length) loadCSS(assets.styles);
			if (assets?.scripts?.length) {
				await loadJS(assets.scripts, { getMarkmap: () => markmapModule });
			}

			// 3) render / update
			if (mm?.setData) {
				mm.setData(root);
			} else {
				try {
					mm?.destroy?.();
				} catch {}
				mm = Markmap.create(svgEl, { zoom: true, pan: true, duration: 200 }, root);
			}

			// fit
			try {
				mm?.fit?.();
			} catch {}
		} finally {
			_rendering = false;
			if (!_destroyed && _pending && markdown !== _lastRenderedMd) {
				render();
			}
		}
	}

	function serializeSvg() {
		if (!svgEl) return null;
		if (!svgEl.getAttribute('xmlns')) svgEl.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
		return new XMLSerializer().serializeToString(svgEl);
	}

	async function svgToPngBlob(svgText: string, scale = 2): Promise<Blob> {
		const svgBlob = new Blob([svgText], { type: 'image/svg+xml;charset=utf-8' });
		const url = URL.createObjectURL(svgBlob);

		const img = new Image();
		img.decoding = 'async';

		await new Promise<void>((resolve, reject) => {
			img.onload = () => resolve();
			img.onerror = () => reject(new Error('Failed to load SVG image'));
			img.src = url;
		});

		URL.revokeObjectURL(url);

		// 尽量从 viewBox 推宽高
		let w = 1200;
		let h = 800;
		try {
			const doc = new DOMParser().parseFromString(svgText, 'image/svg+xml');
			const svg = doc.documentElement as unknown as SVGSVGElement;
			const vb = svg.getAttribute('viewBox');
			if (vb) {
				const parts = vb.split(/\s+/).map((x) => parseFloat(x));
				if (parts.length === 4 && parts.every((n) => Number.isFinite(n))) {
					w = parts[2] || w;
					h = parts[3] || h;
				}
			}
			const aw = parseFloat(svg.getAttribute('width') || '');
			const ah = parseFloat(svg.getAttribute('height') || '');
			if (Number.isFinite(aw) && aw > 0) w = aw;
			if (Number.isFinite(ah) && ah > 0) h = ah;
		} catch {}

		const canvas = document.createElement('canvas');
		canvas.width = Math.round(w * scale);
		canvas.height = Math.round(h * scale);

		const ctx = canvas.getContext('2d');
		if (!ctx) throw new Error('Canvas 2D context not available');
		ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

		const pngBlob: Blob = await new Promise((resolve, reject) => {
			canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('Failed to create PNG blob'))), 'image/png');
		});

		return pngBlob;
	}

	function buildStandaloneHtml(md: string) {
		const safe = (md ?? '').replace(/<\/script>/gi, '<\\/script>');
		return `<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Markmap</title>
<style>
html,body{margin:0;height:100%;font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial}
.markmap>svg{width:100%;height:90vh;min-height:720px;}
</style>
<script>window.markmap={autoLoader:{toolbar:true}};<\\/script>
<script src="https://cdn.jsdelivr.net/npm/markmap-autoloader@0.16.1"
 onerror="this.onerror=null;this.src='https://unpkg.com/markmap-autoloader@0.16.1'"><\\/script>
</head>
<body>
<div class="markmap"><script type="text/template">\n${safe}\n<\\/script></div>
</body>
</html>`;
	}

	// ====== exported APIs for parent ======
	export function exportSvg(): string | null {
		return serializeSvg();
	}
	export async function exportPng(scale = 2): Promise<Blob | null> {
		const svg = serializeSvg();
		if (!svg) return null;
		return await svgToPngBlob(svg, scale);
	}
	export function exportHtml(): string {
		return buildStandaloneHtml(sanitize(stripFences(markdown)));
	}

	onMount(() => {
		render();
	});

	$: if (browser && svgEl && markdown !== _lastRenderedMd) {
		render();
	}

	onDestroy(() => {
		_destroyed = true;
		try {
			mm?.destroy?.();
		} catch {}
	});
</script>

<div
	class={
		'w-full rounded-2xl border border-gray-200/30 dark:border-gray-700/60 ' +
		'bg-white dark:bg-black shadow-sm overflow-hidden ' +
		className
	}
>
	<div class="flex items-center justify-between px-3 py-2 text-xs border-b border-gray-200/20 dark:border-gray-700/40">
		<div class="opacity-80">Markmap 预览</div>
		<div class="opacity-60">拖拽移动 · 滚轮缩放</div>
	</div>
	<div class="w-full h-[70vh] min-h-[520px] p-2">
		<svg bind:this={svgEl} class="w-full h-full"></svg>
	</div>
</div>
