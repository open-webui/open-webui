const packages = [
    'affine', 'aiohttp', 'aiosignal', 'altair', 'annotated-types', 'apsw', 'argon2-cffi', 'argon2-cffi-bindings',
    'arro3-compute', 'arro3-core', 'arro3-io', 'asciitree', 'astropy', 'astropy_iers_data', 'asttokens', 'async-timeout',
    'atomicwrites', 'attrs', 'autograd', 'awkward-cpp', 'b2d', 'bcrypt', 'beautifulsoup4', 'biopython', 'bitarray',
    'bitstring', 'bleach', 'bokeh', 'boost-histogram', 'brotli', 'cachetools', 'Cartopy', 'casadi', 'cbor-diag',
    'certifi', 'cffi', 'cffi_example', 'cftime', 'charset-normalizer', 'clarabel', 'click', 'cligj', 'clingo',
    'cloudpickle', 'cmyt', 'colorspacious', 'contourpy', 'coolprop', 'coverage', 'cramjam', 'crc32c', 'cryptography',
    'css-inline', 'cssselect', 'cvxpy-base', 'cycler', 'cysignals', 'cytoolz', 'decorator', 'demes', 'deprecation',
    'distlib', 'docutils', 'duckdb', 'ewah_bool_utils', 'exceptiongroup', 'executing', 'fastparquet', 'fiona',
    'fonttools', 'freesasa', 'frozenlist', 'fsspec', 'future', 'galpy', 'gensim', 'geopandas', 'gmpy2', 'gsw',
    'h5py', 'html5lib', 'httpx', 'idna', 'igraph', 'imageio', 'iminuit', 'iniconfig', 'ipython', 'jedi', 'Jinja2',
    'joblib', 'jsonschema', 'jsonschema_specifications', 'kiwisolver', 'lakers-python', 'lazy-object-proxy',
    'lazy_loader', 'libcst', 'lightgbm', 'logbook', 'lxml', 'MarkupSafe', 'matplotlib', 'matplotlib-inline',
    'matplotlib-pyodide', 'memory-allocator', 'micropip', 'mmh3', 'mne', 'more-itertools', 'mpmath', 'msgpack',
    'msgspec', 'msprime', 'multidict', 'munch', 'mypy', 'narwhals', 'netcdf4', 'networkx', 'newick', 'nh3', 'nlopt',
    'nltk', 'numcodecs', 'numpy', 'opencv-python', 'optlang', 'orjson', 'packaging', 'pandas', 'parso', 'patsy',
    'pcodec', 'peewee', 'pi-heif', 'Pillow', 'pillow-heif', 'pkgconfig', 'pluggy', 'polars', 'pplpy', 'primecountpy',
    'prompt_toolkit', 'protobuf', 'pure-eval', 'py', 'pyarrow', 'pyclipper', 'pycparser', 'pycryptodome', 'pydantic',
    'pydantic_core', 'pyerfa', 'pygame-ce', 'Pygments', 'pyheif', 'pyiceberg', 'pyinstrument', 'pynacl',
    'pyodide-http', 'pyodide-unix-timezones', 'pyparsing', 'pyproj', 'pyrsistent', 'pysam', 'pyshp', 'pytest',
    'pytest-asyncio', 'pytest-benchmark', 'python-dateutil', 'python-flint', 'python-magic', 'python-sat',
    'python-solvespace', 'pytz', 'pywavelets', 'pyxel', 'pyxirr', 'pyyaml', 'rasterio', 'rateslib', 'rebound',
    'reboundx', 'referencing', 'regex', 'requests', 'retrying', 'rich', 'river', 'RobotRaconteur', 'rpds-py',
    'ruamel.yaml', 'rust-abi-test', 'rust-panic-test', 'scikit-image', 'scikit-learn', 'scipy', 'screed', 'setuptools',
    'shapely', 'simplejson', 'sisl', 'six', 'smart-open', 'sortedcontainers', 'soupsieve', 'sourmash', 'soxr',
    'sparseqr', 'sqlalchemy', 'stack-data', 'statsmodels', 'strictyaml', 'svgwrite', 'swiglpk', 'sympy', 'tblib',
    'termcolor', 'texttable', 'threadpoolctl', 'tiktoken', 'tomli', 'tomli-w', 'toolz', 'tqdm', 'traitlets', 'traits',
    'tree-sitter', 'tree-sitter-go', 'tree-sitter-java', 'tree-sitter-python', 'tskit', 'typing-extensions', 'tzdata',
    'uncertainties', 'unyt', 'urllib3', 'vega-datasets', 'wcwidth', 'webencodings', 'wordcloud', 'wrapt', 'xarray',
    'xgboost', 'xlrd', 'xxhash', 'xyzservices', 'yarl', 'yt', 'zarr', 'zengl', 'zfpy', 'zstandard'
];

import { loadPyodide } from 'pyodide';
import { writeFile, readFile, copyFile, readdir, rmdir } from 'fs/promises';

async function downloadPackages() {
	console.log('Setting up pyodide + micropip');

	let pyodide;
	try {
		pyodide = await loadPyodide({
			packageCacheDir: 'static/pyodide'
		});
	} catch (err) {
		console.error('Failed to load Pyodide:', err);
		return;
	}

	const packageJson = JSON.parse(await readFile('package.json'));
	const pyodideVersion = packageJson.dependencies.pyodide.replace('^', '');

	try {
		const pyodidePackageJson = JSON.parse(await readFile('static/pyodide/package.json'));
		const pyodidePackageVersion = pyodidePackageJson.version.replace('^', '');

		if (pyodideVersion !== pyodidePackageVersion) {
			console.log('Pyodide version mismatch, removing static/pyodide directory');
			await rmdir('static/pyodide', { recursive: true });
		}
	} catch (e) {
		console.log('Pyodide package not found, proceeding with download.');
	}

	try {
		console.log('Loading micropip package');
		await pyodide.loadPackage('micropip');

		const micropip = pyodide.pyimport('micropip');
		console.log('Downloading Pyodide packages:', packages);

		try {
			for (const pkg of packages) {
				console.log(`Installing package: ${pkg}`);
				await micropip.install(pkg);
			}
		} catch (err) {
			console.error('Package installation failed:', err);
			return;
		}

		console.log('Pyodide packages downloaded, freezing into lock file');

		try {
			const lockFile = await micropip.freeze();
			await writeFile('static/pyodide/pyodide-lock.json', lockFile);
		} catch (err) {
			console.error('Failed to write lock file:', err);
		}
	} catch (err) {
		console.error('Failed to load or install micropip:', err);
	}
}

async function copyPyodide() {
	console.log('Copying Pyodide files into static directory');
	// Copy all files from node_modules/pyodide to static/pyodide
	for await (const entry of await readdir('node_modules/pyodide')) {
		await copyFile(`node_modules/pyodide/${entry}`, `static/pyodide/${entry}`);
	}
}

await downloadPackages();
await copyPyodide();
