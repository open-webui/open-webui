// Pyodide host for a sandboxed opaque-origin iframe; executed Python can't reach app credentials/DOM/endpoints. Never send it a token.
(function () {
	let pyodide = null;
	let pyodideReady = null;
	let stdout = null;
	let stderr = null;

	function post(msg, transfer) {
		parent.postMessage(msg, '*', transfer || []);
	}

	async function loadPyodideAndPackages(packages) {
		stdout = null;
		stderr = null;
		// eslint-disable-next-line no-undef
		pyodide = await loadPyodide({
			indexURL: '/pyodide/',
			stdout: (text) => {
				stdout = stdout ? `${stdout}${text}\n` : `${text}\n`;
			},
			stderr: (text) => {
				stderr = stderr ? `${stderr}${text}\n` : `${text}\n`;
			},
			packages: ['micropip']
		});
		// In-memory upload dir only; no IDBFS mount at an opaque origin.
		pyodide.FS.mkdirTree('/mnt/uploads');
		const micropip = pyodide.pyimport('micropip');
		await micropip.install(packages || []);
	}

	async function ensurePyodide(packages) {
		if (!pyodideReady) {
			pyodideReady = loadPyodideAndPackages(packages);
		}
		await pyodideReady;
		if (packages && packages.length > 0 && pyodide) {
			const micropip = pyodide.pyimport('micropip');
			await micropip.install(packages);
		}
	}

	function fsUploadFiles(files, dir) {
		dir = dir || '/mnt/uploads';
		try {
			pyodide.FS.stat(dir);
		} catch {
			pyodide.FS.mkdirTree(dir);
		}
		for (const file of files) {
			pyodide.FS.writeFile(`${dir}/${file.name}`, new Uint8Array(file.data));
		}
	}

	function fsList(path) {
		const entries = [];
		try {
			const items = pyodide.FS.readdir(path).filter((n) => n !== '.' && n !== '..');
			for (const name of items) {
				try {
					const stat = pyodide.FS.stat(`${path}/${name}`);
					const isDir = pyodide.FS.isDir(stat.mode);
					entries.push({ name, type: isDir ? 'directory' : 'file', size: isDir ? 0 : stat.size });
				} catch {
					// skip inaccessible entries
				}
			}
		} catch {
			// directory doesn't exist
		}
		return entries;
	}

	function fsRead(path) {
		const data = pyodide.FS.readFile(path);
		return data.buffer;
	}

	function fsDelete(path) {
		try {
			const stat = pyodide.FS.stat(path);
			if (pyodide.FS.isDir(stat.mode)) {
				const items = pyodide.FS.readdir(path).filter((n) => n !== '.' && n !== '..');
				for (const item of items) {
					fsDelete(`${path}/${item}`);
				}
				pyodide.FS.rmdir(path);
			} else {
				pyodide.FS.unlink(path);
			}
		} catch {
			// already gone
		}
	}

	function fsMkdir(path) {
		pyodide.FS.mkdirTree(path);
	}

	function processResult(result) {
		try {
			if (result == null) return null;
			if (typeof result === 'string' || typeof result === 'number' || typeof result === 'boolean') {
				return result;
			}
			if (typeof result === 'bigint') return result.toString();
			if (Array.isArray(result)) return result.map((item) => processResult(item));
			if (typeof result.toJs === 'function') return processResult(result.toJs());
			if (typeof result === 'object') {
				const out = {};
				for (const key in result) {
					if (Object.prototype.hasOwnProperty.call(result, key)) {
						out[key] = processResult(result[key]);
					}
				}
				return out;
			}
			return JSON.stringify(result);
		} catch (err) {
			return `[processResult error]: ${err && err.message ? err.message : String(err)}`;
		}
	}

	async function executeCode(id, code, files) {
		stdout = null;
		stderr = null;
		let result = null;

		if (files && files.length > 0) {
			fsUploadFiles(files);
		}

		try {
			if (code.includes('matplotlib')) {
				await pyodide.runPythonAsync(`import base64
import os
from io import BytesIO

# before importing matplotlib
# to avoid the wasm backend (which needs js.document', not available here)
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

			result = processResult(await pyodide.runPythonAsync(code));
		} catch (error) {
			stderr = error && error.message ? error.message : String(error);
		}

		post({ id, result, stdout, stderr });
	}

	window.addEventListener('message', async (event) => {
		// Only ever accept messages from our own parent.
		if (event.source !== parent) return;

		const data = event.data || {};
		const { id, type } = data;

		if (!type || type === 'execute') {
			const { code, files, packages } = data;
			await ensurePyodide(packages || []);
			await executeCode(id, code, files);
			return;
		}

		await ensurePyodide();

		switch (type) {
			case 'fs:upload':
				fsUploadFiles(data.files, data.dir);
				post({ id, type: 'fs:upload', success: true });
				break;
			case 'fs:list':
				post({ id, type: 'fs:list', entries: fsList(data.path) });
				break;
			case 'fs:read':
				try {
					const buffer = fsRead(data.path);
					post({ id, type: 'fs:read', data: buffer }, [buffer]);
				} catch (err) {
					post({ id, type: 'fs:read', error: err && err.message ? err.message : String(err) });
				}
				break;
			case 'fs:delete':
				fsDelete(data.path);
				post({ id, type: 'fs:delete', success: true });
				break;
			case 'fs:mkdir':
				fsMkdir(data.path);
				post({ id, type: 'fs:mkdir', success: true });
				break;
			case 'fs:sync':
				// no-op: an opaque origin has no persistent backing store
				post({ id, type: 'fs:sync', success: true });
				break;
			default:
				console.warn('Unknown message type:', type);
		}
	});

	// Tell the parent we are wired up and ready to receive work.
	post({ type: '__pyodide_sandbox_ready__' });
})();
