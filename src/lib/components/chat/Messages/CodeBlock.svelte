<script lang="ts">
	import hljs from 'highlight.js';
	import { toast } from 'svelte-sonner';
	import { getContext, onMount, tick, onDestroy } from 'svelte';
	import { config } from '$lib/stores';

	import PyodideWorker from '$lib/workers/pyodide.worker?worker';
	import { executeCode } from '$lib/apis/utils';
	import { copyToClipboard, renderMermaidDiagram, renderVegaVisualization } from '$lib/utils';

	import 'highlight.js/styles/github-dark.min.css';

	import CodeEditor from '$lib/components/common/CodeEditor.svelte';
	import SvgPanZoom from '$lib/components/common/SVGPanZoom.svelte';

	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronUpDown from '$lib/components/icons/ChevronUpDown.svelte';
	import CommandLine from '$lib/components/icons/CommandLine.svelte';
	import Cube from '$lib/components/icons/Cube.svelte';

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

	export let className = 'mb-2';
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

	let mermaidHtml = null;
	let vegaHtml = null;

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

	const render = async () => {
		onUpdate(token);
		if (lang === 'mermaid' && (token?.raw ?? '').slice(-4).includes('```')) {
			try {
				mermaidHtml = await renderMermaidDiagram(code);
			} catch (error) {
				console.error('Failed to render mermaid diagram:', error);
				const errorMsg = error instanceof Error ? error.message : String(error);
				toast.error($i18n.t('Failed to render diagram') + `: ${errorMsg}`);
				mermaidHtml = null;
			}
		} else if (
			(lang === 'vega' || lang === 'vega-lite') &&
			(token?.raw ?? '').slice(-4).includes('```')
		) {
			try {
				vegaHtml = await renderVegaVisualization(code);
			} catch (error) {
				console.error('Failed to render Vega visualization:', error);
				const errorMsg = error instanceof Error ? error.message : String(error);
				toast.error($i18n.t('Failed to render diagram') + `: ${errorMsg}`);
				vegaHtml = null;
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
		class="relative {className} flex flex-col rounded-3xl border border-gray-100 dark:border-gray-850 my-0.5"
		dir="ltr"
	>
		{#if lang === 'mermaid'}
			{#if mermaidHtml}
				<SvgPanZoom
					className=" rounded-3xl max-h-fit overflow-hidden"
					svg={mermaidHtml}
					content={_token.text}
				/>
			{:else}
				<pre class="mermaid">{code}</pre>
			{/if}
		{:else if lang === 'vega' || lang === 'vega-lite'}
			{#if vegaHtml}
				<SvgPanZoom
					className="rounded-3xl max-h-fit overflow-hidden"
					svg={vegaHtml}
					content={_token.text}
				/>
			{:else}
				<pre class="vega">{code}</pre>
			{/if}
		{:else}
			<div
				class="absolute left-0 right-0 py-2.5 pr-3 text-text-300 pl-4.5 text-xs font-medium dark:text-white"
			>
				{lang}
			</div>

			<div
				class="sticky {stickyButtonsClassName} left-0 right-0 py-2 pr-3 flex items-center justify-end w-full z-10 text-xs text-black dark:text-white"
			>
				<div class="flex items-center gap-0.5">
					<button
						class="flex gap-1 items-center bg-none border-none transition rounded-md px-1.5 py-0.5 bg-white dark:bg-black"
						on:click={collapseCodeBlock}
					>
						<div class=" -translate-y-[0.5px]">
							<ChevronUpDown className="size-3" />
						</div>

						<div>
							{collapsed ? $i18n.t('Expand') : $i18n.t('Collapse')}
						</div>
					</button>

					{#if ($config?.features?.enable_code_execution ?? true) && (lang.toLowerCase() === 'python' || lang.toLowerCase() === 'py' || (lang === '' && checkPythonCode(code)))}
						{#if executing}
							<div
								class="run-code-button bg-none border-none p-0.5 cursor-not-allowed bg-white dark:bg-black"
							>
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
								<div>
									{$i18n.t('Run')}
								</div>
							</button>
						{/if}
					{/if}

					{#if save}
						<button
							class="save-code-button bg-none border-none transition rounded-md px-1.5 py-0.5 bg-white dark:bg-black"
							on:click={saveCode}
						>
							{saved ? $i18n.t('Saved') : $i18n.t('Save')}
						</button>
					{/if}

					<button
						class="copy-code-button bg-none border-none transition rounded-md px-1.5 py-0.5 bg-white dark:bg-black"
						on:click={copyCode}>{copied ? $i18n.t('Copied') : $i18n.t('Copy')}</button
					>

					{#if preview && ['html', 'svg'].includes(lang)}
						<button
							class="flex gap-1 items-center run-code-button bg-none border-none transition rounded-md px-1.5 py-0.5 bg-white dark:bg-black"
							on:click={previewCode}
						>
							<div>
								{$i18n.t('Preview')}
							</div>
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
				<div class=" pt-8 bg-white dark:bg-black"></div>

				{#if !collapsed}
					{#if edit}
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
					{:else}
						<pre
							class=" hljs p-4 px-5 overflow-x-auto"
							style="border-top-left-radius: 0px; border-top-right-radius: 0px; {(executing ||
								stdout ||
								stderr ||
								result) &&
								'border-bottom-left-radius: 0px; border-bottom-right-radius: 0px;'}"><code
								class="language-{lang} rounded-t-none whitespace-pre text-sm"
								>{@html hljs.highlightAuto(code, hljs.getLanguage(lang)?.aliases).value ||
									code}</code
							></pre>
					{/if}
				{:else}
					<div
						class="bg-white dark:bg-black dark:text-white rounded-b-3xl! pt-0.5 pb-3 px-4 flex flex-col gap-2 text-xs"
					>
						<span class="text-gray-500 italic">
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
					class="bg-gray-50 dark:bg-black dark:text-white max-w-full overflow-x-auto scrollbar-hidden"
				/>

				{#if executing || stdout || stderr || result || files}
					<div
						class="bg-gray-50 dark:bg-black dark:text-white rounded-b-3xl! py-4 px-4 flex flex-col gap-2"
					>
						{#if executing}
							<div class=" ">
								<div class=" text-gray-500 text-xs mb-1">{$i18n.t('STDOUT/STDERR')}</div>
								<div class="text-sm">{$i18n.t('Running...')}</div>
							</div>
						{:else}
							{#if stdout || stderr}
								<div class=" ">
									<div class=" text-gray-500 text-xs mb-1">{$i18n.t('STDOUT/STDERR')}</div>
									<div
										class="text-sm {stdout?.split('\n')?.length > 100
											? `max-h-96`
											: ''}  overflow-y-auto"
									>
										{stdout || stderr}
									</div>
								</div>
							{/if}
							{#if result || files}
								<div class=" ">
									<div class=" text-gray-500 text-xs mb-1">{$i18n.t('RESULT')}</div>
									{#if result}
										<div class="text-sm">{`${JSON.stringify(result)}`}</div>
									{/if}
									{#if files}
										<div class="flex flex-col gap-2">
											{#each files as file}
												{#if file.type.startsWith('image')}
													<img src={file.data} alt="Output" class=" w-full max-w-[36rem]" />
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
