<script lang="ts">
	import MarkmapRenderer from '$lib/components/chat/Messages/MarkmapRenderer.svelte';
	import hljs from 'highlight.js';
	import { toast } from 'svelte-sonner';
	import { getContext, onMount, tick, onDestroy } from 'svelte';
	import { config } from '$lib/stores';

	import PyodideWorker from '$lib/workers/pyodide.worker?worker';
	import { executeCode } from '$lib/apis/utils';
	import { copyToClipboard, initMermaid, renderMermaidDiagram, renderVegaVisualization } from '$lib/utils';

	import 'highlight.js/styles/github-dark.min.css';

	import CodeEditor from '$lib/components/common/CodeEditor.svelte';
	import SvgPanZoom from '$lib/components/common/SVGPanZoom.svelte';

	import ChevronUpDown from '$lib/components/icons/ChevronUpDown.svelte';

	const i18n = getContext('i18n');

	export let id = '';
	export let edit = true;

	export let onSave = (e) => {};
	export let onUpdate = (e) => {};
	export let onPreview = (e) => {};

	export let save = false;
	export let run = true;
	export let preview = false;
	export let collapsed = false;

	export let token;
	export let lang = '';
	export let code = '';
	export let attributes = {};

	export let className = '';
	export let editorClassName = '';
	export let stickyButtonsClassName = 'top-0';

	let pyodideWorker = null;

	let _code = '';
	$: if (code) updateCode();
	const updateCode = () => {
		_code = code;
	};

	let _token = null;

	let renderHTML: string | null = null;
	let renderError: string | null = null;

	let executing = false;

	let stdout = null;
	let stderr = null;
	let result = null;
	let files = null;

	let copied = false;
	let saved = false;

	// ===== Markmap mode + export menu =====
	let markmapMode: 'code' | 'render' = 'render';
	let showExportMenu = false;
	let markmapRef: any = null;
    
	// ===== Diagram mode (Graphviz/PlantUML) align with Markmap UX =====
	let diagramMode: 'code' | 'render' = 'render';

	const normLang = () => ((lang ?? '').toLowerCase().trim().split(/\s+/)[0]);

	const isMarkmap = () => normLang() === 'markmap';

	const isGraphviz = () => ['dot', 'graphviz', 'gv'].includes(normLang());

	const isPlantUml = () => ['plantuml', 'puml', 'uml', 'pu'].includes(normLang());

	const isDiagram = () => isGraphviz() || isPlantUml();

	function closeExportMenu() {
		showExportMenu = false;
	}

	function downloadBlob(filename: string, blob: Blob) {
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = filename;
		a.click();
		URL.revokeObjectURL(url);
	}

	function downloadText(filename: string, text: string, mime = 'text/plain;charset=utf-8') {
		downloadBlob(filename, new Blob([text], { type: mime }));
	}

	function stripFences(text: string) {
		let t = (text ?? '').trim();
		t = t.replace(/^\s*```[^\n]*\n/i, '');
		t = t.replace(/\n\s*```\s*$/i, '');
		return t.trim();
	}

	// Mermaid 渲染前清洗：避免 LLM 输出把 <br> / HTML 混入 mermaid
	function sanitizeMermaid(src: string) {
		let s = src ?? '';
		s = s.replace(/<br\s*\/?>/gi, '\n');
		s = s.replace(/<\/?(div|span|p|b|i|em|strong|ul|ol|li|h\d)[^>]*>/gi, '');
		s = s.replace(/&nbsp;/gi, ' ');
		return s;
	}

	// Graphviz / PlantUML 也做轻量清洗（主要处理 <br>）
	function sanitizeDiagram(src: string) {
		let s = src ?? '';
		s = s.replace(/<br\s*\/?>/gi, '\n');
		s = s.replace(/&nbsp;/gi, ' ');
		return stripFences(s);
	}

	// SVG -> PNG（导出用）
	async function svgTextToPngBlob(svgText: string, scale = 2): Promise<Blob> {
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

	const collapseCodeBlock = () => {
		collapsed = !collapsed;
		closeExportMenu();
	};

	const saveCode = () => {
		saved = true;

		code = _code;
		onSave(code);

		setTimeout(() => {
			saved = false;
		}, 1000);
	};

	const copyCode = async () => {
		copied = true;
		await copyToClipboard(_code);

		setTimeout(() => {
			copied = false;
		}, 1000);
	};

	const previewCode = () => {
		onPreview(code);
	};

	const checkPythonCode = (str) => {
		const pythonSyntax = [
			'def ',
			'else:',
			'elif ',
			'try:',
			'except:',
			'finally:',
			'yield ',
			'lambda ',
			'assert ',
			'nonlocal ',
			'del ',
			'True',
			'False',
			'None',
			' and ',
			' or ',
			' not ',
			' in ',
			' is ',
			' with '
		];

		for (let syntax of pythonSyntax) {
			if (str.includes(syntax)) return true;
		}
		return false;
	};

	const executePython = async (code) => {
		result = null;
		stdout = null;
		stderr = null;

		executing = true;

		if ($config?.code?.engine === 'jupyter') {
			const output = await executeCode(localStorage.token, code).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (output) {
				if (output['stdout']) {
					stdout = output['stdout'];
					const stdoutLines = stdout.split('\n');

					for (const [idx, line] of stdoutLines.entries()) {
						if (line.startsWith('data:image/png;base64')) {
							if (files) {
								files.push({ type: 'image/png', data: line });
							} else {
								files = [{ type: 'image/png', data: line }];
							}

							if (stdout.includes(`${line}\n`)) stdout = stdout.replace(`${line}\n`, ``);
							else if (stdout.includes(`${line}`)) stdout = stdout.replace(`${line}`, ``);
						}
					}
				}

				if (output['result']) {
					result = output['result'];
					const resultLines = result.split('\n');

					for (const [idx, line] of resultLines.entries()) {
						if (line.startsWith('data:image/png;base64')) {
							if (files) files.push({ type: 'image/png', data: line });
							else files = [{ type: 'image/png', data: line }];

							if (result.includes(`${line}\n`)) result = result.replace(`${line}\n`, ``);
							else if (result.includes(`${line}`)) result = result.replace(`${line}`, ``);
						}
					}
				}

				output['stderr'] && (stderr = output['stderr']);
			}

			executing = false;
		} else {
			executePythonAsWorker(code);
		}
	};

	const executePythonAsWorker = async (code) => {
		let packages = [
			/\bimport\s+requests\b|\bfrom\s+requests\b/.test(code) ? 'requests' : null,
			/\bimport\s+bs4\b|\bfrom\s+bs4\b/.test(code) ? 'beautifulsoup4' : null,
			/\bimport\s+numpy\b|\bfrom\s+numpy\b/.test(code) ? 'numpy' : null,
			/\bimport\s+pandas\b|\bfrom\s+pandas\b/.test(code) ? 'pandas' : null,
			/\bimport\s+matplotlib\b|\bfrom\s+matplotlib\b/.test(code) ? 'matplotlib' : null,
			/\bimport\s+seaborn\b|\bfrom\s+seaborn\b/.test(code) ? 'seaborn' : null,
			/\bimport\s+sklearn\b|\bfrom\s+sklearn\b/.test(code) ? 'scikit-learn' : null,
			/\bimport\s+scipy\b|\bfrom\s+scipy\b/.test(code) ? 'scipy' : null,
			/\bimport\s+re\b|\bfrom\s+re\b/.test(code) ? 'regex' : null,
			/\bimport\s+sympy\b|\bfrom\s+sympy\b/.test(code) ? 'sympy' : null,
			/\bimport\s+tiktoken\b|\bfrom\s+tiktoken\b/.test(code) ? 'tiktoken' : null,
			/\bimport\s+pytz\b|\bfrom\s+pytz\b/.test(code) ? 'pytz' : null
		].filter(Boolean);

		pyodideWorker = new PyodideWorker();

		pyodideWorker.postMessage({
			id,
			code,
			packages
		});

		setTimeout(() => {
			if (executing) {
				executing = false;
				stderr = 'Execution Time Limit Exceeded';
				pyodideWorker.terminate();
			}
		}, 60000);

		pyodideWorker.onmessage = (event) => {
			const { id, ...data } = event.data;

			if (data['stdout']) stdout = data['stdout'];
			if (data['result']) result = data['result'];
			data['stderr'] && (stderr = data['stderr']);

			executing = false;
		};

		pyodideWorker.onerror = () => {
			executing = false;
		};
	};

	let mermaid = null;
	const renderMermaid = async (code) => {
		if (!mermaid) mermaid = await initMermaid();
		return await renderMermaidDiagram(mermaid, sanitizeMermaid(code));
	};

	// ===== Graphviz renderer (dot -> svg) =====
	let _gv: any = null;

	async function renderGraphviz(dotText: string): Promise<string> {
	  if (!_gv) {
	    const mod: any = await import('@hpcc-js/wasm/graphviz');
	    const Graphviz = mod.Graphviz;
	    if (!Graphviz?.load) {
	      throw new Error('Graphviz WASM not available (check @hpcc-js/wasm install/import)');
	    }
	    _gv = await Graphviz.load();
	  }
	  const src = sanitizeDiagram(dotText);
	  return await _gv.layout(src, 'svg', 'dot');
	}

	// ===== PlantUML renderer (text -> fetch svg) =====
	function getPlantUmlServer(): string {
		const v = (globalThis?.localStorage?.getItem('PLANTUML_SERVER') ?? '').trim();
		return v || 'https://www.plantuml.com/plantuml';
	}

	function normalizePlantUmlSource(src: string): string {
		const s = sanitizeDiagram(src);
		// 如果用户已经写了 @start.../@end...，原样使用
		if (/@start\w+/i.test(s)) return s;

		// 否则：默认按 mindmap 包一层（你要 WBS 就请显式写 @startwbs/@endwbs）
		return `@startmindmap\n${s}\n@endmindmap`;
	}

	async function renderPlantUmlSvg(pumlText: string): Promise<string> {
		const server = getPlantUmlServer().replace(/\/+$/, '');
		const src = normalizePlantUmlSource(pumlText);

		const encMod: any = await import('plantuml-encoder');
		const encoded = encMod.encode(src);

		const url = `${server}/svg/${encoded}`;
		const resp = await fetch(url, { method: 'GET' });
		if (!resp.ok) throw new Error(`PlantUML server error: ${resp.status}`);
		return await resp.text();
	}

	async function fetchPlantUmlPng(pumlText: string): Promise<Blob> {
		const server = getPlantUmlServer().replace(/\/+$/, '');
		const src = normalizePlantUmlSource(pumlText);

		const encMod: any = await import('plantuml-encoder');
		const encoded = encMod.encode(src);

		const url = `${server}/png/${encoded}`;
		const resp = await fetch(url, { method: 'GET' });
		if (!resp.ok) throw new Error(`PlantUML server error: ${resp.status}`);
		return await resp.blob();
	}

	const render = async () => {
		onUpdate(token);

		// Mermaid
		if (lang === 'mermaid' && (token?.raw ?? '').slice(-4).includes('```')) {
			try {
				renderHTML = await renderMermaid(code);
				renderError = null;
			} catch (error) {
				const errorMsg = error instanceof Error ? error.message : String(error);
				renderError = $i18n.t('Failed to render diagram') + `: ${errorMsg}`;
				renderHTML = null;
			}
		}
		// Vega/Vega-lite
		else if ((lang === 'vega' || lang === 'vega-lite') && (token?.raw ?? '').slice(-4).includes('```')) {
			try {
				renderHTML = await renderVegaVisualization(code);
				renderError = null;
			} catch (error) {
				const errorMsg = error instanceof Error ? error.message : String(error);
				renderError = $i18n.t('Failed to render visualization') + `: ${errorMsg}`;
				renderHTML = null;
			}
		}
		// Graphviz / PlantUML: only render when in "render" mode
		else if (isDiagram() && diagramMode === 'render' && (token?.raw ?? '').slice(-4).includes('```')) {
			try {
				if (isGraphviz()) {
					renderHTML = await renderGraphviz(code);
				} else {
					renderHTML = await renderPlantUmlSvg(code);
				}
				renderError = null;
			} catch (error) {
				const errorMsg = error instanceof Error ? error.message : String(error);
				renderError = $i18n.t('Failed to render diagram') + `: ${errorMsg}`;
				renderHTML = null;
			}
		}
	};

	$: if (token && JSON.stringify(token) !== JSON.stringify(_token)) {
		_token = token;
	}

	$: if (_token) {
		render();
	}

	// diagramMode 切回 render 时，立即触发一次渲染
	$: if (_token && isDiagram() && diagramMode === 'render') {
		render();
	}

	$: if (attributes) {
		onAttributesUpdate();
	}

	const onAttributesUpdate = () => {
		if (attributes?.output) {
			const unescapeHtml = (html) => {
				const textArea = document.createElement('textarea');
				textArea.innerHTML = html;
				return textArea.value;
			};

			try {
				const unescapedOutput = unescapeHtml(attributes.output);
				const output = JSON.parse(unescapedOutput);
				stdout = output.stdout;
				stderr = output.stderr;
				result = output.result;
			} catch {}
		}
	};

	onMount(() => {
		if (token) onUpdate(token);

		// 点击空白处关闭导出菜单
		const onDocClick = (e: MouseEvent) => {
			if (!showExportMenu) return;
			const target = e.target as HTMLElement;
			if (!target?.closest?.(`[data-export-menu="${id}"]`)) {
				showExportMenu = false;
			}
		};
		document.addEventListener('click', onDocClick);

		return () => document.removeEventListener('click', onDocClick);
	});

	onDestroy(() => {
		if (pyodideWorker) pyodideWorker.terminate();
	});

	async function exportMermaidOrVegaSvg() {
		if (!renderHTML) return;
		downloadText(`${lang}.svg`, renderHTML, 'image/svg+xml;charset=utf-8');
	}

	async function exportMermaidOrVegaPng() {
		if (!renderHTML) return;
		const png = await svgTextToPngBlob(renderHTML, 2);
		downloadBlob(`${lang}.png`, png);
	}

	async function exportDiagramSvg() {
		if (!renderHTML) return;
		const name = isGraphviz() ? 'graphviz' : 'plantuml';
		downloadText(`${name}.svg`, renderHTML, 'image/svg+xml;charset=utf-8');
	}

	async function exportDiagramPng() {
		if (isPlantUml()) {
			// PlantUML：优先直接从 server 拉 PNG（避免 SVG->PNG 的字体/外链差异）
			const blob = await fetchPlantUmlPng(_code);
			downloadBlob('plantuml.png', blob);
			return;
		}
		// Graphviz：SVG 转 PNG
		if (!renderHTML) return;
		const png = await svgTextToPngBlob(renderHTML, 2);
		downloadBlob('graphviz.png', png);
	}
</script>

<div>
	<div class="relative {className} flex flex-col rounded-3xl border border-gray-100/30 dark:border-gray-850/30 my-0.5" dir="ltr">
		{#if ['mermaid', 'vega', 'vega-lite'].includes(lang)}
			{#if renderHTML}
				<div class="sticky {stickyButtonsClassName} left-0 right-0 py-2 pr-3 flex items-center justify-end w-full z-10 text-xs text-black dark:text-white">
					<div class="flex items-center gap-1" data-export-menu={id}>
						<button
							class="flex gap-1 items-center border-none transition rounded-md px-2 py-0.5 bg-white dark:bg-black"
							on:click|stopPropagation={() => (showExportMenu = !showExportMenu)}
						>
							导出
						</button>

						{#if showExportMenu}
							<div class="absolute right-3 mt-9 w-28 rounded-xl border border-gray-200/60 dark:border-gray-800/60 bg-white dark:bg-black shadow-lg p-1">
								<button class="w-full text-left px-2 py-1 text-xs rounded-lg hover:bg-gray-100 dark:hover:bg-gray-900" on:click={() => { exportMermaidOrVegaSvg(); closeExportMenu(); }}>
									SVG
								</button>
								<button class="w-full text-left px-2 py-1 text-xs rounded-lg hover:bg-gray-100 dark:hover:bg-gray-900" on:click={() => { exportMermaidOrVegaPng(); closeExportMenu(); }}>
									PNG
								</button>
							</div>
						{/if}
					</div>
				</div>

				<SvgPanZoom className="rounded-3xl max-h-fit overflow-hidden" svg={renderHTML} content={_token.text} />
			{:else}
				<div class="p-3">
					{#if renderError}
						<div class="flex gap-2.5 border px-4 py-3 border-red-600/10 bg-red-600/10 rounded-2xl mb-2">{renderError}</div>
					{/if}
					<pre>{code}</pre>
				</div>
			{/if}
		{:else}
			<div class="absolute left-0 right-0 py-2.5 pr-3 text-text-300 pl-4.5 text-xs font-medium dark:text-white">
				{lang}
			</div>

			<div class="sticky {stickyButtonsClassName} left-0 right-0 py-2 pr-3 flex items-center justify-end w-full z-10 text-xs text-black dark:text-white">
				<div class="flex items-center gap-0.5" data-export-menu={id}>
					{#if isMarkmap() || isDiagram()}
						<button
							class="flex gap-1 items-center border-none transition rounded-md px-2 py-0.5 bg-white dark:bg-black"
							on:click|stopPropagation={() => (showExportMenu = !showExportMenu)}
						>
							导出
						</button>

						{#if showExportMenu}
							<div class="absolute right-3 mt-9 w-36 rounded-xl border border-gray-200/60 dark:border-gray-800/60 bg-white dark:bg-black shadow-lg p-1">
								{#if isMarkmap()}
									<button
										class="w-full text-left px-2 py-1 text-xs rounded-lg hover:bg-gray-100 dark:hover:bg-gray-900"
										on:click={async () => {
											if (markmapMode !== 'render') markmapMode = 'render';
											await tick();
											const svg = markmapRef?.exportSvg?.();
											if (svg) downloadText('markmap.svg', svg, 'image/svg+xml;charset=utf-8');
											closeExportMenu();
										}}
									>
										导出 SVG
									</button>

									<button
										class="w-full text-left px-2 py-1 text-xs rounded-lg hover:bg-gray-100 dark:hover:bg-gray-900"
										on:click={async () => {
											if (markmapMode !== 'render') markmapMode = 'render';
											await tick();
											const png = await markmapRef?.exportPng?.(2);
											if (png) downloadBlob('markmap.png', png);
											closeExportMenu();
										}}
									>
										导出 PNG
									</button>

									<button
										class="w-full text-left px-2 py-1 text-xs rounded-lg hover:bg-gray-100 dark:hover:bg-gray-900"
										on:click={() => {
											const html = markmapRef?.exportHtml?.() ?? '';
											if (html) downloadText('markmap.html', html, 'text/html;charset=utf-8');
											closeExportMenu();
										}}
									>
										导出 HTML
									</button>
								{:else}
									<button
										class="w-full text-left px-2 py-1 text-xs rounded-lg hover:bg-gray-100 dark:hover:bg-gray-900"
										on:click={async () => {
											if (diagramMode !== 'render') diagramMode = 'render';
											await tick();
											await exportDiagramSvg();
											closeExportMenu();
										}}
									>
										导出 SVG
									</button>

									<button
										class="w-full text-left px-2 py-1 text-xs rounded-lg hover:bg-gray-100 dark:hover:bg-gray-900"
										on:click={async () => {
											if (diagramMode !== 'render') diagramMode = 'render';
											await tick();
											await exportDiagramPng();
											closeExportMenu();
										}}
									>
										导出 PNG
									</button>
								{/if}
							</div>
						{/if}
					{/if}

					<button
						class="flex gap-1 items-center bg-none border-none transition rounded-md px-1.5 py-0.5 bg-white dark:bg-black"
						on:click={collapseCodeBlock}
					>
						<div class="-translate-y-[0.5px]">
							<ChevronUpDown className="size-3" />
						</div>
						<div>{collapsed ? $i18n.t('Expand') : $i18n.t('Collapse')}</div>
					</button>

					{#if ($config?.features?.enable_code_execution ?? true) &&
					(lang.toLowerCase() === 'python' || lang.toLowerCase() === 'py' || (lang === '' && checkPythonCode(code)))}
						{#if executing}
							<div class="run-code-button bg-none border-none p-0.5 cursor-not-allowed bg-white dark:bg-black">
								{$i18n.t('Running')}
							</div>
						{:else if run}
							<button
								class="flex gap-1 items-center run-code-button bg-none border-none transition rounded-md px-1.5 py-0.5 bg-white dark:bg-black"
								on:click={async () => {
									code = _code;
									await tick();
									executePython(code);
								}}
							>
								<div>{$i18n.t('Run')}</div>
							</button>
						{/if}
					{/if}

					{#if save}
						<button class="save-code-button bg-none border-none transition rounded-md px-1.5 py-0.5 bg-white dark:bg-black" on:click={saveCode}>
							{saved ? $i18n.t('Saved') : $i18n.t('Save')}
						</button>
					{/if}

					<button class="copy-code-button bg-none border-none transition rounded-md px-1.5 py-0.5 bg-white dark:bg-black" on:click={copyCode}>
						{copied ? $i18n.t('Copied') : $i18n.t('Copy')}
					</button>

					{#if isMarkmap()}
						<button
							class="bg-none border-none transition rounded-md px-1.5 py-0.5 bg-white dark:bg-black"
							on:click={() => (markmapMode = markmapMode === 'code' ? 'render' : 'code')}
						>
							{markmapMode === 'code' ? '预览' : '代码'}
						</button>
					{/if}

					{#if isDiagram()}
						<button
							class="bg-none border-none transition rounded-md px-1.5 py-0.5 bg-white dark:bg-black"
							on:click={() => (diagramMode = diagramMode === 'code' ? 'render' : 'code')}
						>
							{diagramMode === 'code' ? '预览' : '代码'}
						</button>
					{/if}

					{#if preview && ['html', 'svg'].includes(lang)}
						<button
							class="flex gap-1 items-center run-code-button bg-none border-none transition rounded-md px-1.5 py-0.5 bg-white dark:bg-black"
							on:click={previewCode}
						>
							<div>{$i18n.t('Preview')}</div>
						</button>
					{/if}
				</div>
			</div>

			<div
				class="language-{lang} rounded-t-3xl -mt-9 {editorClassName
					? editorClassName
					: executing || stdout || stderr || result
						? ''
						: 'rounded-b-3xl'} overflow-hidden"
			>
				<div class="pt-8 bg-white dark:bg-black"></div>

				{#if !collapsed}
					{#if isMarkmap() && markmapMode === 'render'}
						<div class="p-3">
							<MarkmapRenderer bind:this={markmapRef} markdown={_code} />
						</div>
					{:else if isDiagram() && diagramMode === 'render'}
						<div class="p-3">
							{#if renderHTML}
								<SvgPanZoom className="rounded-3xl max-h-fit overflow-hidden" svg={renderHTML} content={_token?.text} />
							{:else}
								{#if renderError}
									<div class="flex gap-2.5 border px-4 py-3 border-red-600/10 bg-red-600/10 rounded-2xl mb-2">{renderError}</div>
								{/if}
								<pre class="text-xs opacity-80">（切到“预览”后将自动渲染）</pre>
							{/if}
						</div>
					{:else}
						{#if edit}
							<CodeEditor
								value={code}
								{id}
								{lang}
								onSave={() => saveCode()}
								onChange={(value) => {
									_code = value;
								}}
							/>
						{:else}
							<pre
								class="hljs p-4 px-5 overflow-x-auto"
								style="border-top-left-radius: 0px; border-top-right-radius: 0px; {(executing ||
									stdout ||
									stderr ||
									result) &&
									'border-bottom-left-radius: 0px; border-bottom-right-radius: 0px;'}"
							>
<code class="language-{lang} rounded-t-none whitespace-pre text-sm">
{@html hljs.highlightAuto(code, hljs.getLanguage(lang)?.aliases).value || code}
</code>
							</pre>
						{/if}
					{/if}
				{:else}
					<div class="bg-white dark:bg-black dark:text-white rounded-b-3xl! pt-0.5 pb-3 px-4 flex flex-col gap-2 text-xs">
						<span class="text-gray-500 italic">
							{$i18n.t('{{COUNT}} hidden lines', { COUNT: code.split('\n').length })}
						</span>
					</div>
				{/if}
			</div>

			{#if !collapsed}
				<div id="plt-canvas-{id}" class="bg-gray-50 dark:bg-black dark:text-white max-w-full overflow-x-auto scrollbar-hidden"></div>

				{#if executing || stdout || stderr || result || files}
					<div class="bg-gray-50 dark:bg-black dark:text-white rounded-b-3xl! py-4 px-4 flex flex-col gap-2">
						{#if executing}
							<div>
								<div class="text-gray-500 text-sm mb-1">{$i18n.t('STDOUT/STDERR')}</div>
								<div class="text-sm">{$i18n.t('Running...')}</div>
							</div>
						{:else}
							{#if stdout || stderr}
								<div>
									<div class="text-gray-500 text-sm mb-1">{$i18n.t('STDOUT/STDERR')}</div>
									<div class="text-sm font-mono whitespace-pre-wrap {stdout?.split('\n')?.length > 100 ? `max-h-96` : ''} overflow-y-auto">
										{stdout || stderr}
									</div>
								</div>
							{/if}
							{#if result || files}
								<div>
									<div class="text-gray-500 text-sm mb-1">{$i18n.t('RESULT')}</div>
									{#if result}
										<div class="text-sm">{`${JSON.stringify(result)}`}</div>
									{/if}
									{#if files}
										<div class="flex flex-col gap-2">
											{#each files as file}
												{#if file.type.startsWith('image')}
													<img src={file.data} alt="Output" class="w-full max-w-[36rem]" />
												{/if}
											{/each}
										</div>
									{/if}
								</div>
							{/if}
						{/if}
					</div>
				{/if}
			{/if}
		{/if}
	</div>
</div>


