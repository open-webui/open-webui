// both kokoro entry points set wasmPaths, so onnxruntime never resolves these hashed copies
import { readdir, unlink } from 'fs/promises';
import { join } from 'path';

async function dropDuplicateWasm(dir) {
	for (const entry of await readdir(dir, { withFileTypes: true })) {
		const entryPath = join(dir, entry.name);
		if (entry.isDirectory()) {
			await dropDuplicateWasm(entryPath);
		} else if (/^ort-wasm-.*\.wasm$/.test(entry.name)) {
			await unlink(entryPath);
		}
	}
}

await dropDuplicateWasm('build/_app');
