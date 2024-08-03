<script lang="ts">
	import { copyToClipboard } from '$lib/utils';
	import hljs from 'highlight.js';
	import 'highlight.js/styles/github-dark.min.css';
	import { loadSandpackClient } from '@codesandbox/sandpack-client';

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

	let sandpackIframe;
	let sandpackClient;
	const executeHTML = async (code) => {
		// Initialize Sandpack client
		const content = {
			files: {
				'/package.json': {
					code: JSON.stringify({
						main: 'index.html',
						devDependencies: {}
					})
				},
				'/index.html': { code }
			},
			environment: 'vanilla',
			template: 'static'
		};
		if (sandpackClient) {
			sandpackClient.updateSandbox(content);
		} else {
			sandpackClient = await loadSandpackClient(sandpackIframe, content, {
				showOpenInCodeSandbox: true
			});
		}
	};

	$: if (lang.toLowerCase() == 'php' || lang.toLowerCase() == 'html') {
		if (!!sandpackIframe) {
			executeHTML(code);
		}
	}

	let debounceTimeout;
	$: if (code) {
		// Function to perform the code highlighting
		const highlightCode = () => {
			highlightedCode = hljs.highlightAuto(code, hljs.getLanguage(lang)?.aliases).value || code;
		};

		// Clear the previous timeout if it exists
		clearTimeout(debounceTimeout);

		// Set a new timeout to debounce the code highlighting
		debounceTimeout = setTimeout(highlightCode, 10);
	}
</script>

<div class="mb-4" dir="ltr">
	<div
		class="flex justify-between bg-[#202123] text-white text-xs px-4 pt-1 pb-0.5 rounded-t-lg overflow-x-auto"
	>
		<div class="p-1">{@html lang}</div>

		<div class="flex items-center">
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
			class="language-{lang} rounded-t-none whitespace-pre"
			>{#if highlightedCode}{@html highlightedCode}{:else}{code}{/if}</code
		>
	</pre>

	{#if lang.toLowerCase() == 'php' || lang.toLowerCase() == 'html'}
		<div class="bg-[#202123] text-white px-4 py-4 rounded-b-lg">
			<div class="text-gray-500 text-xs mb-1 flex justify-between items-center">
				<span>HTML</span>
				<button
					class="copy-code-button bg-none border-none p-1"
					on:click={() => {
						executeHTML(code);
					}}>Refresh</button
				>
			</div>
			<iframe bind:this={sandpackIframe} title="HTML Preview" class="w-full h-96 mt-4 bg-white" />
		</div>
	{/if}
</div>