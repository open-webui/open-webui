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
	'seaborn',
	'pytz'
];

import { loadPyodide } from 'pyodide/pyodide.js';
import { setGlobalDispatcher, ProxyAgent } from 'undici';
import { writeFile, readFile, copyFile, readdir, rmdir, mkdir } from 'fs/promises';
import { existsSync } from 'fs';
import path from 'path';

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
				await micropip.install(pkg, { keep_going: true });
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
	try {
		// Ensure the static/pyodide directory exists
		await mkdir('static/pyodide', { recursive: true });
		
		// Create index.html and console.html files
		await writeFile('static/pyodide/index.html', `<!DOCTYPE html>
<html>
<head>
  <title>Pyodide Environment</title>
  <meta charset="UTF-8">
</head>
<body>
  <h1>Pyodide Environment</h1>
  <p>This directory contains Pyodide files for the Open WebUI application.</p>
</body>
</html>`);
		
		await writeFile('static/pyodide/console.html', `<!DOCTYPE html>
<html>
<head>
  <title>Pyodide Console</title>
  <meta charset="UTF-8">
  <script src="./pyodide.js"></script>
</head>
<body>
  <h1>Pyodide Console</h1>
  <div id="status">Loading Pyodide...</div>
  
  <script>
    async function main() {
      try {
        const pyodide = await loadPyodide();
        const statusElement = document.getElementById('status');
        statusElement.textContent = 'Pyodide loaded successfully!';
        console.log('Pyodide loaded successfully');
      } catch (error) {
        console.error(error);
        const statusElement = document.getElementById('status');
        statusElement.textContent = 'Error loading Pyodide: ' + error.message;
      }
    }
    
    window.onload = main;
  </script>
</body>
</html>`);
		
		const entries = await readdir('node_modules/pyodide');
		for (const entry of entries) {
			try {
				const sourcePath = `node_modules/pyodide/${entry}`;
				const destPath = `static/pyodide/${entry}`;
				
				// Skip if destination already exists and is not index.html or console.html
				if (existsSync(destPath) && entry !== 'index.html' && entry !== 'console.html') {
					console.log(`Skipping ${entry} as it already exists`);
					continue;
				}
				
				await copyFile(sourcePath, destPath);
				console.log(`Copied ${entry} successfully`);
			} catch (err) {
				console.error(`Failed to copy ${entry}: ${err.message}`);
			}
		}
	} catch (err) {
		console.error(`Error in copyPyodide: ${err.message}`);
	}
}

async function ensureEmojiAssets() {
	console.log('Ensuring emoji assets are available');
	try {
		// Ensure the emoji directory exists
		await mkdir('static/assets/emojis', { recursive: true });
		
		// Create placeholder emoji files if they don't exist
		const requiredEmojis = ['1f3bf.svg', '1f6cb.svg'];
		for (const emoji of requiredEmojis) {
			const emojiPath = `static/assets/emojis/${emoji}`;
			if (!existsSync(emojiPath)) {
				const svgContent = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 36 36"><circle cx="18" cy="18" r="18" fill="#CCCCCC"/></svg>`;
				await writeFile(emojiPath, svgContent);
				console.log(`Created placeholder emoji: ${emoji}`);
			}
		}
	} catch (err) {
		console.error(`Error ensuring emoji assets: ${err.message}`);
	}
}

try {
	initNetworkProxyFromEnv();
	await ensureEmojiAssets();
	await downloadPackages();
	await copyPyodide();
	console.log('Pyodide setup completed successfully');
} catch (err) {
	console.error('Error during Pyodide setup:', err);
	process.exit(1);
}
