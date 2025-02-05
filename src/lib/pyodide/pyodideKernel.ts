import PyodideWorker from '$lib/pyodide/pyodideKernel.worker?worker';

export type CellState = {
	id: string;
	status: 'idle' | 'running' | 'completed' | 'error';
	result: any;
	stdout: string;
	stderr: string;
};

export class PyodideKernel {
	private worker: Worker;
	private listeners: Map<string, (data: any) => void>;

	constructor() {
		this.worker = new PyodideWorker();
		this.listeners = new Map();

		// Listen to messages from the worker
		this.worker.onmessage = (event) => {
			const { type, id, ...data } = event.data;

			if ((type === 'stdout' || type === 'stderr') && this.listeners.has(id)) {
				this.listeners.get(id)?.({ type, id, ...data });
			} else if (type === 'result' && this.listeners.has(id)) {
				this.listeners.get(id)?.({ type, id, ...data });
				// Remove the listener once the result is delivered
				this.listeners.delete(id);
			} else if (type === 'kernelState') {
				this.listeners.forEach((listener) => listener({ type, ...data }));
			}
		};

		// Initialize the worker
		this.worker.postMessage({ type: 'initialize' });
	}

	async execute(id: string, code: string): Promise<CellState> {
		return new Promise((resolve, reject) => {
			// Set up the listener for streaming and execution result
			const state: CellState = {
				id,
				status: 'running',
				result: null,
				stdout: '',
				stderr: ''
			};

			this.listeners.set(id, (data) => {
				if (data.type === 'stdout') {
					state.stdout += data.message;
				} else if (data.type === 'stderr') {
					state.stderr += data.message;
				} else if (data.type === 'result') {
					// Final result
					const { state: finalState } = data;
					resolve(finalState);
				}
			});

			// Send execute request to the worker
			this.worker.postMessage({ type: 'execute', id, code });
		});
	}

	async getState() {
		return new Promise<Record<string, CellState>>((resolve) => {
			this.worker.postMessage({ type: 'getState' });
			this.listeners.set('kernelState', (data) => {
				if (data.type === 'kernelState') {
					resolve(data.state);
				}
			});
		});
	}

	terminate() {
		this.worker.postMessage({ type: 'terminate' });
		this.worker.terminate();
	}
}
