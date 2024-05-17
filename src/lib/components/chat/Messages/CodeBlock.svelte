<script lang="ts">
	import { copyToClipboard } from '$lib/utils';
	import hljs from 'highlight.js';
	import 'highlight.js/styles/github-dark.min.css';
	import { tick } from 'svelte';

	export let id = '';

	export let lang = '';
	export let code = '';

	let executed = false;
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

	const executePython = async (text) => {
		executed = true;

		await tick();
		const outputDiv = document.getElementById(`code-output-${id}`);

		if (outputDiv) {
			outputDiv.innerText = 'Running...';
		}

		text = text
			.split('\n')
			.map((line, index) => (index === 0 ? line : '    ' + line))
			.join('\n');

		// pyscript
		let div = document.createElement('div');
		let html = `
<py-script type="py" worker>
import js
import sys
import io

# Create a StringIO object to capture the output
output_capture = io.StringIO()

# Save the current standard output
original_stdout = sys.stdout

# Replace the standard output with the StringIO object
sys.stdout = output_capture

try:
    ${text}
except Exception as e:
    # Capture any errors and write them to the output capture
    print(f"Error: {e}", file=output_capture)

# Restore the original standard output
sys.stdout = original_stdout

# Retrieve the captured output
captured_output = "[NO OUTPUT]"
captured_output = output_capture.getvalue()

# Print the captured output
print(captured_output)

def display_message():
    output_div = js.document.getElementById("code-output-${id}")
    output_div.innerText = captured_output

display_message()
</py-script>`;

		div.innerHTML = html;
		const pyScript = div.firstElementChild;
		try {
			document.body.appendChild(pyScript);
			setTimeout(() => {
				document.body.removeChild(pyScript);
			}, 0);
		} catch (error) {
			console.error('Python error:');
			console.error(error);
		}
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
				<div id="code-output-{id}" class="text-sm" />
			</div>
		{/if}
	</div>
{/if}
