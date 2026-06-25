import { get } from 'svelte/store';
import { config } from '$lib/stores';
import PyodideWorker from '$lib/workers/pyodide.worker?worker';
import { PyodideSandboxHost } from '$lib/pyodide/pyodideSandboxHost';

// Sandboxed opaque-origin iframe by default; same-origin worker (IDBFS persistence) when the flag is set.
export const createPyodideWorker = (): Worker => {
	if (get(config)?.features?.enable_pyodide_file_persistence) {
		return new PyodideWorker();
	}
	return new PyodideSandboxHost() as unknown as Worker;
};
