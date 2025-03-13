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

		let packages = [
			code.includes('requests') ? 'requests' : null,
			code.includes('bs4') ? 'beautifulsoup4' : null,
			code.includes('numpy') ? 'numpy' : null,
			code.includes('pandas') ? 'pandas' : null,
			code.includes('scipy') ? 'scipy' : null,
			code.includes('seaborn') ? 'seaborn' : null,
			code.includes('sympy') ? 'sympy' : null,
			code.includes('tiktoken') ? 'tiktoken' : null,
			code.includes('matplotlib') ? 'matplotlib' : null,
			code.includes('pytz') ? 'pytz' : null,
			code.includes('simplejson') ? 'simplejson' : null,
			code.includes('affine') ? 'affine' : null,
			code.includes('aiohttp') ? 'aiohttp' : null,
			code.includes('aiosignal') ? 'aiosignal' : null,
			code.includes('altair') ? 'altair' : null,
			code.includes('annotated-types') ? 'annotated-types' : null,
			code.includes('apsw') ? 'apsw' : null,
			code.includes('argon2-cffi') ? 'argon2-cffi' : null,
			code.includes('argon2-cffi-bindings') ? 'argon2-cffi-bindings' : null,
			code.includes('arro3-compute') ? 'arro3-compute' : null,
			code.includes('arro3-core') ? 'arro3-core' : null,
			code.includes('arro3-io') ? 'arro3-io' : null,
			code.includes('asciitree') ? 'asciitree' : null,
			code.includes('astropy') ? 'astropy' : null,
			code.includes('astropy_iers_data') ? 'astropy_iers_data' : null,
			code.includes('asttokens') ? 'asttokens' : null,
			code.includes('async-timeout') ? 'async-timeout' : null,
			code.includes('atomicwrites') ? 'atomicwrites' : null,
			code.includes('attrs') ? 'attrs' : null,
			code.includes('autograd') ? 'autograd' : null,
			code.includes('awkward-cpp') ? 'awkward-cpp' : null,
			code.includes('b2d') ? 'b2d' : null,
			code.includes('bcrypt') ? 'bcrypt' : null,
			code.includes('biopython') ? 'biopython' : null,
			code.includes('bitarray') ? 'bitarray' : null,
			code.includes('bitstring') ? 'bitstring' : null,
			code.includes('bleach') ? 'bleach' : null,
			code.includes('bokeh') ? 'bokeh' : null,
			code.includes('boost-histogram') ? 'boost-histogram' : null,
			code.includes('brotli') ? 'brotli' : null,
			code.includes('cachetools') ? 'cachetools' : null,
			code.includes('Cartopy') ? 'Cartopy' : null,
			code.includes('casadi') ? 'casadi' : null,
			code.includes('cbor-diag') ? 'cbor-diag' : null,
			code.includes('certifi') ? 'certifi' : null,
			code.includes('cffi') ? 'cffi' : null,
			code.includes('cffi_example') ? 'cffi_example' : null,
			code.includes('cftime') ? 'cftime' : null,
			code.includes('charset-normalizer') ? 'charset-normalizer' : null,
			code.includes('clarabel') ? 'clarabel' : null,
			code.includes('click') ? 'click' : null,
			code.includes('cligj') ? 'cligj' : null,
			code.includes('clingo') ? 'clingo' : null,
			code.includes('cloudpickle') ? 'cloudpickle' : null,
			code.includes('cmyt') ? 'cmyt' : null,
			code.includes('colorspacious') ? 'colorspacious' : null,
			code.includes('contourpy') ? 'contourpy' : null,
			code.includes('coolprop') ? 'coolprop' : null,
			code.includes('coverage') ? 'coverage' : null,
			code.includes('cramjam') ? 'cramjam' : null,
			code.includes('crc32c') ? 'crc32c' : null,
			code.includes('cryptography') ? 'cryptography' : null,
			code.includes('css-inline') ? 'css-inline' : null,
			code.includes('cssselect') ? 'cssselect' : null,
			code.includes('cvxpy-base') ? 'cvxpy-base' : null,
			code.includes('cycler') ? 'cycler' : null,
			code.includes('cysignals') ? 'cysignals' : null,
			code.includes('cytoolz') ? 'cytoolz' : null,
			code.includes('decorator') ? 'decorator' : null,
			code.includes('demes') ? 'demes' : null,
			code.includes('deprecation') ? 'deprecation' : null,
			code.includes('distlib') ? 'distlib' : null,
			code.includes('docutils') ? 'docutils' : null,
			code.includes('duckdb') ? 'duckdb' : null,
			code.includes('ewah_bool_utils') ? 'ewah_bool_utils' : null,
			code.includes('exceptiongroup') ? 'exceptiongroup' : null,
			code.includes('executing') ? 'executing' : null,
			code.includes('fastparquet') ? 'fastparquet' : null,
			code.includes('fiona') ? 'fiona' : null,
			code.includes('fonttools') ? 'fonttools' : null,
			code.includes('freesasa') ? 'freesasa' : null,
			code.includes('frozenlist') ? 'frozenlist' : null,
			code.includes('fsspec') ? 'fsspec' : null,
			code.includes('future') ? 'future' : null,
			code.includes('galpy') ? 'galpy' : null,
			code.includes('gensim') ? 'gensim' : null,
			code.includes('geopandas') ? 'geopandas' : null,
			code.includes('gmpy2') ? 'gmpy2' : null,
			code.includes('gsw') ? 'gsw' : null,
			code.includes('h3') ? 'h3' : null,
			code.includes('h5py') ? 'h5py' : null,
			code.includes('html5lib') ? 'html5lib' : null,
			code.includes('httpx') ? 'httpx' : null,
			code.includes('idna') ? 'idna' : null,
			code.includes('igraph') ? 'igraph' : null,
			code.includes('imageio') ? 'imageio' : null,
			code.includes('iminuit') ? 'iminuit' : null,
			code.includes('iniconfig') ? 'iniconfig' : null,
			code.includes('ipython') ? 'ipython' : null,
			code.includes('jedi') ? 'jedi' : null,
			code.includes('Jinja2') ? 'Jinja2' : null,
			code.includes('joblib') ? 'joblib' : null,
			code.includes('jsonschema') ? 'jsonschema' : null,
			code.includes('jsonschema_specifications') ? 'jsonschema_specifications' : null,
			code.includes('kiwisolver') ? 'kiwisolver' : null,
			code.includes('lakers-python') ? 'lakers-python' : null,
			code.includes('lazy-object-proxy') ? 'lazy-object-proxy' : null,
			code.includes('lazy_loader') ? 'lazy_loader' : null,
			code.includes('libcst') ? 'libcst' : null,
			code.includes('lightgbm') ? 'lightgbm' : null,
			code.includes('logbook') ? 'logbook' : null,
			code.includes('lxml') ? 'lxml' : null,
			code.includes('MarkupSafe') ? 'MarkupSafe' : null,
			code.includes('matplotlib-inline') ? 'matplotlib-inline' : null,
			code.includes('matplotlib-pyodide') ? 'matplotlib-pyodide' : null,
			code.includes('memory-allocator') ? 'memory-allocator' : null,
			code.includes('micropip') ? 'micropip' : null,
			code.includes('mmh3') ? 'mmh3' : null,
			code.includes('mne') ? 'mne' : null,
			code.includes('more-itertools') ? 'more-itertools' : null,
			code.includes('mpmath') ? 'mpmath' : null,
			code.includes('msgpack') ? 'msgpack' : null,
			code.includes('msgspec') ? 'msgspec' : null,
			code.includes('msprime') ? 'msprime' : null,
			code.includes('multidict') ? 'multidict' : null,
			code.includes('munch') ? 'munch' : null,
			code.includes('mypy') ? 'mypy' : null,
			code.includes('mypy_extensions') ? 'mypy_extensions' : null,
			code.includes('netCDF4') ? 'netCDF4' : null,
			code.includes('networkx') ? 'networkx' : null,
			code.includes('newick') ? 'newick' : null,
			code.includes('nltk') ? 'nltk' : null,
			code.includes('numba') ? 'numba' : null,
			code.includes('numcodecs') ? 'numcodecs' : null,
			code.includes('numexpr') ? 'numexpr' : null,
			code.includes('opencv-python') ? 'opencv-python' : null,
			code.includes('openpyxl') ? 'openpyxl' : null,
			code.includes('orjson') ? 'orjson' : null,
			code.includes('osqp') ? 'osqp' : null,
			code.includes('packaging') ? 'packaging' : null,
			code.includes('palettable') ? 'palettable' : null,
			code.includes('parso') ? 'parso' : null,
			code.includes('passlib') ? 'passlib' : null,
			code.includes('patsy') ? 'patsy' : null,
			code.includes('pexpect') ? 'pexpect' : null,
			code.includes('pickleshare') ? 'pickleshare' : null,
			code.includes('Pillow') ? 'Pillow' : null,
			code.includes('platformdirs') ? 'platformdirs' : null,
			code.includes('plotly') ? 'plotly' : null,
			code.includes('pluggy') ? 'pluggy' : null,
			code.includes('ply') ? 'ply' : null,
			code.includes('polars') ? 'polars' : null,
			code.includes('pooch') ? 'pooch' : null,
			code.includes('prompt-toolkit') ? 'prompt-toolkit' : null,
			code.includes('protobuf') ? 'protobuf' : null,
			code.includes('psutil') ? 'psutil' : null,
			code.includes('ptyprocess') ? 'ptyprocess' : null,
			code.includes('pure-eval') ? 'pure-eval' : null,
			code.includes('py') ? 'py' : null,
			code.includes('pyarrow') ? 'pyarrow' : null,
			code.includes('pycparser') ? 'pycparser' : null,
			code.includes('pydantic') ? 'pydantic' : null,
			code.includes('pydantic_core') ? 'pydantic_core' : null,
			code.includes('pydub') ? 'pydub' : null,
			code.includes('pyerfa') ? 'pyerfa' : null,
			code.includes('Pygments') ? 'Pygments' : null,
			code.includes('pyproj') ? 'pyproj' : null,
			code.includes('pyrsistent') ? 'pyrsistent' : null,
			code.includes('pytest') ? 'pytest' : null,
			code.includes('python-dateutil') ? 'python-dateutil' : null,
			code.includes('python-lsp-jsonrpc') ? 'python-lsp-jsonrpc' : null,
			code.includes('python-lsp-server') ? 'python-lsp-server' : null,
			code.includes('python-multipart') ? 'python-multipart' : null,
			code.includes('pytz-deprecation-shim') ? 'pytz-deprecation-shim' : null,
			code.includes('PyWavelets') ? 'PyWavelets' : null,
			code.includes('pyxel') ? 'pyxel' : null,
			code.includes('PyYAML') ? 'PyYAML' : null,
			code.includes('qrcode') ? 'qrcode' : null,
			code.includes('rasterio') ? 'rasterio' : null,
			code.includes('rdflib') ? 'rdflib' : null,
			code.includes('referencing') ? 'referencing' : null,
			code.includes('regex') ? 'regex' : null,
			code.includes('reportlab') ? 'reportlab' : null,
			code.includes('rpds-py') ? 'rpds-py' : null,
			code.includes('ruff') ? 'ruff' : null,
			code.includes('scikit-image') ? 'scikit-image' : null,
			code.includes('scikit-learn') ? 'scikit-learn' : null,
			code.includes('scs') ? 'scs' : null,
			code.includes('shapely') ? 'shapely' : null,
			code.includes('shellingham') ? 'shellingham' : null,
			code.includes('six') ? 'six' : null,
			code.includes('skia-python') ? 'skia-python' : null,
			code.includes('smart_open') ? 'smart_open' : null,
			code.includes('sniffio') ? 'sniffio' : null,
			code.includes('snuggs') ? 'snuggs' : null,
			code.includes('sortedcontainers') ? 'sortedcontainers' : null,
			code.includes('soupsieve') ? 'soupsieve' : null,
			code.includes('SPARQLWrapper') ? 'SPARQLWrapper' : null,
			code.includes('sqlalchemy') ? 'sqlalchemy' : null,
			code.includes('sqlglot') ? 'sqlglot' : null,
			code.includes('stack_data') ? 'stack_data' : null,
			code.includes('statsmodels') ? 'statsmodels' : null,
			code.includes('tabulate') ? 'tabulate' : null,
			code.includes('tenacity') ? 'tenacity' : null,
			code.includes('threadpoolctl') ? 'threadpoolctl' : null,
			code.includes('tifffile') ? 'tifffile' : null,
			code.includes('tinycss2') ? 'tinycss2' : null,
			code.includes('toml') ? 'toml' : null,
			code.includes('tomli') ? 'tomli' : null,
			code.includes('toolz') ? 'toolz' : null,
			code.includes('tornado') ? 'tornado' : null,
			code.includes('tqdm') ? 'tqdm' : null,
			code.includes('traitlets') ? 'traitlets' : null,
			code.includes('tskit') ? 'tskit' : null,
			code.includes('typing_extensions') ? 'typing_extensions' : null,
			code.includes('tzdata') ? 'tzdata' : null,
			code.includes('tzlocal') ? 'tzlocal' : null,
			code.includes('ujson') ? 'ujson' : null,
			code.includes('unicodedata2') ? 'unicodedata2' : null,
			code.includes('urllib3') ? 'urllib3' : null,
			code.includes('virtualenv') ? 'virtualenv' : null,
			code.includes('wcwidth') ? 'wcwidth' : null,
			code.includes('webencodings') ? 'webencodings' : null,
			code.includes('wordcloud') ? 'wordcloud' : null,
			code.includes('wrapt') ? 'wrapt' : null,
			code.includes('xarray') ? 'xarray' : null,
			code.includes('xarray-einstats') ? 'xarray-einstats' : null,
			code.includes('xgboost') ? 'xgboost' : null,
			code.includes('xlrd') ? 'xlrd' : null,
			code.includes('xlsxwriter') ? 'xlsxwriter' : null,
			code.includes('xmltodict') ? 'xmltodict' : null,
			code.includes('xyzservices') ? 'xyzservices' : null,
			code.includes('yarl') ? 'yarl' : null,
			code.includes('zarr') ? 'zarr' : null
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
