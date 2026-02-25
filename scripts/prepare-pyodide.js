const packages = [
	'micropip',
	'packaging',
	'requests',
	'beautifulsoup4',
	'numpy',
	'pandas',
	'matplotlib',
	'scikit-learn',
	'scipy',
	'regex',
	'sympy',
	'tiktoken',
	'seaborn',
	'pytz',
	'black',
	'openai'
];

import { loadPyodide } from 'pyodide';
import { setGlobalDispatcher, ProxyAgent } from 'undici';
import { writeFile, readFile, copyFile, readdir, rmdir, stat, mkdir } from 'fs/promises';
import { createHash } from 'crypto';

/**
 * Loading network proxy configurations from the environment variables.
 * And the proxy config with lowercase name has the highest priority to use.
 */
function initNetworkProxyFromEnv() {
	// we assume all subsequent requests in this script are HTTPS:
	// https://cdn.jsdelivr.net
	// https://pypi.org
	// https://files.pythonhosted.org
	const allProxy = process.env.all_proxy || process.env.ALL_PROXY;
	const httpsProxy = process.env.https_proxy || process.env.HTTPS_PROXY;
	const httpProxy = process.env.http_proxy || process.env.HTTP_PROXY;
	const preferedProxy = httpsProxy || allProxy || httpProxy;
	/**
	 * use only http(s) proxy because socks5 proxy is not supported currently:
	 * @see https://github.com/nodejs/undici/issues/2224
	 */
	if (!preferedProxy || !preferedProxy.startsWith('http')) return;
	let preferedProxyURL;
	try {
		preferedProxyURL = new URL(preferedProxy).toString();
	} catch {
		console.warn(`Invalid network proxy URL: "${preferedProxy}"`);
		return;
	}
	const dispatcher = new ProxyAgent({ uri: preferedProxyURL });
	setGlobalDispatcher(dispatcher);
	console.log(`Initialized network proxy "${preferedProxy}" from env`);
}

/**
 * Generate a hash of the current configuration to detect changes
 */
function getConfigHash(pyodideVersion) {
	// Use major.minor only for hash (patch versions are compatible)
	const [major, minor] = pyodideVersion.split('.');
	const config = {
		pyodideMajorMinor: `${major}.${minor}`,
		packages: packages.sort()
	};
	return createHash('md5').update(JSON.stringify(config)).digest('hex');
}

/**
 * Check if pyodide cache is valid and up-to-date
 */
async function isCacheValid(pyodideVersion) {
	try {
		// Check if lock file exists
		await stat('static/pyodide/pyodide-lock.json');

		// Check if pyodide package.json exists and major.minor version matches
		// (patch version differences are OK with semver ^)
		const pyodidePackageJson = JSON.parse(await readFile('static/pyodide/package.json'));
		const installedVersion = pyodidePackageJson.version;
		
		// Extract major.minor from both versions
		const [reqMajor, reqMinor] = pyodideVersion.split('.');
		const [instMajor, instMinor] = installedVersion.split('.');
		
		// For ^ (caret) ranges, major.minor must match, patch can differ
		if (reqMajor !== instMajor || reqMinor !== instMinor) {
			console.log(`Pyodide version mismatch: ${installedVersion} -> ${pyodideVersion}`);
			return false;
		}

		// Check if config hash matches (packages list hasn't changed)
		const expectedHash = getConfigHash(pyodideVersion);
		try {
			const storedHash = await readFile('static/pyodide/.config-hash', 'utf-8');
			if (storedHash.trim() !== expectedHash) {
				console.log('Package configuration changed');
				return false;
			}
		} catch {
			// Hash file doesn't exist, need to regenerate
			return false;
		}

		return true;
	} catch {
		return false;
	}
}

async function downloadPackages(pyodideVersion) {
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

	try {
		const pyodidePackageJson = JSON.parse(await readFile('static/pyodide/package.json'));
		const pyodidePackageVersion = pyodidePackageJson.version.replace('^', '');

		if (pyodideVersion !== pyodidePackageVersion) {
			console.log('Pyodide version mismatch, removing static/pyodide directory');
			await rmdir('static/pyodide', { recursive: true });
		}
	} catch (err) {
		console.log('Pyodide package not found, proceeding with download.', err);
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
			// Write config hash to detect future changes
			await writeFile('static/pyodide/.config-hash', getConfigHash(pyodideVersion));
		} catch (err) {
			console.error('Failed to write lock file:', err);
		}
	} catch (err) {
		console.error('Failed to load or install micropip:', err);
	}
}

async function copyPyodide() {
	console.log('Copying Pyodide files into static directory');
	// Ensure static/pyodide directory exists
	try {
		await mkdir('static/pyodide', { recursive: true });
	} catch {
		// Directory may already exist
	}
	// Copy all files from node_modules/pyodide to static/pyodide
	for await (const entry of await readdir('node_modules/pyodide')) {
		await copyFile(`node_modules/pyodide/${entry}`, `static/pyodide/${entry}`);
	}
}

// Main execution
initNetworkProxyFromEnv();

const packageJson = JSON.parse(await readFile('package.json'));
const pyodideVersion = packageJson.dependencies.pyodide.replace('^', '');

// Check if we can skip the expensive work
if (await isCacheValid(pyodideVersion)) {
	console.log('✓ Pyodide cache is valid, skipping download');
} else {
	console.log('Pyodide cache invalid or missing, downloading packages...');
	await downloadPackages(pyodideVersion);
	await copyPyodide();
}
