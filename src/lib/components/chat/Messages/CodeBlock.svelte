<script lang="ts">
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { copyToClipboard } from '$lib/utils';
	import hljs from 'highlight.js';
	import 'highlight.js/styles/github-dark.min.css';
	import { loadPyodide } from 'pyodide';
	import { onMount, tick } from 'svelte';
	import PyodideWorker from '$lib/workers/pyodide.worker?worker';

	export let id = '';

	export let lang = '';
	export let code = '';

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

	$: if (code) {
		highlightedCode = hljs.highlightAuto(code, hljs.getLanguage(lang)?.aliases).value || code;
	}
</script>

<div class="mb-4" dir="ltr">
	<div
		class="flex justify-between bg-[#202123] text-white text-xs px-4 pt-1 pb-0.5 rounded-t-lg overflow-x-auto"
	>
		<div class="p-1">{@html lang}</div>

		<div class="flex items-center">
			{#if lang.toLowerCase() === 'python' || lang.toLowerCase() === 'py' || (lang === '' && checkPythonCode(code))}
				{#if executing}
					<div class="copy-code-button bg-none border-none p-1 cursor-not-allowed">Running</div>
				{:else}
					<button
						class="copy-code-button bg-none border-none p-1"
						on:click={() => {
							executePython(code);
						}}>Run</button
					>
				{/if}
			{/if}
			<button class="copy-code-button bg-none border-none p-1" on:click={copyCode}
				>{copied ? 'Copied' : 'Copy Code'}</button
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
			class="language-{lang} rounded-t-none whitespace-pre">{@html highlightedCode || code}</code
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
</div>
