const packages = [
    'requests',
    'beautifulsoup4',
    'numpy',
    'pandas',
    'matplotlib',
    'scikit-learn',
    'scipy',
    'regex',
    'seaborn'
];

import { loadPyodide } from 'pyodide';
import { writeFile, copyFile, readdir } from 'fs/promises';

async function downloadPackages() {
    console.log('Setting up pyodide + micropip');
    try {
        const pyodide = await loadPyodide({
            packageCacheDir: 'static/pyodide'
        });
        await pyodide.loadPackage('micropip');
        const micropip = pyodide.pyimport('micropip');

        console.log('Downloading Pyodide packages:', packages);
        await micropip.install(packages);
        
        console.log('Pyodide packages downloaded, freezing into lock file');
        const lockFile = await micropip.freeze();
        await writeFile('static/pyodide/pyodide-lock.json', lockFile);
    } catch (error) {
        console.error('Error downloading Pyodide packages:', error);
        process.exit(1);
    }
}

async function copyPyodide() {
    try {
        console.log('Copying Pyodide files into static directory');
        // Copy all files from node_modules/pyodide to static/pyodide
        for await (const entry of await readdir('node_modules/pyodide')) {
            await copyFile(`node_modules/pyodide/${entry}`, `static/pyodide/${entry}`);
        }
    } catch (error) {
        console.error('Error copying Pyodide files:', error);
        process.exit(1);
    }
}

await downloadPackages();
await copyPyodide();