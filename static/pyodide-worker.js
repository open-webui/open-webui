// webworker.js
// Setup your project to serve `py-worker.js`. You should also serve
// `pyodide.js`, and all its associated `.asm.js`, `.json`,
// and `.wasm` files as well:
importScripts('/pyodide/pyodide.js');

async function loadPyodideAndPackages(packages = []) {
	self.stdout = null;
	self.stderr = null;
	self.result = null;

	self.pyodide = await loadPyodide({
		indexURL: '/pyodide/',
		stdout: (text) => {
			console.log('Python output:', text);

			if (self.stdout) {
				self.stdout += `${text}\n`;
			} else {
				self.stdout = `${text}\n`;
			}
		},
		stderr: (text) => {
			console.log('An error occured:', text);
			if (self.stderr) {
				self.stderr += `${text}\n`;
			} else {
				self.stderr = `${text}\n`;
			}
		}
	});

	await self.pyodide.loadPackage('micropip');
	const micropip = self.pyodide.pyimport('micropip');

	await micropip.set_index_urls('https://pypi.org/pypi/{package_name}/json');
	await micropip.install(packages);
}

self.onmessage = async (event) => {
	const { id, code, ...context } = event.data;

	console.log(event.data)

	// The worker copies the context in its own "memory" (an object mapping name to values)
	for (const key of Object.keys(context)) {
		self[key] = context[key];
	}

	// make sure loading is done
	await loadPyodideAndPackages(self.packages);

	self.result = await self.pyodide.runPythonAsync(code);
	self.postMessage({ id, result: self.result, stdout: self.stdout, stderr: self.stderr });
};
