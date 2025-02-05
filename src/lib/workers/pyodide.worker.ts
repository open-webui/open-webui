import { loadPyodide, type PyodideInterface } from 'pyodide';

declare global {
	interface Window {
		stdout: string | null;
		stderr: string | null;
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		result: any;
		pyodide: PyodideInterface;
		packages: string[];
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		[key: string]: any;
	}
}

async function loadPyodideAndPackages(packages: string[] = []) {
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
			console.log('An error occurred:', text);
			if (self.stderr) {
				self.stderr += `${text}\n`;
			} else {
				self.stderr = `${text}\n`;
			}
		},
		packages: ['micropip']
	});

	let mountDir = '/mnt';
	self.pyodide.FS.mkdirTree(mountDir);
	// self.pyodide.FS.mount(self.pyodide.FS.filesystems.IDBFS, {}, mountDir);

	// // Load persisted files from IndexedDB (Initial Sync)
	// await new Promise<void>((resolve, reject) => {
	// 	self.pyodide.FS.syncfs(true, (err) => {
	// 		if (err) {
	// 			console.error('Error syncing from IndexedDB:', err);
	// 			reject(err);
	// 		} else {
	// 			console.log('Successfully loaded from IndexedDB.');
	// 			resolve();
	// 		}
	// 	});
	// });

	const micropip = self.pyodide.pyimport('micropip');

	// await micropip.set_index_urls('https://pypi.org/pypi/{package_name}/json');
	await micropip.install(packages);
}

self.onmessage = async (event) => {
	const { id, code, ...context } = event.data;

	console.log(event.data);

	// The worker copies the context in its own "memory" (an object mapping name to values)
	for (const key of Object.keys(context)) {
		self[key] = context[key];
	}

	// make sure loading is done
	await loadPyodideAndPackages(self.packages);

	try {
		// check if matplotlib is imported in the code
		if (code.includes('matplotlib')) {
			// Override plt.show() to return base64 image
			await self.pyodide.runPythonAsync(`import base64
import os
from io import BytesIO

# before importing matplotlib
# to avoid the wasm backend (which needs js.document', not available in worker)
os.environ["MPLBACKEND"] = "AGG"

import matplotlib.pyplot

_old_show = matplotlib.pyplot.show
assert _old_show, "matplotlib.pyplot.show"

def show(*, block=None):
	buf = BytesIO()
	matplotlib.pyplot.savefig(buf, format="png")
	buf.seek(0)
	# encode to a base64 str
	img_str = base64.b64encode(buf.read()).decode('utf-8')
	matplotlib.pyplot.clf()
	buf.close()
	print(f"data:image/png;base64,{img_str}")

matplotlib.pyplot.show = show`);
		}

		self.result = await self.pyodide.runPythonAsync(code);

		// Safely process and recursively serialize the result
		self.result = processResult(self.result);

		console.log('Python result:', self.result);

		// Persist any changes to IndexedDB
		// await new Promise<void>((resolve, reject) => {
		// 	self.pyodide.FS.syncfs(false, (err) => {
		// 		if (err) {
		// 			console.error('Error syncing to IndexedDB:', err);
		// 			reject(err);
		// 		} else {
		// 			console.log('Successfully synced to IndexedDB.');
		// 			resolve();
		// 		}
		// 	});
		// });
	} catch (error) {
		self.stderr = error.toString();
	}

	self.postMessage({ id, result: self.result, stdout: self.stdout, stderr: self.stderr });
};

function processResult(result: any): any {
	// Catch and always return JSON-safe string representations
	try {
		if (result == null) {
			// Handle null and undefined
			return null;
		}
		if (typeof result === 'string' || typeof result === 'number' || typeof result === 'boolean') {
			// Handle primitive types directly
			return result;
		}
		if (typeof result === 'bigint') {
			// Convert BigInt to a string for JSON-safe representation
			return result.toString();
		}
		if (Array.isArray(result)) {
			// If it's an array, recursively process items
			return result.map((item) => processResult(item));
		}
		if (typeof result.toJs === 'function') {
			// If it's a Pyodide proxy object (e.g., Pandas DF, Numpy Array), convert to JS and process recursively
			return processResult(result.toJs());
		}
		if (typeof result === 'object') {
			// Convert JS objects to a recursively serialized representation
			const processedObject: { [key: string]: any } = {};
			for (const key in result) {
				if (Object.prototype.hasOwnProperty.call(result, key)) {
					processedObject[key] = processResult(result[key]);
				}
			}
			return processedObject;
		}
		// Stringify anything that's left (e.g., Proxy objects that cannot be directly processed)
		return JSON.stringify(result);
	} catch (err) {
		// In case something unexpected happens, we return a stringified fallback
		return `[processResult error]: ${err.message || err.toString()}`;
	}
}

export default {};
