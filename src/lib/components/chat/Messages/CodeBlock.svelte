<script lang="ts">
	import hljs from 'highlight.js';
	import { loadPyodide } from 'pyodide';
	import mermaid from 'mermaid';

	import { v4 as uuidv4 } from 'uuid';

	import { getContext, getAllContexts, onMount } from 'svelte';
	import { copyToClipboard } from '$lib/utils';

	import 'highlight.js/styles/github-dark.min.css';

	import PyodideWorker from '$lib/workers/pyodide.worker?worker';

	const i18n = getContext('i18n');

	export let id = '';

	export let token;
	export let lang = '';
	export let code = '';

	let mermaidHtml = null;

	let highlightedCode = null;
	let executing = false;

	let stdout = null;
	let stderr = null;
	let result = null;

	let copied = false;

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
		if (!code.includes('input') && !code.includes('matplotlib')) {
			executePythonAsWorker(code);
		} else {
			result = null;
			stdout = null;
			stderr = null;

			executing = true;

			document.pyodideMplTarget = document.getElementById(`plt-canvas-${id}`);

			let pyodide = await loadPyodide({
				indexURL: '/pyodide/',
				stdout: (text) => {
					console.log('Python output:', text);

					if (stdout) {
						stdout += `${text}\n`;
					} else {
						stdout = `${text}\n`;
					}
				},
				stderr: (text) => {
					console.log('An error occured:', text);
					if (stderr) {
						stderr += `${text}\n`;
					} else {
						stderr = `${text}\n`;
					}
				},
				packages: ['micropip']
			});

			try {
				const micropip = pyodide.pyimport('micropip');

				// await micropip.set_index_urls('https://pypi.org/pypi/{package_name}/json');

				let packages = [
					code.includes('requests') ? 'requests' : null,
					code.includes('bs4') ? 'beautifulsoup4' : null,
					code.includes('numpy') ? 'numpy' : null,
					code.includes('pandas') ? 'pandas' : null,
					code.includes('matplotlib') ? 'matplotlib' : null,
					code.includes('sklearn') ? 'scikit-learn' : null,
					code.includes('scipy') ? 'scipy' : null,
					code.includes('re') ? 'regex' : null,
					code.includes('seaborn') ? 'seaborn' : null
				].filter(Boolean);

				console.log(packages);
				await micropip.install(packages);

				result = await pyodide.runPythonAsync(`from js import prompt
def input(p):
    return prompt(p)
__builtins__.input = input`);

				result = await pyodide.runPython(code);

				if (!result) {
					result = '[NO OUTPUT]';
				}

				console.log(result);
				console.log(stdout);
				console.log(stderr);

				const pltCanvasElement = document.getElementById(`plt-canvas-${id}`);

				if (pltCanvasElement?.innerHTML !== '') {
					pltCanvasElement.classList.add('pt-4');
				}
			} catch (error) {
				console.error('Error:', error);
				stderr = error;
			}

			executing = false;
		}
	};

	const executePythonAsWorker = async (code) => {
		result = null;
		stdout = null;
		stderr = null;

		executing = true;

		let packages = [
			code.includes('requests') ? 'requests' : null,
			code.includes('bs4') ? 'beautifulsoup4' : null,
			code.includes('numpy') ? 'numpy' : null,
			code.includes('pandas') ? 'pandas' : null,
			code.includes('sklearn') ? 'scikit-learn' : null,
			code.includes('scipy') ? 'scipy' : null,
			code.includes('re') ? 'regex' : null,
			code.includes('seaborn') ? 'seaborn' : null
		].filter(Boolean);

		console.log(packages);

		const pyodideWorker = new PyodideWorker();

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

			data['stdout'] && (stdout = data['stdout']);
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

	$: if (token.raw) {
		if (lang === 'mermaid' && (token?.raw ?? '').slice(-4).includes('```')) {
			(async () => {
				await drawMermaidDiagram();
			})();
		} else {
			// Function to perform the code highlighting
			const highlightCode = () => {
				highlightedCode = hljs.highlightAuto(code, hljs.getLanguage(lang)?.aliases).value || code;
			};

			// Clear the previous timeout if it exists
			clearTimeout(debounceTimeout);
			// Set a new timeout to debounce the code highlighting
			debounceTimeout = setTimeout(highlightCode, 10);
		}
	}

	onMount(async () => {
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
	});
</script>

<div class="my-2" dir="ltr">
	{#if lang === 'mermaid'}
		{#if mermaidHtml}
			{@html `${mermaidHtml}`}
		{:else}
			<pre class="mermaid">{code}</pre>
		{/if}
	{:else}
		<div
			class="flex justify-between bg-[#202123] text-white text-xs px-4 pt-1 pb-0.5 rounded-t-lg overflow-x-auto"
		>
			<div class="p-1">{lang}</div>

			<div class="flex items-center">
				{#if lang.toLowerCase() === 'python' || lang.toLowerCase() === 'py' || (lang === '' && checkPythonCode(code))}
					{#if executing}
						<div class="copy-code-button bg-none border-none p-1 cursor-not-allowed">Running</div>
					{:else}
						<button
							class="copy-code-button bg-none border-none p-1"
							on:click={() => {
								executePython(code);
							}}>{$i18n.t('Run')}</button
						>
					{/if}
				{/if}
				<button class="copy-code-button bg-none border-none p-1" on:click={copyCode}
					>{copied ? $i18n.t('Copied') : $i18n.t('Copy Code')}</button
				>
			</div>
		</div>

		<pre
			class=" hljs p-4 px-5 overflow-x-auto"
			style="border-top-left-radius: 0px; border-top-right-radius: 0px; {(executing ||
				stdout ||
				stderr ||
				result) &&
				'border-bottom-left-radius: 0px; border-bottom-right-radius: 0px;'}"><code
				class="language-{lang} rounded-t-none whitespace-pre"
				>{#if highlightedCode}{@html highlightedCode}{:else}{code}{/if}</code
			></pre>

		<div
			id="plt-canvas-{id}"
			class="bg-[#202123] text-white max-w-full overflow-x-auto scrollbar-hidden"
		/>

		{#if executing}
			<div class="bg-[#202123] text-white px-4 py-4 rounded-b-lg">
				<div class=" text-gray-500 text-xs mb-1">STDOUT/STDERR</div>
				<div class="text-sm">Running...</div>
			</div>
		{:else if stdout || stderr || result}
			<div class="bg-[#202123] text-white px-4 py-4 rounded-b-lg">
				<div class=" text-gray-500 text-xs mb-1">STDOUT/STDERR</div>
				<div class="text-sm">{stdout || stderr || result}</div>
			</div>
		{/if}
	{/if}
</div>
