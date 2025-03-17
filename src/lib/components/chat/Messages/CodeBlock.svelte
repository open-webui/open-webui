<script lang="ts">
	import hljs from 'highlight.js';
	import { loadPyodide } from 'pyodide';
	import mermaid from 'mermaid';

	import { v4 as uuidv4 } from 'uuid';

	import { getContext, getAllContexts, onMount, tick, createEventDispatcher } from 'svelte';
	import { copyToClipboard } from '$lib/utils';

	import 'highlight.js/styles/github-dark.min.css';

	import PyodideWorker from '$lib/workers/pyodide.worker?worker';
	import CodeEditor from '$lib/components/common/CodeEditor.svelte';
	import SvgPanZoom from '$lib/components/common/SVGPanZoom.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let id = '';

	export let save = false;
	export let run = true;

	export let token;
	export let lang = '';
	export let code = '';
	export let attributes = {};

	export let className = 'my-2';
	export let editorClassName = '';
	export let stickyButtonsClassName = 'top-8';

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

	const saveCode = () => {
		saved = true;

		code = _code;
		dispatch('save', code);

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
		executePythonAsWorker(code);
	};

	const executePythonAsWorker = async (code) => {
		result = null;
		stdout = null;
		stderr = null;

		executing = true;

		// Define the packages array
		const availablePackages = [
			'affine',
			'altair',
			'annotated-types',
			'apsw',
			'argon2-cffi',
			'argon2-cffi-bindings',
			'arro3-compute',
			'arro3-core',
			'arro3-io',
			'asciitree',
			'astropy',
			'astropy_iers_data',
			'asttokens',
			'async-timeout',
			'atomicwrites',
			'attrs',
			'autograd',
			'awkward-cpp',
			'b2d',
			'bcrypt',
			'beautifulsoup4',
			'biopython',
			'bitarray',
			'bitstring',
			'bleach',
			'bokeh',
			'boost-histogram',
			'brotli',
			'cachetools',
			'Cartopy',
			'casadi',
			'cbor-diag',
			'cffi',
			'cffi_example',
			'cftime',
			'charset-normalizer',
			'clarabel',
			'click',
			'cligj',
			'clingo',
			'cloudpickle',
			'cmyt',
			'colorspacious',
			'contourpy',
			'coolprop',
			'coverage',
			'cramjam',
			'crc32c',
			'cryptography',
			'css-inline',
			'cssselect',
			'cvxpy-base',
			'cycler',
			'cysignals',
			'cytoolz',
			'decorator',
			'demes',
			'deprecation',
			'distlib',
			'docutils',
			'duckdb',
			'ewah_bool_utils',
			'exceptiongroup',
			'executing',
			'fastparquet',
			'fiona',
			'fonttools',
			'freesasa',
			'frozenlist',
			'fsspec',
			'future',
			'galpy',
			'gmpy2',
			'gsw',
			'h5py',
			'html5lib',
			'igraph',
			'imageio',
			'iminuit',
			'iniconfig',
			'ipython',
			'jedi',
			'Jinja2',
			'joblib',
			'jsonschema',
			'jsonschema_specifications',
			'kiwisolver',
			'lakers-python',
			'lazy-object-proxy',
			'lazy_loader',
			'libcst',
			'logbook',
			'lxml',
			'MarkupSafe',
			'matplotlib',
			'matplotlib-inline',
			'matplotlib-pyodide',
			'memory-allocator',
			'mmh3',
			'mne',
			'more-itertools',
			'mpmath',
			'msgpack',
			'msgspec',
			'msprime',
			'multidict',
			'munch',
			'mypy',
			'narwhals',
			'netcdf4',
			'networkx',
			'newick',
			'nh3',
			'nlopt',
			'nltk',
			'numcodecs',
			'numpy',
			'opencv-python',
			'optlang',
			'orjson',
			'packaging',
			'pandas',
			'parso',
			'patsy',
			'peewee',
			'pi-heif',
			'Pillow',
			'pillow-heif',
			'pkgconfig',
			'pluggy',
			'polars',
			'pplpy',
			'primecountpy',
			'prompt_toolkit',
			'protobuf',
			'pure-eval',
			'py',
			'pyclipper',
			'pycparser',
			'pycryptodome',
			'pydantic',
			'pydantic_core',
			'pyerfa',
			'pygame-ce',
			'Pygments',
			'pyheif',
			'pyiceberg',
			'pyinstrument',
			'pynacl',
			'pyodide-unix-timezones',
			'pyparsing',
			'pyproj',
			'pyrsistent',
			'pysam',
			'pyshp',
			'pytest',
			'pytest-asyncio',
			'pytest-benchmark',
			'python-dateutil',
			'python-flint',
			'python-magic',
			'python-sat',
			'python-solvespace',
			'pytz',
			'pywavelets',
			'pyxel',
			'pyxirr',
			'pyyaml',
			'qrcode',
			'rasterio',
			'rateslib',
			'rebound',
			'reboundx',
			'referencing',
			'regex',
			'retrying',
			'rich',
			'river',
			'rpds-py',
			'ruamel.yaml',
			'rust-abi-test',
			'rust-panic-test',
			'scipy',
			'screed',
			'setuptools',
			'shapely',
			'simplejson',
			'sisl',
			'six',
			'smart-open',
			'sortedcontainers',
			'soupsieve',
			'sourmash',
			'soxr',
			'sparseqr',
			'sqlalchemy',
			'stack-data',
			'statsmodels',
			'strictyaml',
			'svgwrite',
			'swiglpk',
			'sympy',
			'tblib',
			'termcolor',
			'texttable',
			'threadpoolctl',
			'tiktoken',
			'tomli',
			'tomli-w',
			'toolz',
			'tqdm',
			'traitlets',
			'traits',
			'tree-sitter',
			'tree-sitter-go',
			'tree-sitter-java',
			'tree-sitter-python',
			'tskit',
			'typing-extensions',
			'tzdata',
			'uncertainties',
			'unyt',
			'vega-datasets',
			'wcwidth',
			'webencodings',
			'wordcloud',
			'wrapt',
			'xarray',
			'xlrd',
			'xxhash',
			'xyzservices',
			'yt',
			'zarr',
			'zengl',
			'zfpy',
			'zstandard'
		];

		// Special case mappings for package name differences
		const packageMappings = {
			'bs4': 'beautifulsoup4'
		};

		// Detect packages from the code
		let packages = [];
		
		// First check for special mappings
		for (const [importName, packageName] of Object.entries(packageMappings)) {
			if (code.includes(importName)) {
				packages.push(packageName);
			}
		}
		
		// Then check for direct package names
		for (const pkg of availablePackages) {
			// Skip packages already added through mappings
			if (packages.includes(pkg)) continue;
			
			// Check if the package name appears in the code
			if (code.includes(pkg)) {
				packages.push(pkg);
			}
		}

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

						stdout = stdout.replace(`${line}\n`, ``);
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
	};

	$: if (token) {
		if (JSON.stringify(token) !== JSON.stringify(_token)) {
			_token = token;
		}
	}

	$: if (_token) {
		render();
	}

	$: dispatch('code', { lang, code });

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
			dispatch('code', { lang, code });
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
	});
</script>

<div>
	<div class="relative {className} flex flex-col rounded-lg" dir="ltr">
		{#if lang === 'mermaid'}
			{#if mermaidHtml}
				<SvgPanZoom
					className=" border border-gray-50 dark:border-gray-850 rounded-lg max-h-fit overflow-hidden"
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
					on:save={() => {
						saveCode();
					}}
					on:change={(e) => {
						_code = e.detail.value;
					}}
				/>
			</div>

			<div
				id="plt-canvas-{id}"
				class="bg-gray-50 dark:bg-[#202123] dark:text-white max-w-full overflow-x-auto scrollbar-hidden"
			/>

			{#if executing || stdout || stderr || result}
				<div
					class="bg-gray-50 dark:bg-[#202123] dark:text-white !rounded-b-lg py-4 px-4 flex flex-col gap-2"
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
								<div class="text-sm">{stdout || stderr}</div>
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
												<img src={file.data} alt="Output" />
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
