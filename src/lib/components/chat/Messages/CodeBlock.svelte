<script lang="ts">
	import { copyToClipboard } from '$lib/utils';
	import hljs from 'highlight.js';
	import 'highlight.js/styles/github-dark.min.css';
	import { loadPyodide } from 'pyodide';
	import { tick } from 'svelte';

	export let id = '';

	export let lang = '';
	export let code = '';

	let executed = false;

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
		// Check if the string contains typical Python keywords, syntax, or functions
		const pythonKeywords = [
			'def',
			'class',
			'import',
			'from',
			'if',
			'else',
			'elif',
			'for',
			'while',
			'try',
			'except',
			'finally',
			'return',
			'yield',
			'lambda',
			'assert',
			'pass',
			'break',
			'continue',
			'global',
			'nonlocal',
			'del',
			'True',
			'False',
			'None',
			'and',
			'or',
			'not',
			'in',
			'is',
			'as',
			'with'
		];

		for (let keyword of pythonKeywords) {
			if (str.includes(keyword)) {
				return true;
			}
		}

		// Check if the string contains typical Python syntax characters
		const pythonSyntax = [
			'def ',
			'class ',
			'import ',
			'from ',
			'if ',
			'else:',
			'elif ',
			'for ',
			'while ',
			'try:',
			'except:',
			'finally:',
			'return ',
			'yield ',
			'lambda ',
			'assert ',
			'pass',
			'break',
			'continue',
			'global ',
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
			' as ',
			' with ',
			':',
			'=',
			'==',
			'!=',
			'>',
			'<',
			'>=',
			'<=',
			'+',
			'-',
			'*',
			'/',
			'%',
			'**',
			'//',
			'(',
			')',
			'[',
			']',
			'{',
			'}'
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
		executed = true;

		let pyodide = await loadPyodide({
			indexURL: '/pyodide/',
			stderr: (text) => {
				console.log('An error occured:', text);
				if (stderr) {
					stderr += `${text}\n`;
				} else {
					stderr = `${text}\n`;
				}
			},
			stdout: (text) => {
				console.log('Python output:', text);

				if (stdout) {
					stdout += `${text}\n`;
				} else {
					stdout = `${text}\n`;
				}
			}
		});

		result = pyodide.runPython(code);

		console.log(result);
		console.log(stderr);
		console.log(stdout);
	};

	$: highlightedCode = code ? hljs.highlightAuto(code, hljs.getLanguage(lang)?.aliases).value : '';
</script>

{#if code}
	<div class="mb-4">
		<div
			class="flex justify-between bg-[#202123] text-white text-xs px-4 pt-1 pb-0.5 rounded-t-lg overflow-x-auto"
		>
			<div class="p-1">{@html lang}</div>

			<div class="flex items-center">
				{#if lang === 'python' || checkPythonCode(code)}
					<button
						class="copy-code-button bg-none border-none p-1"
						on:click={() => {
							executePython(code);
						}}>Run</button
					>
				{/if}
				<button class="copy-code-button bg-none border-none p-1" on:click={copyCode}
					>{copied ? 'Copied' : 'Copy Code'}</button
				>
			</div>
		</div>

		<pre
			class=" hljs p-4 px-5 overflow-x-auto"
			style="border-top-left-radius: 0px; border-top-right-radius: 0px; {executed &&
				'border-bottom-left-radius: 0px; border-bottom-right-radius: 0px;'}"><code
				class="language-{lang} rounded-t-none whitespace-pre">{@html highlightedCode || code}</code
			></pre>

		{#if executed}
			<div class="bg-[#202123] text-white px-4 py-4 rounded-b-lg">
				<div class=" text-gray-500 text-xs mb-1">STDOUT/STDERR</div>
				<div class="text-sm">
					{#if stdout}
						{stdout}
					{:else if result}
						{result}
					{:else if stderr}
						{stderr}
					{:else}
						Running...
					{/if}
				</div>
			</div>
		{/if}
	</div>
{/if}
