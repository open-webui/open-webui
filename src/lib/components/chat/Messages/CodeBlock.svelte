<script lang="ts">
	import { getContext, onMount, tick, onDestroy } from 'svelte';
	import { copyToClipboard } from '$lib/utils';

	import 'highlight.js/styles/github-dark.min.css';

	import PyodideWorker from '$lib/workers/pyodide.worker?worker';
	import CodeEditor from '$lib/components/common/CodeEditor.svelte';
	import SvgPanZoom from '$lib/components/common/SVGPanZoom.svelte';
	import { config } from '$lib/stores';
	import { executeCode } from '$lib/apis/utils';
	import { toast } from 'svelte-sonner';
	import { mermaidService } from '$lib/services/mermaid.service';
	import { mermaidStore } from '$lib/stores/mermaid.store';
	import { MERMAID_CONFIG } from '$lib/constants';
	import {
		type MermaidError,
		createMermaidError,
		getUserMessage,
		isRetryableError,
		retryRender
	} from '$lib/utils/mermaid-errors';

	const i18n = getContext('i18n');

	export let id = '';

	export let onSave = (e) => {};
	export let onCode = (e) => {};

	export let save = false;
	export let run = true;

	export let token;
	export let lang = '';
	export let code = '';
	export let attributes = {};

	export let className = 'my-2';
	export let editorClassName = '';
	export let stickyButtonsClassName = 'top-8';

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
	let isVisible = false;
	let intersectionObserver: IntersectionObserver | null = null;
	let mermaidContainer: HTMLElement | null = null;
	let hasRendered = false; // Track if diagram has been rendered
	let renderError: MermaidError | null = null;
	let retryCount = 0;
	let showErrorDetails = false;

	let highlightedCode = null;
	let executing = false;

	let stdout = null;
	let stderr = null;
	let result = null;
	let files = null;

	let copied = false;
	let saved = false;

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
		await copyToClipboard(code);

		setTimeout(() => {
			copied = false;
		}, 1000);
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

							if (stdout.startsWith(`${line}\n`)) {
								stdout = stdout.replace(`${line}\n`, ``);
							} else if (stdout.startsWith(`${line}`)) {
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

							if (result.startsWith(`${line}\n`)) {
								result = result.replace(`${line}\n`, ``);
							} else if (result.startsWith(`${line}`)) {
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
			code.includes('requests') ? 'requests' : null,
			code.includes('bs4') ? 'beautifulsoup4' : null,
			code.includes('numpy') ? 'numpy' : null,
			code.includes('pandas') ? 'pandas' : null,
			code.includes('sklearn') ? 'scikit-learn' : null,
			code.includes('scipy') ? 'scipy' : null,
			code.includes('re') ? 'regex' : null,
			code.includes('seaborn') ? 'seaborn' : null,
			code.includes('sympy') ? 'sympy' : null,
			code.includes('tiktoken') ? 'tiktoken' : null,
			code.includes('matplotlib') ? 'matplotlib' : null,
			code.includes('pytz') ? 'pytz' : null
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

						if (stdout.startsWith(`${line}\n`)) {
							stdout = stdout.replace(`${line}\n`, ``);
						} else if (stdout.startsWith(`${line}`)) {
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

	let debounceTimeout;

	const drawMermaidDiagram = async () => {
		// Skip if already rendered
		if (hasRendered && !renderError) {
			return;
		}

		// Clear previous error
		renderError = null;

		if (!mermaidService.isInitialized()) {
			const error = createMermaidError('Service not initialized', code.substring(0, 50));
			renderError = error;
			mermaidStore.addError(error.type, error.message, error.codePreview);
			console.log(`[Mermaid] CodeBlock: Service not initialized, using fallback for id=${id}`);
			return;
		}

		console.log(`[Mermaid] CodeBlock: Checking cache for diagram id=${id}`);

		// Get current theme
		const theme = mermaidService.getTheme();

		try {
			// Check cache (memory + IndexedDB)
			const cachedSvg = await mermaidStore.getFromCache(code, theme);
			if (cachedSvg) {
				console.log(`[Mermaid] CodeBlock: Cache hit for id=${id}, using cached SVG`);
				mermaidHtml = cachedSvg;
				hasRendered = true;
				renderError = null;
				return;
			}

			console.log(`[Mermaid] CodeBlock: Cache miss for id=${id}, rendering...`);

			// Render using service with retry logic
			const startTime = performance.now();
			const svg = await retryRender(
				async () => {
					return await mermaidService.render(code, theme);
				},
				MERMAID_CONFIG.MAX_RETRIES
			);
			const renderTime = performance.now() - startTime;

			if (svg) {
				mermaidHtml = svg;
				hasRendered = true;
				renderError = null;
				retryCount = 0;
				// Store in cache (memory + IndexedDB)
				mermaidStore.setInCache(code, svg, theme);
				// Record metrics
				mermaidStore.recordRender(true, renderTime);
				console.log(`[Mermaid] CodeBlock: Render successful for id=${id}, duration=${renderTime.toFixed(2)}ms`);
			} else {
				const error = createMermaidError('Render returned null', code.substring(0, 50));
				renderError = error;
				mermaidStore.recordRender(false, renderTime);
				mermaidStore.addError(error.type, error.message, error.codePreview);
				console.error(`[Mermaid] CodeBlock: Render failed for id=${id}`);
			}
		} catch (error) {
			const errorObj = error instanceof Error ? error : new Error(String(error));
			const mermaidError = createMermaidError(errorObj, code.substring(0, 50));
			renderError = mermaidError;
			mermaidStore.addError(mermaidError.type, mermaidError.message, mermaidError.codePreview);
			console.error(`[Mermaid] CodeBlock: Render error for id=${id}:`, errorObj);
		}
	};

	const handleRetry = async () => {
		if (retryCount >= MERMAID_CONFIG.MAX_RETRIES) {
			console.log(`[Mermaid] Retry failed, showing fallback for id=${id}`);
			return;
		}

		retryCount++;
		console.log(`[Mermaid] Retry button clicked, attempt ${retryCount} for id=${id}`);
		hasRendered = false; // Allow re-render
		await drawMermaidDiagram();
	};

	const debouncedRender = () => {
		if (debounceTimeout) {
			clearTimeout(debounceTimeout);
			console.log(`[Mermaid] Code change detected, resetting debounce timer for id=${id}`);
		}

		debounceTimeout = setTimeout(() => {
			console.log(`[Mermaid] Debounce timeout reached, rendering diagram id=${id}`);
			drawMermaidDiagram();
			debounceTimeout = null;
		}, MERMAID_CONFIG.DEBOUNCE_DELAY);
	};

	const render = async () => {
		if (lang === 'mermaid' && code) {
			// Check if streaming is complete (has closing backticks)
			const rawContent = token?.raw ?? '';
			const isComplete = rawContent.slice(-4).includes('```');

			if (isComplete) {
				// Streaming complete, render immediately
				if (debounceTimeout) {
					clearTimeout(debounceTimeout);
					debounceTimeout = null;
					console.log(`[Mermaid] Streaming complete, rendering immediately for id=${id}`);
				}
				await drawMermaidDiagram();
			} else {
				// Still streaming, debounce
				console.log(`[Mermaid] Streaming detected, debouncing render (${MERMAID_CONFIG.DEBOUNCE_DELAY}ms) for id=${id}`);
				debouncedRender();
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

	$: onCode({ lang, code });

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
		console.log('codeblock', lang, code);

		if (lang) {
			onCode({ lang, code });
		}
		// Mermaid initialization is now handled globally in +layout.svelte

		// Setup lazy loading for Mermaid diagrams
		if (lang === 'mermaid' && browser) {
			await tick(); // Wait for DOM to be ready

			try {
				// Find the container element by data attribute (more reliable)
				mermaidContainer = document.querySelector(`[data-mermaid-id="${id}"]`) as HTMLElement;
				if (!mermaidContainer) {
					// Fallback to ID
					mermaidContainer = document.getElementById(`mermaid-container-${id}`);
				}

				if (mermaidContainer && 'IntersectionObserver' in window) {
					console.log(`[Mermaid] Lazy loading: Observer created for diagram id=${id}`);

					intersectionObserver = new IntersectionObserver(
						(entries) => {
							for (const entry of entries) {
								if (entry.isIntersecting) {
									isVisible = true;
									console.log(`[Mermaid] Lazy loading: Diagram visible, starting render (id: ${id})`);
									drawMermaidDiagram();
								} else {
									isVisible = false;
									console.log(`[Mermaid] Lazy loading: Diagram scrolled out of view (id: ${id})`);
								}
							}
						},
						{
							rootMargin: `${MERMAID_CONFIG.LAZY_LOAD_MARGIN}px`,
							threshold: MERMAID_CONFIG.LAZY_LOAD_THRESHOLD
						}
					);

					intersectionObserver.observe(mermaidContainer);
				} else {
					// IntersectionObserver not available or element not found, render immediately
					console.log(`[Mermaid] Lazy loading: IntersectionObserver unavailable, rendering immediately`);
					isVisible = true;
					drawMermaidDiagram();
				}
			} catch (error) {
				const errorMessage = error instanceof Error ? error.message : String(error);
				console.warn(`[Mermaid] Lazy loading: Error setting up observer: ${errorMessage}, rendering immediately`);
				isVisible = true;
				drawMermaidDiagram();
			}
		}
	});

	onDestroy(() => {
		if (pyodideWorker) {
			pyodideWorker.terminate();
		}

		// Cleanup IntersectionObserver
		if (intersectionObserver) {
			intersectionObserver.disconnect();
			intersectionObserver = null;
		}

		// Clear debounce timeout
		if (debounceTimeout) {
			clearTimeout(debounceTimeout);
			debounceTimeout = null;
		}
	});
</script>

	<div>
	<div class="relative {className} flex flex-col rounded-lg" dir="ltr">
		{#if lang === 'mermaid'}
			<div id="mermaid-container-{id}" data-mermaid-id={id}>
				{#if renderError}
					<div class="mermaid-error border border-red-200 dark:border-red-800 rounded-lg p-4 bg-red-50 dark:bg-red-900/20">
						<div class="flex items-start gap-2 mb-2">
							<div class="error-icon text-red-500 dark:text-red-400 text-xl">⚠️</div>
							<div class="flex-1">
								<div class="error-message text-red-700 dark:text-red-300 font-medium mb-2">
									{getUserMessage(renderError.type)}
								</div>
								{#if isRetryableError(renderError.type) && retryCount < MERMAID_CONFIG.MAX_RETRIES}
									<button
										class="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded text-sm transition"
										on:click={handleRetry}
									>
										Retry
									</button>
								{/if}
							</div>
						</div>
						<details class="mt-2">
							<summary class="cursor-pointer text-sm text-red-600 dark:text-red-400 hover:underline">
								Show code
							</summary>
							<pre class="mt-2 p-2 bg-gray-100 dark:bg-gray-800 rounded text-xs overflow-auto max-h-48"><code>{code}</code></pre>
						</details>
					</div>
				{:else if mermaidHtml}
					<SvgPanZoom
						className=" border border-gray-100 dark:border-gray-850 rounded-lg max-h-fit overflow-hidden"
						svg={mermaidHtml}
						content={_token?.text || code}
					/>
				{:else if !isVisible}
					<div class="border border-gray-100 dark:border-gray-850 rounded-lg p-4 text-center text-gray-500 dark:text-gray-400">
						Loading diagram...
					</div>
				{:else}
					<pre class="mermaid">{code}</pre>
				{/if}
			</div>
		{:else}
			<div class="text-text-300 absolute pl-4 py-1.5 text-xs font-medium dark:text-white">
				{lang}
			</div>

			<div
				class="sticky {stickyButtonsClassName} mb-1 py-1 pr-2.5 flex items-center justify-end z-10 text-xs text-black dark:text-white"
			>
				<div class="flex items-center gap-0.5 translate-y-[1px]">
					{#if lang.toLowerCase() === 'python' || lang.toLowerCase() === 'py' || (lang === '' && checkPythonCode(code))}
						{#if executing}
							<div class="run-code-button bg-none border-none p-1 cursor-not-allowed">Running</div>
						{:else if run}
							<button
								class="run-code-button bg-none border-none bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-md px-1.5 py-0.5"
								on:click={async () => {
									code = _code;
									await tick();
									executePython(code);
								}}>{$i18n.t('Run')}</button
							>
						{/if}
					{/if}

					{#if save}
						<button
							class="save-code-button bg-none border-none bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-md px-1.5 py-0.5"
							on:click={saveCode}
						>
							{saved ? $i18n.t('Saved') : $i18n.t('Save')}
						</button>
					{/if}

					<button
						class="copy-code-button bg-none border-none bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-md px-1.5 py-0.5"
						on:click={copyCode}>{copied ? $i18n.t('Copied') : $i18n.t('Copy')}</button
					>
				</div>
			</div>

			<div
				class="language-{lang} rounded-t-lg -mt-8 {editorClassName
					? editorClassName
					: executing || stdout || stderr || result
						? ''
						: 'rounded-b-lg'} overflow-hidden"
			>
				<div class=" pt-7 bg-gray-50 dark:bg-gray-850"></div>
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

			<div
				id="plt-canvas-{id}"
				class="bg-gray-50 dark:bg-[#202123] dark:text-white max-w-full overflow-x-auto scrollbar-hidden"
			/>

			{#if executing || stdout || stderr || result || files}
				<div
					class="bg-gray-50 dark:bg-[#202123] dark:text-white rounded-b-lg! py-4 px-4 flex flex-col gap-2"
				>
					{#if executing}
						<div class=" ">
							<div class=" text-gray-500 text-xs mb-1">STDOUT/STDERR</div>
							<div class="text-sm">Running...</div>
						</div>
					{:else}
						{#if stdout || stderr}
							<div class=" ">
								<div class=" text-gray-500 text-xs mb-1">STDOUT/STDERR</div>
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
								<div class=" text-gray-500 text-xs mb-1">RESULT</div>
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
	</div>
</div>
