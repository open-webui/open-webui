<script lang="ts">
	import mermaid from 'mermaid';

	import { v4 as uuidv4 } from 'uuid';

	import { getContext, onMount, tick, onDestroy } from 'svelte';
	import { slide } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';
	import { copyToClipboard } from '$lib/utils';

	let codeBlockElement;
	let buttonsElement;
	let messagesContainer;
	let animationFrameId;

	import 'highlight.js/styles/github-dark.min.css';

	import PyodideWorker from '$lib/workers/pyodide.worker?worker';
	import CodeEditor from '$lib/components/common/CodeEditor.svelte';
	import SvgPanZoom from '$lib/components/common/SVGPanZoom.svelte';
	import { config } from '$lib/stores';
	import { executeCode } from '$lib/apis/utils';
	import { toast } from 'svelte-sonner';
	import ChevronUpDown from '$lib/components/icons/ChevronUpDown.svelte';
	import CommandLine from '$lib/components/icons/CommandLine.svelte';
	import Cube from '$lib/components/icons/Cube.svelte';

	const i18n = getContext('i18n');

	export let id = '';

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

	export let className = 'my-2';
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

	let highlightedCode = null;
	let executing = false;

	let stdout = null;
	let stderr = null;
	let result = null;
	let files = null;

	let copied = false;
	let saved = false;

	const collapseCodeBlock = async () => {
		collapsed = !collapsed;
		await tick(); // Ensure DOM updates complete

		// Update button position after collapse state changes
		setTimeout(() => {
			updateButtonPosition();
		}, 100); // Small delay to ensure layout has updated
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
		await copyToClipboard(code);

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
			code.includes('pytz') ? 'pytz' : null,
			code.includes('openai') ? 'openai' : null
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
		try {
			if (await mermaid.parse(code)) {
				const { svg } = await mermaid.render(`mermaid-${uuidv4()}`, code);
				mermaidHtml = svg;
			}
		} catch (error) {
			console.log('Error:', error);
		}
	};

	const render = async () => {
		if (lang === 'mermaid' && (token?.raw ?? '').slice(-4).includes('```')) {
			(async () => {
				await drawMermaidDiagram();
			})();
		}

		onUpdate(token);
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

	let topSectionHeight = 70; // Cache the height to avoid repeated DOM queries

	const updateButtonPosition = () => {
		if (!codeBlockElement || !buttonsElement || !messagesContainer) return;

		const containerRect = messagesContainer.getBoundingClientRect();
		const codeBlockRect = codeBlockElement.getBoundingClientRect();

		// Check if code block is visible in the container
		if (codeBlockRect.bottom < containerRect.top || codeBlockRect.top > containerRect.bottom) {
			return; // Code block not visible
		}

		// Calculate how much of the code block is above the visible area (including top section)
		const hiddenTop = Math.max(0, containerRect.top + topSectionHeight - codeBlockRect.top);

		// Calculate offset with strict bounds
		let offset;
		if (collapsed) {
			// For collapsed state: buttons should stay very close to the top
			// Never move more than 40px down, and ensure they stay above the collapsed content
			const maxCollapsedOffset = Math.min(40, Math.max(0, codeBlockRect.height - 80)); // Leave 80px for content
			offset = Math.min(hiddenTop, maxCollapsedOffset);

			// Ensure buttons never go below the language label area when collapsed
			offset = Math.max(0, offset);
		} else {
			// For expanded state: allow more movement but still within bounds
			const maxExpandedOffset = Math.max(
				0,
				codeBlockRect.height - buttonsElement.offsetHeight - 20
			);
			offset = Math.min(hiddenTop, maxExpandedOffset);
		}

		// Additional safety: if offset would push buttons below visible area, reset to 0
		if (codeBlockRect.top + offset + buttonsElement.offsetHeight > containerRect.bottom) {
			offset = Math.max(0, containerRect.bottom - codeBlockRect.top - buttonsElement.offsetHeight);
		}

		buttonsElement.style.transform = `translateY(${offset}px)`;
	};

	const throttledUpdatePosition = () => {
		if (animationFrameId) return; // Already scheduled

		animationFrameId = requestAnimationFrame(() => {
			updateButtonPosition();
			animationFrameId = null;
		});
	};

	const calculateTopSectionHeight = () => {
		const chatHeader =
			document.querySelector('[data-testid="chat-header"]') ||
			document.querySelector('.chat-header') ||
			document.querySelector('nav') ||
			messagesContainer?.previousElementSibling;

		if (chatHeader) {
			topSectionHeight = chatHeader.getBoundingClientRect().height;
		}
	};

	// Clean code block implementation

	onMount(async () => {
		if (token) {
			onUpdate(token);
		}

		if (document.documentElement.classList.contains('dark')) {
			mermaid.initialize({
				startOnLoad: true,
				theme: 'dark',
				securityLevel: 'loose'
			});
		} else {
			mermaid.initialize({
				startOnLoad: true,
				theme: 'default',
				securityLevel: 'loose'
			});
		}

		// Set up scroll listener for button positioning
		messagesContainer = document.getElementById('messages-container');
		if (messagesContainer) {
			// Calculate top section height once
			calculateTopSectionHeight();

			// Use throttled update for smooth performance
			messagesContainer.addEventListener('scroll', throttledUpdatePosition, { passive: true });
			window.addEventListener('resize', () => {
				calculateTopSectionHeight();
				throttledUpdatePosition();
			});

			// Initial position
			setTimeout(updateButtonPosition, 100);
		}
	});

	onDestroy(() => {
		if (pyodideWorker) {
			pyodideWorker.terminate();
		}
		if (messagesContainer) {
			messagesContainer.removeEventListener('scroll', throttledUpdatePosition);
			window.removeEventListener('resize', throttledUpdatePosition);
		}
		if (animationFrameId) {
			cancelAnimationFrame(animationFrameId);
		}
	});
</script>

<div bind:this={codeBlockElement}>
	<div
		class="relative {className} flex flex-col rounded-lg transition-all duration-300 ease-in-out"
		dir="ltr"
		style="
      contain: layout !important;
      width: 100% !important;
      max-width: 100% !important;
      min-width: 100% !important;
      overflow-x: auto !important;
      flex-shrink: 0 !important;
      flex-grow: 0 !important;
    "
	>
		{#if lang === 'mermaid'}
			{#if mermaidHtml}
				<SvgPanZoom
					className=" border border-gray-100 dark:border-gray-850 rounded-lg max-h-fit overflow-hidden"
					svg={mermaidHtml}
					content={_token.text}
				/>
			{:else}
				<pre class="mermaid">{code}</pre>
			{/if}
		{:else}
			<div class="text-text-300 absolute pl-4 py-1.5 text-xs font-medium dark:text-white">
				{lang}
			</div>

			<div
				bind:this={buttonsElement}
				class="absolute top-0 right-0 mb-1 py-1 pr-2.5 flex items-center justify-end z-30 text-xs text-black dark:text-white"
			>
				<div class="flex items-center gap-0.5 translate-y-[1px]">
					<button
						class="flex gap-1 items-center bg-none border border-gray-200 dark:border-gray-700 bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-md px-1.5 py-0.5"
						on:click={collapseCodeBlock}
					>
						<div
							class=" -translate-y-[0.5px] transition-transform duration-300 {collapsed
								? 'rotate-180'
								: ''}"
						>
							<ChevronUpDown className="size-3" />
						</div>

						<div>
							{collapsed ? $i18n.t('Expand') : $i18n.t('Collapse')}
						</div>
					</button>

					{#if preview && ['html', 'svg'].includes(lang)}
						<button
							class="flex gap-1 items-center run-code-button bg-none border border-gray-200 dark:border-gray-700 bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-md px-1.5 py-0.5"
							on:click={previewCode}
						>
							<div class=" -translate-y-[0.5px]">
								<Cube className="size-3" />
							</div>

							<div>
								{$i18n.t('Preview')}
							</div>
						</button>
					{/if}

					{#if ($config?.features?.enable_code_execution ?? true) && (lang.toLowerCase() === 'python' || lang.toLowerCase() === 'py' || (lang === '' && checkPythonCode(code)))}
						{#if executing}
							<div class="run-code-button bg-none border-none p-1 cursor-not-allowed">
								{$i18n.t('Running')}
							</div>
						{:else if run}
							<button
								class="flex gap-1 items-center run-code-button bg-none border border-gray-200 dark:border-gray-700 bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-md px-1.5 py-0.5"
								on:click={async () => {
									code = _code;
									await tick();
									executePython(code);
								}}
							>
								<div class=" -translate-y-[0.5px]">
									<CommandLine className="size-3" />
								</div>

								<div>
									{$i18n.t('Run')}
								</div>
							</button>
						{/if}
					{/if}

					{#if save}
						<button
							class="save-code-button bg-none border border-gray-200 dark:border-gray-700 bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-md px-1.5 py-0.5"
							on:click={saveCode}
						>
							{saved ? $i18n.t('Saved') : $i18n.t('Save')}
						</button>
					{/if}

					<button
						class="copy-code-button bg-none border border-gray-200 dark:border-gray-700 bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-md px-1.5 py-0.5"
						on:click={copyCode}>{copied ? $i18n.t('Copied') : $i18n.t('Copy')}</button
					>
				</div>
			</div>

			<div
				class="language-{lang} rounded-t-lg -mt-8 {editorClassName
					? editorClassName
					: executing || stdout || stderr || result
						? ''
						: 'rounded-b-lg'} overflow-hidden transition-all duration-300 ease-in-out"
				style="
          contain: layout !important;
          width: 100% !important;
          max-width: 100% !important;
          min-width: 100% !important;
          overflow-x: auto !important;
          flex-shrink: 0 !important;
          flex-grow: 0 !important;
        "
			>
				<div class=" pt-7 bg-gray-50 dark:bg-gray-850"></div>

				<div class="w-full">
					{#if !collapsed}
						<div
							in:slide={{ duration: 300, delay: 0, easing: quintOut }}
							out:slide={{ duration: 300, delay: 0, easing: quintOut }}
							class="overflow-hidden"
						>
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
						<div
							class="bg-gray-50 dark:bg-black dark:text-white rounded-b-lg! pt-2 pb-2 px-4 flex flex-col gap-2 text-xs overflow-hidden"
							in:slide={{ duration: 300, delay: 0, easing: quintOut }}
							out:slide={{ duration: 300, delay: 0, easing: quintOut }}
						>
							<span class="text-gray-500 italic">
								{$i18n.t('{{COUNT}} hidden lines', {
									COUNT: code.split('\n').length
								})}
							</span>
						</div>
					{/if}
				</div>
			</div>

			{#if !collapsed}
				<div
					in:slide={{ duration: 300, delay: 0, easing: quintOut }}
					out:slide={{ duration: 300, delay: 0, easing: quintOut }}
					class="overflow-hidden"
				>
					<div
						id="plt-canvas-{id}"
						class="bg-gray-50 dark:bg-[#202123] dark:text-white max-w-full overflow-x-auto scrollbar-hidden"
						style="contain: layout;"
					/>

					{#if executing || stdout || stderr || result || files}
						<div
							class="bg-gray-50 dark:bg-[#202123] dark:text-white rounded-b-lg! py-4 px-4 flex flex-col gap-2"
							style="contain: layout;"
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
											<div class="text-sm">
												{`${JSON.stringify(result)}`}
											</div>
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
				</div>
			{/if}
		{/if}
	</div>
</div>
