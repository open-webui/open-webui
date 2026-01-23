<script lang="ts">
	import hljs from 'highlight.js';
	import { toast } from 'svelte-sonner';
	import { getContext, onMount, tick, onDestroy } from 'svelte';
	import { config } from '$lib/stores';

	import PyodideWorker from '$lib/workers/pyodide.worker?worker';
	import { executeCode } from '$lib/apis/utils';
	import {
		copyToClipboard,
		initMermaid,
		renderMermaidDiagram,
		renderVegaVisualization
	} from '$lib/utils';

	import 'highlight.js/styles/github-dark.min.css';

	import CodeEditor from '$lib/components/common/CodeEditor.svelte';
	import SvgPanZoom from '$lib/components/common/SVGPanZoom.svelte';

	import ChevronUpDown from '$lib/components/icons/ChevronUpDown.svelte';
	import CommandLine from '$lib/components/icons/CommandLine.svelte';

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
	$: if (code) {
		updateCode();
	}

	const updateCode = () => {
		_code = code;
	};

	let _token = null;

	let renderHTML = null;
	let renderError = null;

	let highlightedCode = null;
	let executing = false;

	let stdout = null;
	let stderr = null;
	let result = null;
	let files = null;

	let copied = false;
	let saved = false;

	const collapseCodeBlock = () => {
		collapsed = !collapsed;
	};

	const getLangAccentClass = (language) => {
		const normalized = (language || '').toLowerCase();

		if (['js', 'javascript', 'ts', 'typescript'].includes(normalized)) {
			return 'bg-amber-400 dark:bg-amber-500';
		}
		if (['py', 'python'].includes(normalized)) {
			return 'bg-blue-500 dark:bg-blue-400';
		}
		if (['html', 'xml', 'svg'].includes(normalized)) {
			return 'bg-orange-500 dark:bg-orange-400';
		}
		if (['css', 'scss', 'sass', 'less'].includes(normalized)) {
			return 'bg-cyan-500 dark:bg-cyan-400';
		}
		if (['json', 'yaml', 'yml', 'toml'].includes(normalized)) {
			return 'bg-slate-400 dark:bg-slate-500';
		}
		if (['bash', 'sh', 'shell', 'zsh'].includes(normalized)) {
			return 'bg-emerald-500 dark:bg-emerald-400';
		}
		if (['sql'].includes(normalized)) {
			return 'bg-violet-500 dark:bg-violet-400';
		}

		return 'bg-gray-300 dark:bg-gray-600';
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
		// Check if the string contains typical Python syntax characters
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
			if (str.includes(syntax)) {
				return true;
			}
		}

		// If none of the above conditions met, it's probably not Python code
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
								files.push({
									type: 'image/png',
									data: line
								});
							} else {
								files = [
									{
										type: 'image/png',
										data: line
									}
								];
							}

							if (stdout.includes(`${line}\n`)) {
								stdout = stdout.replace(`${line}\n`, ``);
							} else if (stdout.includes(`${line}`)) {
								stdout = stdout.replace(`${line}`, ``);
							}
						}
					}
				}

				if (output['result']) {
					result = output['result'];
					const resultLines = result.split('\n');

					for (const [idx, line] of resultLines.entries()) {
						if (line.startsWith('data:image/png;base64')) {
							if (files) {
								files.push({
									type: 'image/png',
									data: line
								});
							} else {
								files = [
									{
										type: 'image/png',
										data: line
									}
								];
							}

							if (result.includes(`${line}\n`)) {
								result = result.replace(`${line}\n`, ``);
							} else if (result.includes(`${line}`)) {
								result = result.replace(`${line}`, ``);
							}
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
			/\bimport\s+seaborn\b|\bfrom\s+seaborn\b/.test(code) ? 'seaborn' : null,
			/\bimport\s+sympy\b|\bfrom\s+sympy\b/.test(code) ? 'sympy' : null,
			/\bimport\s+tiktoken\b|\bfrom\s+tiktoken\b/.test(code) ? 'tiktoken' : null,
			/\bimport\s+pytz\b|\bfrom\s+pytz\b/.test(code) ? 'pytz' : null
		].filter(Boolean);

		console.log(packages);

		pyodideWorker = new PyodideWorker();

		pyodideWorker.postMessage({
			id: id,
			code: code,
			packages: packages
		});

		setTimeout(() => {
			if (executing) {
				executing = false;
				stderr = 'Execution Time Limit Exceeded';
				pyodideWorker.terminate();
			}
		}, 60000);

		pyodideWorker.onmessage = (event) => {
			console.log('pyodideWorker.onmessage', event);
			const { id, ...data } = event.data;

			console.log(id, data);

			if (data['stdout']) {
				stdout = data['stdout'];
				const stdoutLines = stdout.split('\n');

				for (const [idx, line] of stdoutLines.entries()) {
					if (line.startsWith('data:image/png;base64')) {
						if (files) {
							files.push({
								type: 'image/png',
								data: line
							});
						} else {
							files = [
								{
									type: 'image/png',
									data: line
								}
							];
						}

						if (stdout.includes(`${line}\n`)) {
							stdout = stdout.replace(`${line}\n`, ``);
						} else if (stdout.includes(`${line}`)) {
							stdout = stdout.replace(`${line}`, ``);
						}
					}
				}
			}

			if (data['result']) {
				result = data['result'];
				const resultLines = result.split('\n');

				for (const [idx, line] of resultLines.entries()) {
					if (line.startsWith('data:image/png;base64')) {
						if (files) {
							files.push({
								type: 'image/png',
								data: line
							});
						} else {
							files = [
								{
									type: 'image/png',
									data: line
								}
							];
						}

						if (result.startsWith(`${line}\n`)) {
							result = result.replace(`${line}\n`, ``);
						} else if (result.startsWith(`${line}`)) {
							result = result.replace(`${line}`, ``);
						}
					}
				}
			}

			data['stderr'] && (stderr = data['stderr']);
			data['result'] && (result = data['result']);

			executing = false;
		};

		pyodideWorker.onerror = (event) => {
			console.log('pyodideWorker.onerror', event);
			executing = false;
		};
	};

	let mermaid = null;
	const renderMermaid = async (code) => {
		if (!mermaid) {
			mermaid = await initMermaid();
		}
		return await renderMermaidDiagram(mermaid, code);
	};

	const render = async () => {
		onUpdate(token);
		if (lang === 'mermaid' && (token?.raw ?? '').slice(-4).includes('```')) {
			try {
				renderHTML = await renderMermaid(code);
			} catch (error) {
				console.error('Failed to render mermaid diagram:', error);
				const errorMsg = error instanceof Error ? error.message : String(error);
				renderError = $i18n.t('Failed to render diagram') + `: ${errorMsg}`;
				renderHTML = null;
			}
		} else if (
			(lang === 'vega' || lang === 'vega-lite') &&
			(token?.raw ?? '').slice(-4).includes('```')
		) {
			try {
				renderHTML = await renderVegaVisualization(code);
			} catch (error) {
				console.error('Failed to render Vega visualization:', error);
				const errorMsg = error instanceof Error ? error.message : String(error);
				renderError = $i18n.t('Failed to render visualization') + `: ${errorMsg}`;
				renderHTML = null;
			}
		}
	};

	$: if (token) {
		if (JSON.stringify(token) !== JSON.stringify(_token)) {
			_token = token;
		}
	}

	$: if (_token) {
		render();
	}

	$: if (attributes) {
		onAttributesUpdate();
	}

	const onAttributesUpdate = () => {
		if (attributes?.output) {
			// Create a helper function to unescape HTML entities
			const unescapeHtml = (html) => {
				const textArea = document.createElement('textarea');
				textArea.innerHTML = html;
				return textArea.value;
			};

			try {
				// Unescape the HTML-encoded string
				const unescapedOutput = unescapeHtml(attributes.output);

				// Parse the unescaped string into JSON
				const output = JSON.parse(unescapedOutput);

				// Assign the parsed values to variables
				stdout = output.stdout;
				stderr = output.stderr;
				result = output.result;
			} catch (error) {
				console.error('Error:', error);
			}
		}
	};

	onMount(async () => {
		if (token) {
			onUpdate(token);
		}
	});

	onDestroy(() => {
		if (pyodideWorker) {
			pyodideWorker.terminate();
		}
	});
</script>

	<div>
		<div
		class="relative {className} flex flex-col rounded-2xl border border-gray-200/70 dark:border-gray-800/80 bg-white/90 dark:bg-gray-950/90 my-2 shadow-md dark:shadow-none overflow-hidden"
		dir="ltr"
	>
		<!-- Removed original wide sidebar -->

		{#if ['mermaid', 'vega', 'vega-lite'].includes(lang)}
			{#if renderHTML}
				<SvgPanZoom
					className="max-h-fit overflow-hidden bg-white dark:bg-gray-950"
					svg={renderHTML}
					content={_token.text}
				/>
			{:else}
				<div class="p-4 bg-white dark:bg-gray-950">
					{#if renderError}
						<div
							class="flex gap-2.5 border px-4 py-3 border-red-200 dark:border-red-900/50 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-lg mb-2 text-sm"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="size-5 flex-shrink-0"
							>
								<path
									fill-rule="evenodd"
									d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0Zm-8-5a.75.75 0 0 1 .75.75v4.5a.75.75 0 0 1-1.5 0v-4.5A.75.75 0 0 1 10 5Zm0 10a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
									clip-rule="evenodd"
								/>
							</svg>
							{renderError}
						</div>
					{/if}
					<pre
						class="text-sm text-gray-700 dark:text-gray-300 font-mono">{code}</pre>
				</div>
			{/if}
		{:else}
			<div
				class="group absolute left-0 right-0 z-10 flex items-center justify-between px-4 py-2 min-h-[40px] bg-gradient-to-b from-white/90 via-white/85 to-white/75 dark:from-gray-950/90 dark:via-gray-950/80 dark:to-gray-950/70 text-gray-600 dark:text-gray-300 border-b border-white/70 dark:border-gray-900/70 backdrop-blur-xl transition-colors"
			>
				<div class="flex items-center gap-3">
					<div class="flex items-center gap-1.5" aria-hidden="true">
						<span class="h-2.5 w-2.5 rounded-full bg-red-400 ring-1 ring-black/10"></span>
						<span class="h-2.5 w-2.5 rounded-full bg-amber-400 ring-1 ring-black/10"></span>
						<span class="h-2.5 w-2.5 rounded-full bg-emerald-400 ring-1 ring-black/10"></span>
					</div>
					<span
						class="inline-flex items-center gap-1.5 text-xs font-semibold tracking-wide font-mono text-gray-600 dark:text-gray-300"
					>
						<CommandLine className="size-3.5" />
						<span class="capitalize">{lang || 'Code'}</span>
					</span>
				</div>
				<div
					class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200"
				>
					{#if ($config?.features?.enable_code_execution ?? true) && (lang.toLowerCase() === 'python' || lang.toLowerCase() === 'py' || (lang === '' && checkPythonCode(code)))}
						{#if executing}
							<div
								class="inline-flex items-center gap-1 text-xs font-medium text-gray-500 dark:text-gray-300 px-2 py-1 rounded-full bg-white/70 dark:bg-gray-900/50 ring-1 ring-black/5 dark:ring-white/10"
							>
								<svg
									class="animate-spin size-3"
									xmlns="http://www.w3.org/2000/svg"
									fill="none"
									viewBox="0 0 24 24"
								>
									<circle
										class="opacity-25"
										cx="12"
										cy="12"
										r="10"
										stroke="currentColor"
										stroke-width="4"
									></circle>
									<path
										class="opacity-75"
										fill="currentColor"
										d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
									></path>
								</svg>
								{$i18n.t('Running')}
							</div>
						{:else if run}
							<button
								class="inline-flex items-center gap-1 text-xs font-medium text-gray-500 dark:text-gray-300 hover:text-green-600 dark:hover:text-green-400 px-2 py-1 rounded-full hover:bg-white/70 dark:hover:bg-gray-900/60 transition"
								on:click={async () => {
									code = _code;
									await tick();
									executePython(code);
								}}
								aria-label={$i18n.t('Run')}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									class="size-3.5"
								>
									<path
										d="M6.3 2.84A1.5 1.5 0 0 0 4 4.11v11.78a1.5 1.5 0 0 0 2.3 1.27l9.344-5.891a1.5 1.5 0 0 0 0-2.538L6.3 2.841Z"
									/>
								</svg>
								<span class="hidden sm:inline">{$i18n.t('Run')}</span>
							</button>
						{/if}
					{/if}

					{#if save}
						<button
							class="inline-flex items-center gap-1 text-xs font-medium text-gray-500 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white px-2 py-1 rounded-full hover:bg-white/70 dark:hover:bg-gray-900/60 transition"
							on:click={saveCode}
							aria-label={$i18n.t('Save')}
						>
							{#if saved}
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									class="size-3.5 text-green-500"
								>
									<path
										fill-rule="evenodd"
										d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
										clip-rule="evenodd"
									/>
								</svg>
							{:else}
								<span class="hidden sm:inline">{$i18n.t('Save')}</span>
							{/if}
						</button>
					{/if}

					<button
						class="inline-flex items-center gap-1 text-xs font-medium text-gray-500 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white px-2 py-1 rounded-full hover:bg-white/70 dark:hover:bg-gray-900/60 transition"
						on:click={copyCode}
						aria-label={$i18n.t('Copy')}
					>
						{#if copied}
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="size-3.5 text-green-500"
							>
								<path
									fill-rule="evenodd"
									d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z"
									clip-rule="evenodd"
								/>
							</svg>
						{:else}
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="size-3.5"
							>
								<path
									d="M7 3.5A1.5 1.5 0 0 1 8.5 2h3.879a1.5 1.5 0 0 1 1.06.44l3.122 3.12A1.5 1.5 0 0 1 17 6.622V12.5a1.5 1.5 0 0 1-1.5 1.5h-1v-3.379a3 3 0 0 0-.879-2.121L10.5 5.379A3 3 0 0 0 8.379 4.5H7v-1Z"
								/>
								<path
									d="M4.5 6A1.5 1.5 0 0 0 3 7.5v9A1.5 1.5 0 0 0 4.5 18h7a1.5 1.5 0 0 0 1.5-1.5v-5.879a1.5 1.5 0 0 0-.44-1.06L9.44 6.439A1.5 1.5 0 0 0 8.378 6H4.5Z"
								/>
							</svg>
							<span class="hidden sm:inline">{$i18n.t('Copy')}</span>
						{/if}
					</button>

					{#if preview && ['html', 'svg'].includes(lang)}
						<button
							class="inline-flex items-center gap-1 text-xs font-medium text-gray-500 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white px-2 py-1 rounded-full hover:bg-white/70 dark:hover:bg-gray-900/60 transition"
							on:click={previewCode}
							aria-label={$i18n.t('Preview')}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 20 20"
								fill="currentColor"
								class="size-3.5"
							>
								<path d="M10 12.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z" />
								<path
									fill-rule="evenodd"
									d="M.664 10.59a1.651 1.651 0 0 1 0-1.186A10.004 10.004 0 0 1 10 3c4.257 0 7.893 2.66 9.336 6.41.147.381.146.804 0 1.186A10.004 10.004 0 0 1 10 17c-4.257 0-7.893-2.66-9.336-6.41ZM14 10a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z"
									clip-rule="evenodd"
								/>
							</svg>
							<span class="hidden sm:inline">{$i18n.t('Preview')}</span>
						</button>
					{/if}

					<button
						class="inline-flex items-center gap-1 text-xs font-medium text-gray-500 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white px-2 py-1 rounded-full hover:bg-white/70 dark:hover:bg-gray-900/60 transition"
						on:click={collapseCodeBlock}
						aria-label={collapsed ? $i18n.t('Expand') : $i18n.t('Collapse')}
					>
						<ChevronUpDown className="size-3.5" />
					</button>
				</div>
			</div>

			<div
				class="language-{lang} {editorClassName
					? editorClassName
					: executing || stdout || stderr || result
						? ''
						: ''} overflow-hidden font-mono"
			>
				<div class="pt-10 bg-gray-50 dark:bg-gray-950"></div>

				{#if !collapsed}
					{#if edit}
						<div class="px-2">
							<CodeEditor
								value={code}
								{id}
								{lang}
								onSave={() => {
									saveCode();
								}}
								onChange={(value) => {
									_code = value;
								}}
							/>
						</div>
					{:else}
						<pre
							class="hljs p-4 px-5 overflow-x-auto bg-gray-50 dark:bg-gray-950 text-sm leading-7"
							style="border-radius: 0; margin: 0;"><code class="language-{lang} whitespace-pre"
								>{@html hljs.highlightAuto(code, hljs.getLanguage(lang)?.aliases).value ||
									code}</code
							></pre>
					{/if}
				{:else}
					<div
						class="bg-gray-50 dark:bg-gray-950 text-gray-400 dark:text-gray-500 py-2 px-4 flex flex-col gap-2 text-sm text-center border-t border-gray-100 dark:border-gray-900"
					>
						<span class="italic">
							{$i18n.t('{{COUNT}} hidden lines', {
								COUNT: code.split('\n').length
							})}
						</span>
					</div>
				{/if}
			</div>

			{#if !collapsed}
				<div
					id="plt-canvas-{id}"
					class="bg-gray-50 dark:bg-gray-900 text-gray-800 dark:text-gray-200 max-w-full overflow-x-auto scrollbar-hidden"
				></div>

				{#if executing || stdout || stderr || result || files}
					<div
						class="bg-gray-50 dark:bg-gray-900/50 text-gray-800 dark:text-gray-200 border-t border-gray-100 dark:border-gray-800/50 py-3 px-4 flex flex-col gap-3"
					>
						{#if executing}
							<div>
								<div
									class="inline-flex items-center gap-2 rounded-lg bg-gray-100 dark:bg-gray-800/50 px-2.5 py-1 text-xs font-medium text-gray-600 dark:text-gray-400 mb-2"
								>
									{$i18n.t('Output')}
								</div>
								<div class="text-sm flex items-center gap-2 text-gray-500">
									<svg
										class="animate-spin size-3.5"
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
									>
										<circle
											class="opacity-25"
											cx="12"
											cy="12"
											r="10"
											stroke="currentColor"
											stroke-width="4"
										></circle>
										<path
											class="opacity-75"
											fill="currentColor"
											d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
										></path>
									</svg>
									{$i18n.t('Running...')}
								</div>
							</div>
						{:else}
							{#if stdout || stderr}
								<div>
									<div
										class="inline-flex items-center gap-2 rounded-lg bg-gray-100 dark:bg-gray-800/50 px-2.5 py-1 text-xs font-medium text-gray-600 dark:text-gray-400 mb-2"
									>
										{$i18n.t('Output')}
									</div>
									<div
										class="text-sm leading-6 font-mono whitespace-pre-wrap bg-white dark:bg-gray-950 rounded-lg p-3 border border-gray-100 dark:border-gray-800 {stdout?.split(
											'\n'
										)?.length > 100
											? `max-h-96`
											: ''} overflow-y-auto"
										style="font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;"
									>
										{stdout || stderr}
									</div>
								</div>
							{/if}
							{#if result || files}
								<div>
									<div
										class="inline-flex items-center gap-2 rounded-lg bg-gray-100 dark:bg-gray-800/50 px-2.5 py-1 text-xs font-medium text-gray-600 dark:text-gray-400 mb-2"
									>
										{$i18n.t('Result')}
									</div>
									{#if result}
										<div
											class="text-sm leading-6 font-mono bg-white dark:bg-gray-950 rounded-lg p-3 border border-gray-100 dark:border-gray-800"
											style="font-family: 'JetBrains Mono', 'Fira Code', Consolas, monospace;"
										>
											{`${JSON.stringify(result)}`}
										</div>
									{/if}
									{#if files}
										<div class="flex flex-col gap-2 mt-2">
											{#each files as file}
												{#if file.type.startsWith('image')}
													<img
														src={file.data}
														alt="Output"
														class="w-full max-w-[36rem] rounded-lg border border-gray-100 dark:border-gray-800"
													/>
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
